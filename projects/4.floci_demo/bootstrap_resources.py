from pprint import pprint

from document_pipeline import ensure_resources, list_bucket_objects, list_jobs, queue_depth

def main() -> None:
    resources = ensure_resources()

    print("Created or verified demo resources")
    pprint(resources)

    print("\nQueue depth")
    print(queue_depth())

    print("\nCurrent jobs")
    pprint(list_jobs())

    print("\nCurrent S3 objects")
    pprint(list_bucket_objects())


if __name__ == "__main__":
    main()
