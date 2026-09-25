"""Which resources an API call created or deleted, and what they cost while idle.

A declarative table: (service, action) -> CloudFormation/Cloud Control type plus how to read
the resource's ID from the request or response. Refs are computed at ingest (the response is
only available then) and stored on the item; `leftovers.py` checks them later.

Idle cost = what the resource bills per month even when nothing uses it, at us-east-1 list
price for 730 hours. Usage-priced resources (S3, Lambda, on-demand DynamoDB, SQS, ...) idle
at $0. These are estimates for a reviewer, not a bill.
"""

from __future__ import annotations

HOURS = 730


def _get(d, path):
    """Follow a dotted path through dicts; list indexes as digits. None if missing."""
    for part in path.split("."):
        if isinstance(d, list):
            d = d[int(part)] if part.isdigit() and int(part) < len(d) else None
        elif isinstance(d, dict):
            d = d.get(part)
        else:
            return None
    return d


def _items(d, path, key):
    """IDs from an EC2-style `{"items": [{key: ...}]}` list."""
    return [i.get(key) for i in (_get(d, path) or {}).get("items", []) if i.get(key)]


# (service, action) -> (type, where the ID is: ("req"|"resp", path) or a function of (req, resp))
CREATES = {
    ("s3", "CreateBucket"): ("AWS::S3::Bucket", ("req", "bucketName")),
    ("sqs", "CreateQueue"): ("AWS::SQS::Queue", ("resp", "queueUrl")),
    ("sns", "CreateTopic"): ("AWS::SNS::Topic", ("resp", "topicArn")),
    ("events", "PutRule"): ("AWS::Events::Rule", ("req", "name")),
    ("cloudfront", "CreateDistribution"): ("AWS::CloudFront::Distribution", ("resp", "distribution.id")),
    ("cloudfront", "CreateDistributionWithTags"): ("AWS::CloudFront::Distribution", ("resp", "distribution.id")),
    ("cloudfront", "CreateOriginAccessControl"): ("AWS::CloudFront::OriginAccessControl", ("resp", "originAccessControl.id")),
    ("acm", "RequestCertificate"): ("AWS::CertificateManager::Certificate", ("resp", "certificateArn")),
    ("lambda", "CreateFunction"): ("AWS::Lambda::Function", ("req", "functionName")),
    ("dynamodb", "CreateTable"): ("AWS::DynamoDB::Table", ("req", "tableName")),
    ("iam", "CreateRole"): ("AWS::IAM::Role", ("req", "roleName")),
    ("iam", "CreateUser"): ("AWS::IAM::User", ("req", "userName")),
    ("iam", "CreatePolicy"): ("AWS::IAM::ManagedPolicy", ("resp", "policy.arn")),
    ("iam", "CreateAccessKey"): ("AWS::IAM::AccessKey", ("resp", "accessKey.accessKeyId")),
    ("logs", "CreateLogGroup"): ("AWS::Logs::LogGroup", ("req", "logGroupName")),
    ("ec2", "RunInstances"): ("AWS::EC2::Instance", lambda q, s: _items(s, "instancesSet", "instanceId")),
    ("ec2", "CreateNatGateway"): ("AWS::EC2::NatGateway", ("resp", "CreateNatGatewayResponse.natGateway.natGatewayId")),
    ("ec2", "AllocateAddress"): ("AWS::EC2::EIP", ("resp", "allocationId")),
    ("ec2", "CreateVolume"): ("AWS::EC2::Volume", ("resp", "volumeId")),
    ("ec2", "CreateVpc"): ("AWS::EC2::VPC", ("resp", "vpc.vpcId")),
    ("ec2", "CreateSecurityGroup"): ("AWS::EC2::SecurityGroup", ("resp", "groupId")),
    ("ec2", "CreateVpcEndpoint"): ("AWS::EC2::VPCEndpoint", ("resp", "CreateVpcEndpointResponse.vpcEndpoint.vpcEndpointId")),
    ("rds", "CreateDBInstance"): ("AWS::RDS::DBInstance", ("req", "dBInstanceIdentifier")),
    ("kms", "CreateKey"): ("AWS::KMS::Key", ("resp", "keyMetadata.keyId")),
    ("secretsmanager", "CreateSecret"): ("AWS::SecretsManager::Secret", ("resp", "aRN")),
    ("elasticloadbalancing", "CreateLoadBalancer"): ("AWS::ElasticLoadBalancingV2::LoadBalancer",
                                                     ("resp", "loadBalancers.0.loadBalancerArn")),
    ("cloudwatch", "PutMetricAlarm"): ("AWS::CloudWatch::Alarm", ("req", "alarmName")),
    ("eks", "CreateCluster"): ("AWS::EKS::Cluster", ("req", "name")),
    ("ecr", "CreateRepository"): ("AWS::ECR::Repository", ("req", "repositoryName")),
    ("route53", "CreateHostedZone"): ("AWS::Route53::HostedZone", ("resp", "hostedZone.id")),
}

# Create-or-update calls: the same call creates a new resource or changes an existing one.
UPSERTS = {("events", "PutRule"), ("cloudwatch", "PutMetricAlarm")}

DELETES = {
    ("s3", "DeleteBucket"): ("AWS::S3::Bucket", ("req", "bucketName")),
    ("sqs", "DeleteQueue"): ("AWS::SQS::Queue", ("req", "queueUrl")),
    ("sns", "DeleteTopic"): ("AWS::SNS::Topic", ("req", "topicArn")),
    ("events", "DeleteRule"): ("AWS::Events::Rule", ("req", "name")),
    ("cloudfront", "DeleteDistribution"): ("AWS::CloudFront::Distribution", ("req", "id")),
    ("cloudfront", "DeleteOriginAccessControl"): ("AWS::CloudFront::OriginAccessControl", ("req", "id")),
    ("acm", "DeleteCertificate"): ("AWS::CertificateManager::Certificate", ("req", "certificateArn")),
    ("lambda", "DeleteFunction"): ("AWS::Lambda::Function", ("req", "functionName")),
    ("dynamodb", "DeleteTable"): ("AWS::DynamoDB::Table", ("req", "tableName")),
    ("iam", "DeleteRole"): ("AWS::IAM::Role", ("req", "roleName")),
    ("iam", "DeleteUser"): ("AWS::IAM::User", ("req", "userName")),
    ("iam", "DeletePolicy"): ("AWS::IAM::ManagedPolicy", ("req", "policyArn")),
    ("iam", "DeleteAccessKey"): ("AWS::IAM::AccessKey", ("req", "accessKeyId")),
    ("logs", "DeleteLogGroup"): ("AWS::Logs::LogGroup", ("req", "logGroupName")),
    ("ec2", "TerminateInstances"): ("AWS::EC2::Instance", lambda q, s: _items(q, "instancesSet", "instanceId")),
    ("ec2", "DeleteNatGateway"): ("AWS::EC2::NatGateway", ("req", "DeleteNatGatewayRequest.NatGatewayId")),
    ("ec2", "ReleaseAddress"): ("AWS::EC2::EIP", ("req", "allocationId")),
    ("ec2", "DeleteVolume"): ("AWS::EC2::Volume", ("req", "volumeId")),
    ("ec2", "DeleteVpc"): ("AWS::EC2::VPC", ("req", "vpcId")),
    ("ec2", "DeleteSecurityGroup"): ("AWS::EC2::SecurityGroup", ("req", "groupId")),
    ("rds", "DeleteDBInstance"): ("AWS::RDS::DBInstance", ("req", "dBInstanceIdentifier")),
    ("kms", "ScheduleKeyDeletion"): ("AWS::KMS::Key", ("req", "keyId")),
    ("secretsmanager", "DeleteSecret"): ("AWS::SecretsManager::Secret", ("req", "secretId")),
    ("elasticloadbalancing", "DeleteLoadBalancer"): ("AWS::ElasticLoadBalancingV2::LoadBalancer",
                                                     ("req", "loadBalancerArn")),
    ("cloudwatch", "DeleteAlarms"): ("AWS::CloudWatch::Alarm", lambda q, s: list(q.get("alarmNames") or [])),
    ("eks", "DeleteCluster"): ("AWS::EKS::Cluster", ("req", "name")),
    ("ecr", "DeleteRepository"): ("AWS::ECR::Repository", ("req", "repositoryName")),
    ("route53", "DeleteHostedZone"): ("AWS::Route53::HostedZone", ("req", "id")),
}

# Attributes worth keeping for cost: (type) -> {attr name: request path}
ATTRS = {
    "AWS::EC2::Instance": {"instance_type": "instanceType"},
    "AWS::EC2::Volume": {"size_gb": "size", "volume_type": "volumeType"},
    "AWS::RDS::DBInstance": {"instance_class": "dBInstanceClass", "multi_az": "multiAZ"},
    "AWS::ElasticLoadBalancingV2::LoadBalancer": {"lb_type": "type"},
    "AWS::EC2::VPCEndpoint": {"endpoint_type": "CreateVpcEndpointRequest.VpcEndpointType"},
}


def _ids(spec, req, resp) -> list[str]:
    where = spec[1]
    if callable(where):
        found = where(req or {}, resp or {})
    else:
        found = _get(req if where[0] == "req" else resp, where[1])
    found = found if isinstance(found, list) else [found]
    return [normalize_id(spec[0], str(i)) for i in found if i]


def normalize_id(rtype: str, rid: str) -> str:
    if rtype == "AWS::Route53::HostedZone":
        return rid.removeprefix("/hostedzone/")
    return rid


def refs(service: str, action: str, req: dict | None, resp: dict | None) -> tuple[list[dict], list[dict]]:
    """(created, deleted) resource refs for one API call. Failed calls should not be passed."""
    created, deleted = [], []
    spec = CREATES.get((service, action))
    if spec:
        attrs = {k: _get(req or {}, path) for k, path in ATTRS.get(spec[0], {}).items()}
        attrs = {k: v for k, v in attrs.items() if v is not None}
        upsert = {"upsert": True} if (service, action) in UPSERTS else {}
        created = [{"type": spec[0], "id": i, **({"attrs": attrs} if attrs else {}), **upsert}
                   for i in _ids(spec, req, resp)]
    spec = DELETES.get((service, action))
    if spec:
        deleted = [{"type": spec[0], "id": i} for i in _ids(spec, req, resp)]
    return created, deleted


# --- idle cost ------------------------------------------------------------------------------
# us-east-1 list prices (per hour unless noted). Checked against the AWS Price List API on
# 2026-09-25: NAT gateway, public IPv4, ALB, t3.micro, t4g.micro, m5.large, db.t3.micro,
# gp3, KMS key, secret, EKS cluster, interface endpoint. The rest are published list prices
# not re-checked that day.

EC2_HOURLY = {"t2.micro": 0.0116, "t3.nano": 0.0052, "t3.micro": 0.0104, "t3.small": 0.0208,
              "t3.medium": 0.0416, "t3.large": 0.0832, "t4g.nano": 0.0042, "t4g.micro": 0.0084,
              "t4g.small": 0.0168, "t4g.medium": 0.0336, "m5.large": 0.096, "m6i.large": 0.096,
              "m7g.large": 0.0816, "c5.large": 0.085, "r5.large": 0.126}
RDS_HOURLY = {"db.t3.micro": 0.017, "db.t4g.micro": 0.016, "db.t3.small": 0.034, "db.t4g.small": 0.032,
              "db.t3.medium": 0.068, "db.m5.large": 0.171}
EBS_GB_MONTH = {"gp3": 0.08, "gp2": 0.10, "io1": 0.125, "io2": 0.125, "st1": 0.045, "sc1": 0.015, "standard": 0.05}

FLAT_MONTHLY = {
    "AWS::EC2::NatGateway": (0.045 * HOURS, "NAT gateway hourly charge, before data processing"),
    "AWS::EC2::EIP": (0.005 * HOURS, "public IPv4 address"),
    "AWS::KMS::Key": (1.00, "customer managed key"),
    "AWS::SecretsManager::Secret": (0.40, "secret storage"),
    "AWS::CloudWatch::Alarm": (0.10, "standard-resolution alarm"),
    "AWS::EKS::Cluster": (0.10 * HOURS, "EKS control plane, standard support"),
    "AWS::Route53::HostedZone": (0.50, "hosted zone"),
}


def idle_cost(ref: dict) -> tuple[float | None, str]:
    """(USD per month, basis). None when it depends on something not recorded."""
    t, a = ref["type"], ref.get("attrs") or {}
    if t in FLAT_MONTHLY:
        return round(FLAT_MONTHLY[t][0], 2), FLAT_MONTHLY[t][1]
    if t == "AWS::EC2::Instance":
        rate = EC2_HOURLY.get(a.get("instance_type"))
        return (round(rate * HOURS, 2), f"{a['instance_type']} on-demand Linux") if rate else (
            None, f"instance type {a.get('instance_type', '?')}: see pricing")
    if t == "AWS::RDS::DBInstance":
        rate = RDS_HOURLY.get(a.get("instance_class"))
        if rate:
            factor = 2 if str(a.get("multi_az")).lower() == "true" else 1
            return round(rate * HOURS * factor, 2), f"{a['instance_class']} single-AZ, storage extra" if factor == 1 \
                else f"{a['instance_class']} Multi-AZ, storage extra"
        return None, f"class {a.get('instance_class', '?')}: see pricing"
    if t == "AWS::EC2::Volume":
        size, vtype = a.get("size_gb"), a.get("volume_type") or "gp2"
        if size and vtype in EBS_GB_MONTH:
            return round(float(size) * EBS_GB_MONTH[vtype], 2), f"{size} GB {vtype}"
        return None, "volume size unknown"
    if t == "AWS::ElasticLoadBalancingV2::LoadBalancer":
        return (round(0.0225 * HOURS, 2), "application load balancer, before LCUs") if a.get("lb_type", "application") == "application" \
            else (round(0.0225 * HOURS, 2), "network load balancer, before NLCUs")
    if t == "AWS::EC2::VPCEndpoint":
        if a.get("endpoint_type", "Gateway") == "Interface":
            return round(0.01 * HOURS, 2), "interface endpoint, per AZ"
        return 0.0, "gateway endpoint"
    return 0.0, "usage-priced: nothing while idle"
