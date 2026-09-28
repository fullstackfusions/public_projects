"""DynamoDB access. The only module in `chaperone` that talks to AWS.

Table (single, provisioned): PK/SK strings, TTL on `expires_at`.
    ACTOR#<actor>  / <time>#<KIND>#<eventID>   one recorded event (see model.py)
    ACTORS         / <actor>                   actor registry: last_seen, agent
    POLLER#<name>  / CURSOR                    event IDs the poller already wrote
    IDC#<userId>   / ACTOR                     role session an Identity Center user acts as
"""

from __future__ import annotations

import os

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

_table = None


def table():
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
    return _table


def put_event(item: dict) -> None:
    """Idempotent: the key is derived from the CloudTrail event, so a repeat overwrites
    the item with identical content."""
    table().put_item(Item=item)
    touch_actor(item["actor"], item["time"], item.get("agent", False))
    remember_idc(item)


_idc_cache: dict[str, str | None] = {}


def remember_idc(item: dict) -> None:
    """Role-session events carry onBehalfOf.userId: remember which session that Identity
    Center user acts as (written once per user per Lambda container)."""
    user_id, actor = item.get("on_behalf_of"), item["actor"]
    if not user_id or not actor.startswith("role/") or _idc_cache.get(user_id) == actor:
        return
    table().put_item(Item={"PK": f"IDC#{user_id}", "SK": "ACTOR", "actor": actor})
    _idc_cache[user_id] = actor


def resolve_idc(user_id: str) -> str | None:
    if user_id not in _idc_cache:
        item = table().get_item(Key={"PK": f"IDC#{user_id}", "SK": "ACTOR"}).get("Item")
        _idc_cache[user_id] = item["actor"] if item else None
    return _idc_cache[user_id]


def put_events(items: list[dict]) -> None:
    """Many events at once: batched writes (25 per request) and one actor update per actor,
    instead of a put plus two updates per event."""
    if not items:
        return
    with table().batch_writer(overwrite_by_pkeys=["PK", "SK"]) as batch:
        for item in items:
            batch.put_item(Item=item)
    latest: dict[str, tuple[str, bool]] = {}
    for item in items:
        time, agent = latest.get(item["actor"], ("", False))
        latest[item["actor"]] = (max(time, item["time"]), agent or item.get("agent", False))
    for actor, (time, agent) in latest.items():
        touch_actor(actor, time, agent)
    for item in {i["on_behalf_of"]: i for i in items if i.get("on_behalf_of")}.values():
        remember_idc(item)


def touch_actor(actor: str, time: str, agent: bool) -> None:
    """Keep last_seen at the newest event time (events arrive out of order), and mark the
    actor as an agent once any of its events is an agent's."""
    _conditional_update(actor, "SET last_seen = :t", "attribute_not_exists(last_seen) OR last_seen < :t",
                        {":t": time})
    if agent:
        # "agent" is a DynamoDB reserved word, hence #agent.
        _conditional_update(actor, "SET #agent = :a", "attribute_not_exists(#agent)", {":a": True},
                            {"#agent": "agent"})


def _conditional_update(actor, expr, condition, values, names=None):
    try:
        table().update_item(
            Key={"PK": "ACTORS", "SK": actor},
            UpdateExpression=expr,
            ConditionExpression=condition,
            ExpressionAttributeValues=values,
            **({"ExpressionAttributeNames": names} if names else {}),
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise


def actors() -> list[dict]:
    return _query_all(Key("PK").eq("ACTORS"))


def events(actor: str, start: str | None = None, end: str | None = None) -> list[dict]:
    cond = Key("PK").eq(f"ACTOR#{actor}")
    if start and end:
        cond &= Key("SK").between(start, end + "~")
    elif start:
        cond &= Key("SK").gte(start)
    return _query_all(cond)


def get_many(keys: list[dict]) -> list[dict]:
    """BatchGetItem in chunks of 100, retrying unprocessed keys."""
    out, name = [], table().name
    for n in range(0, len(keys), 100):
        pending = {name: {"Keys": keys[n:n + 100]}}
        while pending:
            r = table().meta.client.batch_get_item(RequestItems=pending)
            out += r["Responses"].get(name, [])
            pending = r.get("UnprocessedKeys") or None
    return out


def get_cursor(name: str) -> list[str]:
    item = table().get_item(Key={"PK": f"POLLER#{name}", "SK": "CURSOR"}).get("Item")
    return list(item.get("seen", [])) if item else []


def put_cursor(name: str, seen: list[str]) -> None:
    table().put_item(Item={"PK": f"POLLER#{name}", "SK": "CURSOR", "seen": seen})


def _query_all(cond) -> list[dict]:
    items, kwargs = [], {"KeyConditionExpression": cond}
    while True:
        page = table().query(**kwargs)
        items += page["Items"]
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]
