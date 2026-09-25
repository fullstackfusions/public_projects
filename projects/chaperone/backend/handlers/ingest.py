"""EventBridge -> Lambda: one "AWS API Call via CloudTrail" event per invocation (D-018).

Near-real-time path for ordinary API calls, including those an MCP tool call made
(`invokedBy: aws-mcp.amazonaws.com`). MCP tool-call events themselves never reach
EventBridge; poller.py fetches them.
"""

import json
import logging

from chaperone import model, store

log = logging.getLogger()
log.setLevel(logging.INFO)


def handler(event, _context):
    record = event.get("detail") or {}
    try:
        item = model.to_item(record, store.resolve_idc)
    except model.Skip as why:
        return {"skipped": str(why)}
    store.put_event(item)
    log.info(json.dumps({"stored": item["SK"], "actor": item["actor"], "risk": item.get("risk")}))
    return {"stored": item["SK"]}
