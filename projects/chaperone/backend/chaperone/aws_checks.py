"""The AWS services Chaperone builds on for the review answers (D-023):

- AWS Cloud Control API: one existence check for many resource types ("left running").
- IAM Access Analyzer ValidatePolicy: every proposed guardrail is checked by AWS's own linter.
- IAM Access Analyzer policy generation: a least-privilege policy with resource ARNs for a
  principal over the session's time window, from the trail's logs. Shown next to Chaperone's
  preview with the differences (D-027): each catches things the other misses.
"""

from __future__ import annotations

import os

import boto3
from botocore.exceptions import ClientError

from .leftovers import EXISTS, GONE, UNKNOWN

# Types whose Cloud Control primary identifier isn't the ID we store.
_GLOBAL = {"AWS::IAM::Role", "AWS::IAM::User", "AWS::IAM::ManagedPolicy", "AWS::IAM::AccessKey",
           "AWS::CloudFront::Distribution", "AWS::CloudFront::OriginAccessControl", "AWS::Route53::HostedZone"}


def cc_identifier(ref: dict) -> str:
    if ref["type"] == "AWS::Events::Rule":
        return f"arn:aws:events:{ref['region']}:{ref['account']}:rule/{ref['id']}"
    return ref["id"]


def _native_check(ref: dict, region: str):
    """Types whose Cloud Control read handler needs permissions an existence check must not
    have (from the CloudFormation schemas): Secrets Manager wants GetSecretValue, Lambda
    wants GetFunction (returns environment variables) and kms:Decrypt, EventBridge rules
    want iam:PassRole. Use the narrowest native call instead. None = use Cloud Control."""
    t = ref["type"]
    if t == "AWS::SecretsManager::Secret":
        r = boto3.client("secretsmanager", region_name=region).describe_secret(SecretId=ref["id"])
        return (GONE, "scheduled for deletion") if r.get("DeletedDate") else (EXISTS, "DescribeSecret")
    if t == "AWS::Lambda::Function":
        arn = f"arn:aws:lambda:{region}:{ref['account']}:function:{ref['id']}"
        boto3.client("lambda", region_name=region).list_tags(Resource=arn)
        return EXISTS, "lambda ListTags"
    if t == "AWS::Events::Rule":
        boto3.client("events", region_name=region).describe_rule(Name=ref["id"])
        return EXISTS, "events DescribeRule"
    if t == "AWS::IAM::AccessKey":
        return UNKNOWN, "access keys aren't readable through Cloud Control; check IAM"
    return None


def cloud_control_check(ref: dict) -> tuple[str, str]:
    region = "us-east-1" if ref["type"] in _GLOBAL else ref.get("region") or "us-east-1"
    try:
        native = _native_check(ref, region)
        if native:
            return native
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("ResourceNotFoundException", "NoSuchEntity"):
            return GONE, code
        return UNKNOWN, f"{code}: {e.response['Error'].get('Message', '')[:120]}"
    client = boto3.client("cloudcontrol", region_name=region)
    try:
        client.get_resource(TypeName=ref["type"], Identifier=cc_identifier(ref))
        return EXISTS, "Cloud Control GetResource"
    except ClientError as e:
        code, msg = e.response["Error"]["Code"], e.response["Error"].get("Message", "")
        if code == "ResourceNotFoundException" or "not found" in msg.lower() or "does not exist" in msg.lower():
            return GONE, code
        if code in ("UnsupportedActionException", "TypeNotFoundException"):
            return UNKNOWN, f"{ref['type']} not readable through Cloud Control"
        return UNKNOWN, f"{code}: {msg[:120]}"


def validate(policy: dict, policy_type: str = "IDENTITY_POLICY") -> list[dict]:
    """IAM Access Analyzer ValidatePolicy findings (errors, security warnings, suggestions)."""
    import json
    client = boto3.client("accessanalyzer", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    findings = []
    for page in client.get_paginator("validate_policy").paginate(
            policyDocument=json.dumps(policy), policyType=policy_type):
        findings += [{"type": f["findingType"], "issue": f["issueCode"], "detail": f["findingDetails"],
                      "learn_more": f.get("learnMoreLink")} for f in page["findings"]]
    return findings


def start_policy_generation(principal_arn: str, start, end) -> str:
    """Kick off Access Analyzer policy generation for one principal and window. Minutes."""
    client = boto3.client("accessanalyzer", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return client.start_policy_generation(
        policyGenerationDetails={"principalArn": principal_arn},
        cloudTrailDetails={
            "trails": [{"cloudTrailArn": os.environ["TRAIL_ARN"], "allRegions": True}],
            "accessRole": os.environ["ACCESS_ANALYZER_ROLE_ARN"],
            "startTime": start, "endTime": end,
        },
    )["jobId"]


def get_generated_policy(job_id: str) -> dict:
    client = boto3.client("accessanalyzer", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    r = client.get_generated_policy(jobId=job_id, includeResourcePlaceholders=True,
                                    includeServiceLevelTemplate=True)
    return {"status": r["jobDetails"]["status"],
            "started_on": r["jobDetails"].get("startedOn"),
            "completed_on": r["jobDetails"].get("completedOn"),
            "error": r["jobDetails"].get("jobError"),
            "policies": [p["policy"] for p in r.get("generatedPolicyResult", {}).get("generatedPolicies", [])],
            "properties": {k: v for k, v in r.get("generatedPolicyResult", {}).get("properties", {}).items()
                           if k in ("isComplete", "principalArn", "cloudTrailProperties")}}
