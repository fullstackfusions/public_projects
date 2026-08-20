import random
import time
import uuid

from fastapi import FastAPI, HTTPException
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from telemetry import order_processing_duration_seconds, tracer

app = FastAPI(title="sli-slo-demo-app")
FastAPIInstrumentor.instrument_app(app)

# Injected via k6 to make the dashboard show something interesting.
SLOW_PATH_PROBABILITY = 0.05
ERROR_PROBABILITY = 0.02


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/search")
def search(q: str = ""):
    time.sleep(random.uniform(0.02, 0.15))
    if random.random() < ERROR_PROBABILITY:
        raise HTTPException(status_code=500, detail="search backend unavailable")
    return {"query": q, "results": []}


@app.post("/api/orders")
def create_order():
    start = time.perf_counter()
    with tracer.start_as_current_span("process_order") as span:
        order_id = str(uuid.uuid4())
        span.set_attribute("order.id", order_id)

        base_latency = random.uniform(0.05, 0.2)
        if random.random() < SLOW_PATH_PROBABILITY:
            base_latency += random.uniform(0.5, 1.5)
        time.sleep(base_latency)

        duration = time.perf_counter() - start
        order_processing_duration_seconds.record(duration, {"route": "/api/orders"})

        if random.random() < ERROR_PROBABILITY:
            span.set_attribute("order.failed", True)
            raise HTTPException(status_code=500, detail="order processing failed")

        return {"order_id": order_id, "duration_seconds": duration}
