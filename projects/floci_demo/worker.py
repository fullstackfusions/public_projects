import argparse
from pprint import pprint

from document_pipeline import process_next_job, run_worker_loop


def main() -> None:
    parser = argparse.ArgumentParser(description="Process queued Floci demo jobs")
    parser.add_argument("--loop", action="store_true", help="Continuously poll SQS for work")
    args = parser.parse_args()

    if args.loop:
        run_worker_loop()
        return

    job = process_next_job()
    if job is None:
        print("No queued jobs available.")
        return

    pprint(job)


if __name__ == "__main__":
    main()
