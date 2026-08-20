import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation, View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

OTEL_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")

resource = Resource.create({"service.name": "sli-slo-demo-app"})

tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True)))
trace.set_tracer_provider(tracer_provider)

metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=OTEL_ENDPOINT, insecure=True),
    export_interval_millis=5000,
)

# Default OTel histogram bucket boundaries (0-10000) assume a millisecond
# scale. Our order-processing durations are recorded in seconds (~0.05-1.5s),
# so without an explicit view every sample lands in the same bucket and
# percentiles become meaningless. Boundaries below cover 10ms-5s.
order_duration_view = View(
    instrument_name="order_processing_duration_seconds",
    aggregation=ExplicitBucketHistogramAggregation(
        boundaries=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 5]
    ),
)

# The FastAPI auto-instrumentor's own histogram (instrument name
# "http.server.duration", exported as http_server_duration_milliseconds)
# uses default boundaries with huge gaps at the top (750 -> 1000 -> 2500 ->
# 5000ms). histogram_quantile linearly interpolates within whichever bucket
# a percentile falls into, so a p99 landing in the 1000-2500ms bucket gets
# estimated toward 2500ms even though nothing in this app takes that long
# (max ~1.7s). Verified live: the dashboard showed p99 ~2-2.5s against a
# true max of 1.66s from k6's own summary. Boundaries below are sized for
# this app's real range (20ms-1.7s) and keep 500 as an exact boundary since
# the SLO/burn-rate queries filter on le="500.0".
http_duration_view = View(
    instrument_name="http.server.duration",
    aggregation=ExplicitBucketHistogramAggregation(
        boundaries=[5, 10, 20, 30, 50, 75, 100, 150, 200, 300, 400, 500, 600, 750, 1000, 1250, 1500, 1750, 2000, 3000, 5000]
    ),
)

meter_provider = MeterProvider(
    resource=resource,
    metric_readers=[metric_reader],
    views=[order_duration_view, http_duration_view],
)
metrics.set_meter_provider(meter_provider)

tracer = trace.get_tracer("sli-slo-demo-app")
meter = metrics.get_meter("sli-slo-demo-app")

order_processing_duration_seconds = meter.create_histogram(
    name="order_processing_duration_seconds",
    description="Time spent processing an order end to end",
    unit="s",
)
