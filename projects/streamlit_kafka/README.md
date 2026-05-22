# streamlit_kafka

A **Streamlit UI for producing dummy metric data into Kafka**. The form lets you customize a nested JSON payload (`totalCount`, `resolution`, a list of `timestamps` / `values`, a `dimensionMap`, etc.), serializes it to JSON, and publishes it to a configured Kafka topic via `kafka-python`.

Handy for testing downstream consumers without hand-crafting JSON in a CLI.

## Files

| File | Purpose |
|------|---------|
| `streamlit_kafka.py` | The full Streamlit app, including the `KafkaProducer` setup and the JSON-builder form. |

## Prerequisites

- Python 3.9+
- A running Kafka broker reachable at `localhost:9092` (override `bootstrap_servers` at the top of the script if different).

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run streamlit_kafka.py
```

Open the Streamlit URL, fill in the form, and hit the produce button to send the message to Kafka.

## Notes

Change the destination topic by editing the `producer.send(...)` call in `streamlit_kafka.py`. For a richer Kafka stack with a UI to inspect what landed in the topic, see `kafka_kafdrop_ui_project/` in this repo.
