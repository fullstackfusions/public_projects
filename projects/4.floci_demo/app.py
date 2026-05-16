import streamlit as st

from document_pipeline import (
    ensure_resources,
    get_job,
    list_bucket_objects,
    list_jobs,
    load_processing_result,
    process_all_jobs,
    process_next_job,
    queue_depth,
    submit_document,
)


st.set_page_config(page_title="Floci Document Pipeline Demo", layout="wide")


def _job_label(job: dict) -> str:
    return f"{job['title']} | {job['customer_name']} | {job['status']} | {job['job_id'][:8]}"


resources = ensure_resources()
jobs = list_jobs()
queued_jobs = sum(1 for job in jobs if job["status"] == "QUEUED")
processed_jobs = sum(1 for job in jobs if job["status"] == "PROCESSED")
failed_jobs = sum(1 for job in jobs if job["status"] == "FAILED")

st.title("Floci document pipeline demo")
st.write(
    "Upload a document, store it in S3, queue it through SQS, and track processing status in DynamoDB."
)

sidebar = st.sidebar
sidebar.header("Pipeline controls")
sidebar.write(f"Bucket: {resources['bucket_name']}")
sidebar.write(f"Queue depth: {queue_depth()}")
sidebar.write(f"Table: {resources['table_name']}")

if sidebar.button("Process one queued job", use_container_width=True):
    processed = process_next_job()
    if processed is None:
        sidebar.info("No queued jobs available.")
    else:
        sidebar.success(f"Processed {processed['job_id'][:8]}")
    st.rerun()

if sidebar.button("Process up to 10 queued jobs", use_container_width=True):
    processed_jobs_batch = process_all_jobs(limit=10)
    if not processed_jobs_batch:
        sidebar.info("No queued jobs available.")
    else:
        sidebar.success(f"Processed {len(processed_jobs_batch)} jobs")
    st.rerun()

metric_columns = st.columns(4)
metric_columns[0].metric("Total jobs", len(jobs))
metric_columns[1].metric("Queued", queued_jobs)
metric_columns[2].metric("Processed", processed_jobs)
metric_columns[3].metric("Failed", failed_jobs)

with st.form("submit-document"):
    st.subheader("Submit a document")
    customer_name = st.text_input("Customer name", value="Northwind Traders")
    title = st.text_input("Document title", value="Invoice intake")
    notes = st.text_area(
        "Notes",
        value="Review this document, create a summary, and keep both source and result in S3.",
        height=120,
    )
    uploaded_file = st.file_uploader("Upload a file", type=["csv", "json", "md", "txt", "yml", "yaml"])
    submitted = st.form_submit_button("Queue document")

    if submitted:
        try:
            payload = uploaded_file.getvalue() if uploaded_file is not None else None
            job = submit_document(
                customer_name=customer_name,
                title=title,
                notes=notes,
                uploaded_name=uploaded_file.name if uploaded_file is not None else None,
                uploaded_bytes=payload,
                content_type=uploaded_file.type if uploaded_file is not None else None,
            )
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.success(f"Queued job {job['job_id']}")
            st.rerun()

st.subheader("Jobs")
if not jobs:
    st.info("No jobs submitted yet.")
else:
    st.dataframe(
        [
            {
                "job_id": job["job_id"],
                "customer_name": job["customer_name"],
                "title": job["title"],
                "status": job["status"],
                "created_at": job["created_at"],
                "file_name": job["file_name"],
            }
            for job in jobs
        ],
        use_container_width=True,
    )

    selected_job_id = st.selectbox(
        "Inspect a job",
        options=[job["job_id"] for job in jobs],
        format_func=lambda job_id: _job_label(next(job for job in jobs if job["job_id"] == job_id)),
    )
    selected_job = get_job(selected_job_id)
    st.json(selected_job)

    result = load_processing_result(selected_job_id)
    if result is not None:
        st.subheader("Processing result")
        st.json(result)

st.subheader("S3 objects")
objects = list_bucket_objects()
if not objects:
    st.info("No S3 objects stored yet.")
else:
    st.code("\n".join(objects))
