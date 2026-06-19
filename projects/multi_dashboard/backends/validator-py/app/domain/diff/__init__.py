from __future__ import annotations

import random
from typing import Dict, List

from ...schemas.validation import CommandOutput, StreamingMetadata, ValidationDeviceResult


def generate_dummy_output(size_bytes: int) -> str:
    lines = []
    current_size = 0

    line_templates = [
        lambda: f"Interface GigabitEthernet{random.randint(0,9)}/{random.randint(0,48)} is up, line protocol is up",
        lambda: f"  Hardware is GigabitEthernet, address is {random.randint(0,65535):04x}.{random.randint(0,65535):04x}.{random.randint(0,65535):04x}",
        lambda: f"  Internet address is {random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}/{random.randint(8,30)}",
        lambda: f"  MTU {random.randint(1500,9000)} bytes, BW {random.randint(100,10000)} Kbit/sec, DLY {random.randint(10,1000)} usec",
        lambda: "  Encapsulation ARPA, loopback not set",
        lambda: f"  Last input {random.randint(0,23)}:{random.randint(0,59):02d}:{random.randint(0,59):02d}, output {random.randint(0,23)}:{random.randint(0,59):02d}:{random.randint(0,59):02d}",
        lambda: f"  {random.randint(1000,999999)} packets input, {random.randint(10000,9999999)} bytes, {random.randint(0,100)} no buffer",
        lambda: f"  {random.randint(1000,999999)} packets output, {random.randint(10000,9999999)} bytes, {random.randint(0,10)} underruns",
        lambda: f"BGP router identifier {random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}, local AS number {random.randint(1,65535)}",
        lambda: "Neighbor        V           AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd",
        lambda: f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}     4        {random.randint(100,65000)}   {random.randint(1000,9999)}    {random.randint(1000,9999)}        0    0    0 {random.randint(0,23)}:{random.randint(0,59):02d}:{random.randint(0,59):02d}        {random.randint(0,1000)}",
        lambda: f"Route distinguisher: {random.randint(100,65000)}:{random.randint(1,999)}",
        lambda: "  Network          Next Hop            Metric LocPrf Weight Path",
        lambda: f"*>{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}/{random.randint(8,32)}    {random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}              {random.randint(0,100)}      {random.randint(100,200)}      0 {random.randint(100,999)} {random.randint(100,999)} {random.randint(100,999)}",
        lambda: f"Total number of prefixes {random.randint(1,5000)}",
    ]

    while current_size < size_bytes:
        template_func = random.choice(line_templates)
        line = template_func()
        lines.append(line)
        current_size += len(line) + 1

    return "\n".join(lines)


def generate_device_result(change_request_id: str, device_id: str) -> ValidationDeviceResult:
    commands = [
        ("show version", 3000),
        ("show ip route", 9000),
        ("show ip interface", 14000),
        ("show bgp summary", 6000),
    ]

    pre_check: List[CommandOutput] = []
    post_check: List[CommandOutput] = []

    for cmd, size in commands:
        pre_check.append(CommandOutput(command=cmd, output=generate_dummy_output(size), size=str(size)))
        post_check.append(CommandOutput(command=cmd, output=generate_dummy_output(size), size=str(size)))

    return ValidationDeviceResult(
        change_request_id=change_request_id,
        device_id=device_id,
        device_name=f"Router_{device_id}",
        device_status="Success",
        validation_status="Passed",
        pre_check_output=pre_check,
        post_check_output=post_check,
        llm_analysis="Analysis: Configuration changes applied successfully. No critical issues detected.",
        streaming_metadata=StreamingMetadata(
            stream_id=f"stream_{device_id}_{random.randint(1000, 9999)}"
        ),
    )


# In-memory caches — intentionally module-level (single process, no persistence needed)
_device_results_cache: Dict[str, ValidationDeviceResult] = {}
_presigned_url_content_cache: Dict[str, str] = {}


def get_or_create_device_result(change_request_id: str, device_id: str) -> ValidationDeviceResult:
    cache_key = f"{change_request_id}:{device_id}"
    if cache_key not in _device_results_cache:
        _device_results_cache[cache_key] = generate_device_result(change_request_id, device_id)
    return _device_results_cache[cache_key]
