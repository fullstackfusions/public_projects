"""What did the agent leave running?

From one session's API items: every resource it created, whether it deleted it again before
the session ended ("cleaned up"), whether it still exists now ("left running", with idle
cost), and anything it deleted that it had not created in that session ("removed
pre-existing", the one a reviewer should look at first).

Existence is checked by an injected `check(ref) -> (status, detail)` so this stays pure;
`aws_checks.cloud_control_check` is the real one.
"""

from __future__ import annotations

from urllib.parse import urlparse

from . import resources
from .model import API

EXISTS, GONE, UNKNOWN = "exists", "gone", "unknown"


def arn_of(ref: dict, region: str, account: str) -> str | None:
    """Best-effort ARN for a ref, used to scope guardrails. None if not derivable."""
    t, i = ref["type"], ref["id"]
    if i.startswith("arn:"):
        return i
    build = {
        "AWS::S3::Bucket": f"arn:aws:s3:::{i}",
        "AWS::Events::Rule": f"arn:aws:events:{region}:{account}:rule/{i}",
        "AWS::IAM::Role": f"arn:aws:iam::{account}:role/{i}",
        "AWS::IAM::User": f"arn:aws:iam::{account}:user/{i}",
        "AWS::Lambda::Function": f"arn:aws:lambda:{region}:{account}:function:{i}",
        "AWS::DynamoDB::Table": f"arn:aws:dynamodb:{region}:{account}:table/{i}",
        "AWS::Logs::LogGroup": f"arn:aws:logs:{region}:{account}:log-group:{i}",
        "AWS::CloudFront::Distribution": f"arn:aws:cloudfront::{account}:distribution/{i}",
        "AWS::KMS::Key": f"arn:aws:kms:{region}:{account}:key/{i}",
        "AWS::EC2::Instance": f"arn:aws:ec2:{region}:{account}:instance/{i}",
        "AWS::EC2::Volume": f"arn:aws:ec2:{region}:{account}:volume/{i}",
        "AWS::EC2::VPC": f"arn:aws:ec2:{region}:{account}:vpc/{i}",
        "AWS::EC2::SecurityGroup": f"arn:aws:ec2:{region}:{account}:security-group/{i}",
        "AWS::ECR::Repository": f"arn:aws:ecr:{region}:{account}:repository/{i}",
        "AWS::EKS::Cluster": f"arn:aws:eks:{region}:{account}:cluster/{i}",
    }.get(t)
    if build:
        return build
    if t == "AWS::SQS::Queue":
        name = urlparse(i).path.rsplit("/", 1)[-1]
        return f"arn:aws:sqs:{region}:{account}:{name}"
    return None


def _key(ref, region):
    return ref["type"], region, ref["id"]


def created_keys(items: list[dict]) -> set[tuple]:
    """Keys of every resource these items created, for `known_before`."""
    return {_key(ref, i.get("region")) for i in items if i["kind"] == API for ref in i.get("creates", [])}


def analyze(items: list[dict], check=None, known_before: set[tuple] = frozenset()) -> dict:
    """items: one session's items (any order). Returns the four lists and the idle total.
    known_before: keys of resources recorded as created before this session (any actor);
    a create-or-update call (PutRule) on one of them is an update, not a new resource."""
    apis = sorted((i for i in items if i["kind"] == API), key=lambda i: (i["time"], i["SK"]))
    created: dict[tuple, dict] = {}
    removed_preexisting = []
    for item in apis:
        region = item.get("region")
        for ref in item.get("creates", []):
            if ref.get("upsert") and _key(ref, region) in known_before:
                continue  # an update to something that already existed
            created.setdefault(_key(ref, region), {
                **ref, "region": region, "account": item.get("account"),
                "created_at": item["time"], "created_by": f"{item['service']}:{item['action']}",
                "via": item.get("via"), "event_id": item["event_id"]})
        for ref in item.get("deletes", []):
            entry = created.get(_key(ref, region))
            if entry and "deleted_at" not in entry:
                entry["deleted_at"] = item["time"]
                entry["deleted_by"] = f"{item['service']}:{item['action']}"
            elif not entry:
                removed_preexisting.append({**ref, "region": region, "deleted_at": item["time"],
                                            "deleted_by": f"{item['service']}:{item['action']}",
                                            "via": item.get("via"), "event_id": item["event_id"]})

    cleaned_up = [e for e in created.values() if "deleted_at" in e]
    candidates = [e for e in created.values() if "deleted_at" not in e]
    left_running, already_gone = [], []
    for e in candidates:
        status, detail = check(e) if check else (UNKNOWN, "not checked")
        cost, basis = resources.idle_cost(e)
        row = {**e, "status": status, "status_detail": detail, "idle_usd_month": cost, "cost_basis": basis}
        (already_gone if status == GONE else left_running).append(row)

    known = [r["idle_usd_month"] for r in left_running if r["status"] == EXISTS and r["idle_usd_month"]]
    return {
        "left_running": left_running,
        "removed_later": already_gone,   # created here, deleted after the session ended
        "cleaned_up": cleaned_up,
        "removed_preexisting": removed_preexisting,
        "idle_usd_month": round(sum(known), 2),
        "unpriced": sum(1 for r in left_running if r["status"] != GONE and r["idle_usd_month"] is None),
    }
