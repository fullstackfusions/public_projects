"""Risk rules on real Day 0 calls and on synthetic calls for risks Day 0 never hit."""

import json

import pytest

from chaperone import rules
from chaperone.rules import (AUDIT_TAMPERING, DESTRUCTIVE, IDENTITY_ESCALATION, PUBLIC_EXPOSURE, READ, WRITE,
                             classify)
from conftest import by_name


def real(event):
    return classify(rules.service_from_source(event["eventSource"]), event["eventName"],
                    event.get("requestParameters"), event.get("readOnly"))


# --- real events ------------------------------------------------------------------------

def test_day0_cloudfront_only_bucket_policy_is_a_write_not_public(day0):
    (e,) = by_name(day0, "PutBucketPolicy")
    assert real(e).risk == WRITE


def test_day0_sqs_policy_for_eventbridge_is_not_public(day0):
    (e,) = by_name(day0, "SetQueueAttributes")
    assert real(e).risk == WRITE


@pytest.mark.parametrize("name", ["DeleteQueue", "DeleteRule", "RemoveTargets"])
def test_day0_probe_cleanup_is_destructive(day0, name):
    (e,) = by_name(day0, name)
    assert real(e).risk == DESTRUCTIVE


@pytest.mark.parametrize("name", ["LookupEvents", "GetCallerIdentity", "DescribeCertificate", "GetBucketTagging"])
def test_day0_reads(day0, name):
    for e in by_name(day0, name):
        assert real(e).risk == READ


@pytest.mark.parametrize("name", ["CreateBucket", "CreateDistributionWithTags", "RequestCertificate",
                                  "PutRule", "PutTargets", "CreateQueue", "UpdateDistribution"])
def test_day0_writes(day0, name):
    for e in by_name(day0, name):
        assert real(e).risk == WRITE


def test_every_day0_api_event_classifies(day0):
    for e in day0:
        assert real(e).risk in rules.SEVERITY


# --- public exposure --------------------------------------------------------------------

def test_public_bucket_policy():
    policy = {"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Principal": "*", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::b/*"}]}
    v = classify("s3", "PutBucketPolicy", {"bucketName": "b", "bucketPolicy": policy})
    assert v.risk == PUBLIC_EXPOSURE
    assert "b" in v.reasons[0]


def test_bucket_policy_star_with_condition_is_not_public():
    policy = {"Statement": [{"Effect": "Allow", "Principal": {"AWS": "*"}, "Action": "s3:GetObject",
                             "Condition": {"StringEquals": {"aws:PrincipalOrgID": "o-123"}}}]}
    assert classify("s3", "PutBucketPolicy", {"bucketPolicy": policy}).risk == WRITE


def test_policy_as_json_string_and_single_statement():
    assert rules.policy_is_public(json.dumps({"Statement": {"Effect": "Allow", "Principal": {"AWS": ["*"]}}}))
    assert not rules.policy_is_public("")
    assert not rules.policy_is_public("not json")


def test_public_access_block_removed_or_weakened():
    assert classify("s3", "DeleteBucketPublicAccessBlock", {"bucketName": "b"}).risk == PUBLIC_EXPOSURE
    weakened = {"bucketName": "b", "PublicAccessBlockConfiguration": {
        "BlockPublicAcls": True, "IgnorePublicAcls": True, "BlockPublicPolicy": False, "RestrictPublicBuckets": True}}
    assert classify("s3", "PutBucketPublicAccessBlock", weakened).risk == PUBLIC_EXPOSURE
    strict = {"PublicAccessBlockConfiguration": {k: True for k in (
        "BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")}}
    assert classify("s3", "PutBucketPublicAccessBlock", strict).risk == WRITE


def test_security_group_open_to_internet():
    p = {"groupId": "sg-1", "ipPermissions": {"items": [
        {"ipProtocol": "tcp", "fromPort": 22, "toPort": 22, "ipRanges": {"items": [{"cidrIp": "0.0.0.0/0"}]}}]}}
    assert classify("ec2", "AuthorizeSecurityGroupIngress", p).risk == PUBLIC_EXPOSURE
    p6 = {"ipPermissions": {"items": [{"ipv6Ranges": {"items": [{"cidrIpv6": "::/0"}]}}]}}
    assert classify("ec2", "AuthorizeSecurityGroupIngress", p6).risk == PUBLIC_EXPOSURE
    private = {"ipPermissions": {"items": [{"ipRanges": {"items": [{"cidrIp": "10.0.0.0/8"}]}}]}}
    assert classify("ec2", "AuthorizeSecurityGroupIngress", private).risk == WRITE


def test_lambda_public_url_and_versioned_event_name():
    assert classify("lambda", "CreateFunctionUrlConfig20211031", {"authType": "NONE"}).risk == PUBLIC_EXPOSURE
    assert classify("lambda", "CreateFunctionUrlConfig20211031", {"authType": "AWS_IAM"}).risk == WRITE
    assert classify("lambda", "AddPermission20150331v2", {"principal": "*"}).risk == PUBLIC_EXPOSURE
    assert classify("lambda", "AddPermission20150331v2",
                    {"principal": "*", "sourceArn": "arn:aws:events:..."}).risk == WRITE


def test_snapshots_shared_publicly():
    p = {"snapshotId": "snap-1", "createVolumePermission": {"add": {"items": [{"group": "all"}]}}}
    assert classify("ec2", "ModifySnapshotAttribute", p).risk == PUBLIC_EXPOSURE
    assert classify("rds", "ModifyDBSnapshotAttribute", {"valuesToAdd": ["all"]}).risk == PUBLIC_EXPOSURE


# --- identity and audit -----------------------------------------------------------------

@pytest.mark.parametrize("action", ["AttachRolePolicy", "PutUserPolicy", "CreateAccessKey", "UpdateAssumeRolePolicy"])
def test_identity_escalation(action):
    assert classify("iam", action).risk == IDENTITY_ESCALATION


def test_assume_role_is_escalation_but_role_creation_is_a_write():
    assert classify("sts", "AssumeRole").risk == IDENTITY_ESCALATION
    assert classify("iam", "CreateRole").risk == WRITE


@pytest.mark.parametrize("action", ["StopLogging", "DeleteTrail", "UpdateTrail", "PutEventSelectors"])
def test_audit_tampering_beats_destructive(action):
    assert classify("cloudtrail", action).risk == AUDIT_TAMPERING


def test_readonly_flag_wins_over_verb_guess():
    assert classify("s3", "SomethingNew", read_only=True).risk == READ
    assert classify("s3", "GetSomething", read_only=False).risk == WRITE


# --- helpers ----------------------------------------------------------------------------

def test_service_prefix_mapping():
    assert rules.service_from_source("monitoring.amazonaws.com") == "cloudwatch"
    assert rules.service_from_source("s3.amazonaws.com") == "s3"


def test_worst_keeps_reasons_of_the_top_class_only():
    v = rules.worst([rules.Verdict(READ), rules.Verdict(DESTRUCTIVE, ["a"]), rules.Verdict(DESTRUCTIVE, ["b", "a"])])
    assert v.risk == DESTRUCTIVE and v.reasons == ["a", "b"]
    assert rules.worst([]).risk == READ


def test_day0_receive_message_is_a_read(day0):
    from chaperone import model
    (tool,) = [model.to_item(e) for e in by_name(day0, "CallReadWriteTool")
               if any(d["apiName"] == "sqs:ReceiveMessage"
                      for d in e["additionalEventData"]["downstreamRequests"])]
    assert tool["risk"] == READ
