"""Scheduled every minute: fetch the events EventBridge doesn't deliver (D-018).

- MCP tool calls (`aws-mcp.amazonaws.com`, eventType AwsMcpEvent) in us-east-1
- Identity Center sign-ins (`AssumeRoleWithSAML`) and credential fetches
  (`GetRoleCredentials`) in the Identity Center region

CloudTrail can take up to ~15 minutes to make an event visible, so each run looks back
LOOKBACK_MINUTES and skips event IDs a previous run already wrote (kept in a cursor item).

Reconcile: EventBridge can silently skip events (on Day 1 it never delivered 12 kms:Decrypt
calls Lambda made for the agent). So each run also re-reads every agent's activity with
LookupEvents in every region and writes what's missing: EventBridge for speed, this for
completeness.

Backfill (manual invoke): {"backfill_user": "<name>", "lookback_minutes": N, "regions": [...]}
records everything that user name did in the window, e.g. history from before install.
"""

import json
import logging
import os
from datetime import datetime, timedelta, timezone

import boto3

from chaperone import model, store

log = logging.getLogger()
log.setLevel(logging.INFO)

LOOKBACK_MINUTES = int(os.environ.get("LOOKBACK_MINUTES", "20"))

# name -> (region, LookupAttribute)
TARGETS = {
    "mcp": (os.environ.get("MCP_REGION", "us-east-1"),
            {"AttributeKey": "EventSource", "AttributeValue": "aws-mcp.amazonaws.com"}),
    "signin": (os.environ.get("IDENTITY_CENTER_REGION", "us-east-2"),
               {"AttributeKey": "EventName", "AttributeValue": "AssumeRoleWithSAML"}),
    "credentials": (os.environ.get("IDENTITY_CENTER_REGION", "us-east-2"),
                    {"AttributeKey": "EventName", "AttributeValue": "GetRoleCredentials"}),
}


RECONCILE_REGIONS = [r for r in os.environ.get("RECONCILE_REGIONS", "").split(",") if r]
# Each run reconciles one slice of the regions, so every region is re-read every
# RECONCILE_SLICES minutes (well inside the look-back) and a run stays a few seconds.
RECONCILE_SLICES = int(os.environ.get("RECONCILE_SLICES", "5"))


def regions_for(minute: int, regions=None, slices=None) -> list[str]:
    regions = sorted(regions if regions is not None else RECONCILE_REGIONS)
    slices = slices or RECONCILE_SLICES
    return [r for i, r in enumerate(regions) if i % slices == minute % slices]


def agent_usernames():
    """LookupEvents' Username for an assumed role is the session name: role/<Role>/<Session>."""
    return sorted({a["SK"].split("/")[-1] for a in store.actors()
                   if a.get("agent") and a["SK"].startswith("role/")})


def handler(event, _context):
    event = event or {}
    now = datetime.now(timezone.utc)
    lookback = int(event.get("lookback_minutes", LOOKBACK_MINUTES))
    if event.get("backfill_user"):
        attr = {"AttributeKey": "Username", "AttributeValue": event["backfill_user"]}
        return {region: poll(None, region, attr, now - timedelta(minutes=lookback), now)
                for region in event.get("regions", ["us-east-1"])}
    start = now - timedelta(minutes=lookback)
    result = {name: poll(name, region, attr, start, now) for name, (region, attr) in TARGETS.items()}
    for user in agent_usernames():
        attr = {"AttributeKey": "Username", "AttributeValue": user}
        for region in regions_for(now.minute):
            r = poll(f"reconcile:{user}:{region}", region, attr, start, now)
            if r["stored"]:
                result[f"reconcile:{user}:{region}"] = r
    return result


def poll(name, region, attr, start, end):
    client = boto3.client("cloudtrail", region_name=region)
    seen = set(store.get_cursor(name)) if name else set()
    skipped = 0
    in_window, items = [], []
    for page in client.get_paginator("lookup_events").paginate(
            LookupAttributes=[attr], StartTime=start, EndTime=end):
        for e in page["Events"]:
            in_window.append(e["EventId"])
            if e["EventId"] in seen:
                continue
            try:
                items.append(model.to_item(e["CloudTrailEvent"], store.resolve_idc))
            except model.Skip:
                skipped += 1
    store.put_events(items)
    stored = len(items)
    # Only IDs still inside the window are needed next time; this keeps the cursor small.
    if name:
        store.put_cursor(name, in_window)
    result = {"stored": stored, "skipped": skipped, "in_window": len(in_window)}
    if stored or not (name or "").startswith("reconcile:"):  # quiet when there's nothing to fix
        log.info(json.dumps({"target": name or f"backfill:{region}", **result}))
    return result
