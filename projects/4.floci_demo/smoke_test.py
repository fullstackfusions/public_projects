from pprint import pprint

from document_pipeline import (
    ensure_resources,
    get_job,
    list_bucket_objects,
    load_processing_result,
    process_all_jobs,
    queue_depth,
    submit_document,
)


SAMPLE_DOCUMENT = """Invoice 10042
Customer: Northwind Traders
Amount: 189.42
Currency: USD
Line Items:
- Onboarding workshop
- API integration support
"""


def main() -> None:
    print("Resources")
    pprint(ensure_resources())

    print("\nSubmit document")
    job = submit_document(
        customer_name="Northwind Traders",
        title="Invoice intake",
        notes="Create a short summary and keep the source file in S3.",
        uploaded_name="invoice-10042.txt",
        uploaded_bytes=SAMPLE_DOCUMENT.encode("utf-8"),
        content_type="text/plain",
    )
    pprint(job)

    print("\nQueue depth after submit")
    print(queue_depth())

    print("\nProcess queued jobs")
    pprint(process_all_jobs(limit=5))

    print("\nQueue depth after processing")
    print(queue_depth())

    print("\nStored objects")
    pprint(list_bucket_objects())

    print("\nFinal job record")
    pprint(get_job(job["job_id"]))

    print("\nProcessing result")
    pprint(load_processing_result(job["job_id"]))


if __name__ == "__main__":
    main()
