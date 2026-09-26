"""Created/deleted resource refs from real Day 0 calls, and idle cost."""

import pytest

from chaperone import model, resources
from conftest import by_name


def refs_of(event):
    i = model.to_item(event)
    return i.get("creates", []), i.get("deletes", [])


@pytest.mark.parametrize("name,rtype,rid", [
    ("CreateBucket", "AWS::S3::Bucket", "chaperone-web-111122223333-use1"),
    ("CreateQueue", "AWS::SQS::Queue", "https://sqs.us-east-1.amazonaws.com/111122223333/chaperone-eb-probe"),
    ("PutRule", "AWS::Events::Rule", "chaperone-eb-probe"),
    ("CreateDistributionWithTags", "AWS::CloudFront::Distribution", "EDFDVBD6EXAMPLE"),
    ("CreateOriginAccessControl", "AWS::CloudFront::OriginAccessControl", "EDBG9D9LUL0Z3"),
    ("RequestCertificate", "AWS::CertificateManager::Certificate",
     "arn:aws:acm:us-east-1:111122223333:certificate/11111111-2222-4333-8444-555555555555"),
])
def test_day0_creates(day0, name, rtype, rid):
    (e,) = by_name(day0, name)
    created, deleted = refs_of(e)
    assert [(c["type"], c["id"]) for c in created] == [(rtype, rid)] and deleted == []


@pytest.mark.parametrize("name,rtype", [("DeleteQueue", "AWS::SQS::Queue"), ("DeleteRule", "AWS::Events::Rule")])
def test_day0_deletes_match_their_creates(day0, name, rtype):
    (d,) = by_name(day0, name)
    create_name = {"DeleteQueue": "CreateQueue", "DeleteRule": "PutRule"}[name]
    (c,) = by_name(day0, create_name)
    strip = lambda refs: [(r["type"], r["id"]) for r in refs]  # noqa: E731
    assert strip(refs_of(d)[1]) == strip(refs_of(c)[0])


def test_failed_call_creates_nothing(day0):
    (e,) = by_name(day0, "CreateBucket")
    assert "creates" not in model.to_item({**e, "errorCode": "BucketAlreadyExists"})


def test_run_instances_multiple_ids_and_type():
    created, _ = resources.refs("ec2", "RunInstances", {"instanceType": "t3.micro"},
                                {"instancesSet": {"items": [{"instanceId": "i-1"}, {"instanceId": "i-2"}]}})
    assert [c["id"] for c in created] == ["i-1", "i-2"]
    assert created[0]["attrs"] == {"instance_type": "t3.micro"}
    assert resources.idle_cost(created[0]) == (7.59, "t3.micro on-demand Linux")


def test_hosted_zone_ids_are_normalized():
    c, _ = resources.refs("route53", "CreateHostedZone", {}, {"hostedZone": {"id": "/hostedzone/Z123"}})
    _, d = resources.refs("route53", "DeleteHostedZone", {"id": "Z123"}, None)
    assert c[0]["id"] == d[0]["id"] == "Z123"


@pytest.mark.parametrize("ref,usd", [
    ({"type": "AWS::EC2::NatGateway"}, 32.85),
    ({"type": "AWS::EC2::EIP"}, 3.65),
    ({"type": "AWS::KMS::Key"}, 1.00),
    ({"type": "AWS::EC2::Volume", "attrs": {"size_gb": 100, "volume_type": "gp3"}}, 8.00),
    ({"type": "AWS::RDS::DBInstance", "attrs": {"instance_class": "db.t3.micro"}}, 12.41),
    ({"type": "AWS::S3::Bucket"}, 0.0),
    ({"type": "AWS::Lambda::Function"}, 0.0),
])
def test_idle_cost(ref, usd):
    assert resources.idle_cost(ref)[0] == usd


def test_unknown_size_is_not_guessed():
    assert resources.idle_cost({"type": "AWS::EC2::Instance", "attrs": {"instance_type": "x9.huge"}})[0] is None
