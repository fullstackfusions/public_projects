"""Investigation tools: thin HTTP clients over prodsim.

Tool errors are returned as text, never raised, so the model sees exactly what an
engineer would ("HTTP 503 ... Retry later") — which is what makes the loop trap bite.
"""

from __future__ import annotations

import json
import time
from functools import lru_cache
from typing import Any

import httpx
from langchain_core.tools import tool

from oncall import telemetry
from oncall.config import settings


@lru_cache
def _http() -> httpx.Client:
    return httpx.Client(base_url=settings().prodsim_url, timeout=30.0)


def _get(tool_name: str, path: str, params: dict[str, Any]) -> str:
    ctx = telemetry.current()
    headers = {"X-Scenario": ctx.scenario, "X-Run-Id": ctx.run_id} if ctx else {}
    params = {k: v for k, v in params.items() if v is not None}
    t0 = time.perf_counter()
    try:
        r = _http().get(path, params=params, headers=headers)
        status = r.status_code
        body = r.text if r.headers.get("content-type", "").startswith("text/") else _pretty(r)
        out = body if r.is_success else f"HTTP {status} from {path}: {body}"
    except httpx.HTTPError as e:
        status, out = 0, f"request to {path} failed: {e}"
    telemetry.record(
        "tool",
        in_chars=len(json.dumps(params)),
        out_chars=len(out),
        out_tokens=telemetry.count_tokens(out),
        latency_ms=(time.perf_counter() - t0) * 1000,
        ok=200 <= status < 300,
        meta={"tool": tool_name, "params": params, "status": status},
    )
    return out


def _pretty(r: httpx.Response) -> str:
    try:
        return json.dumps(r.json(), indent=1)
    except ValueError:
        return r.text


@tool
def list_services() -> str:
    """List the services that exist in this environment."""
    return _get("list_services", "/services", {})


@tool
def query_logs(
    service: str,
    minutes: int = 30,
    level: str | None = None,
    contains: str | None = None,
    limit: int = 250,
) -> str:
    """Fetch recent log lines for a service.

    Args:
        service: Service name, e.g. "checkout-api".
        minutes: Look-back window in minutes (1-120).
        level: Minimum severity: DEBUG, INFO, WARN, ERROR or FATAL. Omit for all lines.
        contains: Only return lines containing this substring (case-insensitive).
        limit: Maximum number of most recent lines to return.
    """
    return _get("query_logs", "/logs", {"service": service, "minutes": minutes, "level": level,
                                        "contains": contains, "limit": limit})


@tool
def get_metrics(service: str, metric: str, minutes: int = 60) -> str:
    """Fetch a per-minute metric time series for a service.

    Args:
        service: Service name.
        metric: Metric name, e.g. "error_rate", "p99_latency_ms", "active_connections".
            An unknown metric returns the list of available ones.
        minutes: Look-back window in minutes.
    """
    return _get("get_metrics", "/metrics", {"service": service, "metric": metric,
                                            "minutes": minutes})


@tool
def list_deploys(service: str | None = None, hours: int = 24) -> str:
    """List recent production deploys, newest first, optionally for one service."""
    return _get("list_deploys", "/deploys", {"service": service, "hours": hours})


@tool
def get_k8s_events(namespace: str | None = None) -> str:
    """List Kubernetes events, optionally filtered by namespace (like `kubectl get events`)."""
    return _get("get_k8s_events", "/k8s/events", {"namespace": namespace})


@tool
def get_dependencies(service: str) -> str:
    """Show what a service depends on and what depends on it."""
    return _get("get_dependencies", "/dependencies", {"service": service})


@tool
def search_runbooks(query: str) -> str:
    """Search the team runbooks. Returns the full text of the top matching pages."""
    return _get("search_runbooks", "/runbooks/search", {"q": query})


@tool(return_direct=True)
def submit_incident_report(
    summary: str,
    root_cause: str,
    evidence: list[str],
    remediation: str,
    confidence: float,
) -> str:
    """Submit the final incident report. Call exactly once, when the root cause is identified.

    Args:
        summary: One or two sentences on what is happening and the impact.
        root_cause: The specific underlying cause (which change, in which service, and why
            it causes the symptoms). Not the symptom.
        evidence: Concrete observations supporting the root cause, each citing its source
            (log line, deploy id, metric, event).
        remediation: The recommended immediate mitigation and follow-up.
        confidence: 0.0-1.0.
    """
    telemetry.emit("report_submitted", root_cause=root_cause, confidence=confidence)
    return "Incident report recorded. Investigation complete."


INVESTIGATION_TOOLS = [
    list_services,
    query_logs,
    get_metrics,
    list_deploys,
    get_k8s_events,
    get_dependencies,
    search_runbooks,
]
ALL_TOOLS = [*INVESTIGATION_TOOLS, submit_incident_report]
# Tools whose output can be large enough to be worth compressing.
BULKY_TOOLS = ["query_logs", "get_metrics", "get_k8s_events", "search_runbooks"]
