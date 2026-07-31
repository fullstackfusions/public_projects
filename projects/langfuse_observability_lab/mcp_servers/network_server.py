"""MCP server exposing 'network' tools: run commands on devices, DNS lookup,
ping/subnet check.

Runs over stdio. This server deliberately models the three blind spots from
the write-up in README.md instead of only the happy path:

- `core-sw-01`, `edge-rtr-02`   -> always succeed immediately.
- `flaky-fw-03`                 -> simulates a device/connection that drops
                                    the first 2 of every 3 attempts, then
                                    succeeds on the 3rd. This is the "gateway
                                    silently drops, 3rd retry works" scenario.
                                    The retrying itself is NOT done here --
                                    see agents/network_client.py -- this
                                    server only ever raises on a bad attempt,
                                    same as a real flaky device/gateway would.
- `dead-host-04`                -> never responds. Raises TimeoutError after
                                    a short simulated delay on every attempt
                                    (scaled down from a real 5-minute MCP
                                    timeout so the demo stays fast).
- `10.0.0.99`                   -> "up" per DNS/inventory but 100% ping loss.
                                    `ping_check` reports this as normal
                                    (non-error) output -- a silent degraded
                                    result, not an exception, which is
                                    exactly the case that a red/green trace
                                    view alone won't catch for you.
"""
from __future__ import annotations

import json
import time
from typing import List

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("network-server")

_DEVICES = {"core-sw-01", "edge-rtr-02", "flaky-fw-03", "dead-host-04"}

# Per-device attempt counter, used to make flaky-fw-03 deterministic:
# fails on attempts where (count % 3 != 0), succeeds every 3rd attempt.
_ATTEMPT_COUNTS: dict[str, int] = {}

_DNS_TABLE = {
    "core-sw-01.lab.internal": "10.0.0.1",
    "edge-rtr-02.lab.internal": "10.0.0.2",
    "flaky-fw-03.lab.internal": "10.0.0.3",
}

_PING_RESULTS = {
    "10.0.0.1": {"loss_pct": 0, "avg_rtt_ms": 1.2},
    "10.0.0.2": {"loss_pct": 0, "avg_rtt_ms": 2.4},
    "10.0.0.3": {"loss_pct": 0, "avg_rtt_ms": 1.8},
    "10.0.0.99": {"loss_pct": 100, "avg_rtt_ms": None},  # silently unreachable
}


def _execute(device: str, command: str) -> str:
    if device not in _DEVICES:
        raise ValueError(f"Unknown device '{device}' (not in inventory).")

    if device == "dead-host-04":
        time.sleep(0.3)  # stand-in for the real multi-minute MCP timeout
        raise TimeoutError(f"Timed out waiting for '{device}' to respond (no route to host).")

    if device == "flaky-fw-03":
        _ATTEMPT_COUNTS[device] = _ATTEMPT_COUNTS.get(device, 0) + 1
        if _ATTEMPT_COUNTS[device] % 3 != 0:
            raise ConnectionError(f"Connection reset by '{device}' while sending command.")

    return f"{device}$ {command}\n-> ok (simulated output for '{command}')"


@mcp.tool()
def run_command(device: str, command: str) -> str:
    """Run a single CLI command on a single network device, e.g.
    device='core-sw-01', command='show interfaces status'."""
    return _execute(device, command)


@mcp.tool()
def run_commands(devices: List[str], commands: List[str]) -> str:
    """Run one command per device across multiple devices in one batch:
    devices[i] gets commands[i]. Per-device failures are captured in the
    returned JSON instead of raising, so a partial-failure batch still
    looks like a single successful tool call unless the caller inspects
    the payload -- worth noticing when you're staring at a trace."""
    if len(devices) != len(commands):
        raise ValueError("devices and commands must be the same length.")
    results = {}
    for device, command in zip(devices, commands):
        try:
            results[device] = _execute(device, command)
        except Exception as exc:  # noqa: BLE001 - intentionally captured as data, not raised
            results[device] = f"ERROR: {type(exc).__name__}: {exc}"
    return json.dumps(results, indent=2)


@mcp.tool()
def dns_lookup(hostname: str) -> str:
    """Resolve a hostname, e.g. 'core-sw-01.lab.internal'."""
    ip = _DNS_TABLE.get(hostname)
    if not ip:
        raise ValueError(f"NXDOMAIN: '{hostname}' does not resolve.")
    return f"{hostname} -> {ip}"


@mcp.tool()
def ping_check(target: str, count: int = 4) -> str:
    """Ping a single IP or every host in a small subnet (CIDR, e.g.
    '10.0.0.0/29'). Reports loss percentage and avg RTT per host. A host
    with 100% loss is still reported as normal output, not an error --
    read the numbers, don't just trust that the tool call was 'green'."""
    if "/" in target:
        import ipaddress

        network = ipaddress.ip_network(target, strict=False)
        hosts = [str(h) for h in list(network.hosts())[:8]]
    else:
        hosts = [target]

    report = {}
    for host in hosts:
        report[host] = _PING_RESULTS.get(
            host, {"loss_pct": 0, "avg_rtt_ms": 0.9}
        )
    return json.dumps({"count": count, "results": report}, indent=2)


if __name__ == "__main__":
    mcp.run(transport="stdio")
