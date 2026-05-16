import os

import boto3
from botocore.config import Config


def _connection_kwargs(service_name: str) -> dict:
    kwargs = {
        "endpoint_url": os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566"),
        "region_name": os.getenv("AWS_DEFAULT_REGION", "us-east-1"),
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", "test"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    }

    if service_name == "s3":
        kwargs["config"] = Config(s3={"addressing_style": "path"})

    return kwargs


def client(service_name: str):
    return boto3.client(service_name, **_connection_kwargs(service_name))


def resource(service_name: str):
    return boto3.resource(service_name, **_connection_kwargs(service_name))
