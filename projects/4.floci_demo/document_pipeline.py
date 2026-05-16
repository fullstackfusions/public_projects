import json
import mimetypes
import re
import time
import uuid
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from floci_client import client, resource


BUCKET_NAME = "document-intake-demo"
QUEUE_NAME = "document-processing-demo"
TABLE_NAME = "document-jobs-demo"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_filename(file_name: str | None) -> str:
    candidate = Path(file_name or "submission.txt").name.strip() or "submission.txt"
    return re.sub(r"[^A-Za-z0-9._-]", "-", candidate)


def ensure_bucket() -> str:
    s3 = client("s3")
    existing = {bucket["Name"] for bucket in s3.list_buckets().get("Buckets", [])}
    if BUCKET_NAME not in existing:
        s3.create_bucket(Bucket=BUCKET_NAME)
    return BUCKET_NAME


def ensure_queue() -> str:
    sqs = client("sqs")
    sqs.create_queue(
        QueueName=QUEUE_NAME,
        Attributes={"VisibilityTimeout": "30"},
    )
    return sqs.get_queue_url(QueueName=QUEUE_NAME)["QueueUrl"]


def ensure_table() -> str:
    dynamodb_client = client("dynamodb")
    existing = set(dynamodb_client.list_tables().get("TableNames", []))
    if TABLE_NAME not in existing:
        table = resource("dynamodb").create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
    return TABLE_NAME


def ensure_resources() -> dict:
    return {
        "bucket_name": ensure_bucket(),
        "queue_url": ensure_queue(),
        "table_name": ensure_table(),
    }


def _table():
    ensure_table()
    return resource("dynamodb").Table(TABLE_NAME)


def _default_document(title: str, notes: str) -> bytes:
    payload = {
        "title": title,
        "notes": notes,
        "submitted_at": _utc_now(),
    }
    return json.dumps(payload, indent=2).encode("utf-8")


def submit_document(
    customer_name: str,
    title: str,
    notes: str,
    uploaded_name: str | None = None,
    uploaded_bytes: bytes | None = None,
    content_type: str | None = None,
) -> dict:
    customer_name = customer_name.strip()
    title = title.strip()
    notes = notes.strip()

    if not customer_name:
        raise ValueError("customer_name is required")
    if not title:
        raise ValueError("title is required")
    if not notes and not uploaded_bytes:
        raise ValueError("notes or an uploaded document is required")

    resources = ensure_resources()
    safe_name = _safe_filename(uploaded_name)
    body = uploaded_bytes if uploaded_bytes is not None else _default_document(title, notes)

    if uploaded_bytes is None:
        safe_name = "submission.json"
        content_type = "application/json"
    elif not content_type:
        guessed_type, _ = mimetypes.guess_type(safe_name)
        content_type = guessed_type or "application/octet-stream"

    job_id = str(uuid.uuid4())
    created_at = _utc_now()
    object_key = f"incoming/{job_id}/{safe_name}"

    s3 = client("s3")
    s3.put_object(
        Bucket=resources["bucket_name"],
        Key=object_key,
        Body=body,
        ContentType=content_type or "application/octet-stream",
        Metadata={
            "customer_name": customer_name,
            "job_id": job_id,
            "title": title,
        },
    )

    queue_message = {
        "bucket_name": resources["bucket_name"],
        "content_type": content_type or "application/octet-stream",
        "job_id": job_id,
        "object_key": object_key,
    }
    sqs = client("sqs")
    queue_response = sqs.send_message(
        QueueUrl=resources["queue_url"],
        MessageBody=json.dumps(queue_message),
    )

    item = {
        "job_id": job_id,
        "customer_name": customer_name,
        "title": title,
        "notes": notes,
        "status": "QUEUED",
        "created_at": created_at,
        "updated_at": created_at,
        "bucket_name": resources["bucket_name"],
        "object_key": object_key,
        "content_type": content_type or "application/octet-stream",
        "file_name": safe_name,
        "file_size_bytes": len(body),
        "message_id": queue_response["MessageId"],
    }
    _table().put_item(Item=item)
    return item


def get_job(job_id: str) -> dict | None:
    response = _table().get_item(Key={"job_id": job_id})
    return response.get("Item")


def list_jobs() -> list[dict]:
    items = _table().scan().get("Items", [])
    return sorted(items, key=lambda item: item["created_at"], reverse=True)


def queue_depth() -> int:
    attributes = client("sqs").get_queue_attributes(
        QueueUrl=ensure_queue(),
        AttributeNames=["ApproximateNumberOfMessages"],
    )
    return int(attributes["Attributes"].get("ApproximateNumberOfMessages", "0"))


def list_bucket_objects() -> list[str]:
    response = client("s3").list_objects_v2(Bucket=ensure_bucket())
    return [item["Key"] for item in response.get("Contents", [])]


def _decode_body(file_name: str, content_type: str, body: bytes) -> tuple[bool, str | None]:
    text_like_suffixes = {".csv", ".json", ".md", ".py", ".txt", ".yaml", ".yml"}
    suffix = Path(file_name).suffix.lower()
    is_text = content_type.startswith("text/") or content_type in {"application/json", "application/xml"}
    is_text = is_text or suffix in text_like_suffixes

    if not is_text:
        return False, None

    return True, body.decode("utf-8", errors="replace")


def _build_summary(job: dict, body: bytes) -> dict:
    is_text, decoded = _decode_body(job["file_name"], job["content_type"], body)
    summary = {
        "sha256": sha256(body).hexdigest(),
        "size_bytes": len(body),
        "stored_in_s3": f"s3://{job['bucket_name']}/{job['object_key']}",
    }

    if not is_text or decoded is None:
        summary["document_type"] = "binary"
        return {
            "job_id": job["job_id"],
            "processed_at": _utc_now(),
            "summary": summary,
        }

    lines = [line for line in decoded.splitlines() if line.strip()]
    words = decoded.split()
    summary.update(
        {
            "document_type": "text",
            "line_count": len(lines),
            "word_count": len(words),
            "preview": decoded[:240],
        }
    )

    if job["file_name"].lower().endswith(".json"):
        try:
            parsed = json.loads(decoded)
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(parsed, dict):
                summary["top_level_keys"] = sorted(parsed.keys())[:10]

    return {
        "job_id": job["job_id"],
        "processed_at": _utc_now(),
        "summary": summary,
    }


def load_processing_result(job_id: str) -> dict | None:
    job = get_job(job_id)
    if not job or "result_key" not in job:
        return None

    response = client("s3").get_object(Bucket=job["bucket_name"], Key=job["result_key"])
    body = response["Body"].read().decode("utf-8")
    return json.loads(body)


def process_next_job() -> dict | None:
    resources = ensure_resources()
    sqs = client("sqs")
    response = sqs.receive_message(
        QueueUrl=resources["queue_url"],
        MaxNumberOfMessages=1,
        WaitTimeSeconds=1,
    )
    messages = response.get("Messages", [])
    if not messages:
        return None

    message = messages[0]
    payload = json.loads(message["Body"])
    job_id = payload["job_id"]
    job = get_job(job_id)

    if job is None:
        sqs.delete_message(QueueUrl=resources["queue_url"], ReceiptHandle=message["ReceiptHandle"])
        return None

    table = _table()
    started_at = _utc_now()
    table.update_item(
        Key={"job_id": job_id},
        UpdateExpression="SET #status = :status, updated_at = :updated_at, processing_started_at = :processing_started_at",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={
            ":status": "PROCESSING",
            ":updated_at": started_at,
            ":processing_started_at": started_at,
        },
    )

    try:
        s3_response = client("s3").get_object(Bucket=job["bucket_name"], Key=job["object_key"])
        body = s3_response["Body"].read()
        result = _build_summary(job, body)
        result_key = f"processed/{job_id}.json"
        client("s3").put_object(
            Bucket=job["bucket_name"],
            Key=result_key,
            Body=json.dumps(result, indent=2).encode("utf-8"),
            ContentType="application/json",
        )

        finished_at = _utc_now()
        table.update_item(
            Key={"job_id": job_id},
            UpdateExpression=(
                "SET #status = :status, updated_at = :updated_at, processed_at = :processed_at, "
                "result_key = :result_key, summary = :summary REMOVE failure_reason"
            ),
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "PROCESSED",
                ":updated_at": finished_at,
                ":processed_at": finished_at,
                ":result_key": result_key,
                ":summary": result["summary"],
            },
        )
        sqs.delete_message(QueueUrl=resources["queue_url"], ReceiptHandle=message["ReceiptHandle"])
    except Exception as exc:
        failed_at = _utc_now()
        table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #status = :status, updated_at = :updated_at, failure_reason = :failure_reason",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "FAILED",
                ":updated_at": failed_at,
                ":failure_reason": str(exc),
            },
        )
        sqs.delete_message(QueueUrl=resources["queue_url"], ReceiptHandle=message["ReceiptHandle"])
        raise

    return get_job(job_id)


def process_all_jobs(limit: int = 10) -> list[dict]:
    processed = []
    for _ in range(limit):
        job = process_next_job()
        if job is None:
            break
        processed.append(job)
    return processed


def run_worker_loop(poll_interval_seconds: float = 2.0) -> None:
    while True:
        processed = process_next_job()
        if processed is None:
            time.sleep(poll_interval_seconds)
            continue
        print(f"Processed job {processed['job_id']} ({processed['status']})")
