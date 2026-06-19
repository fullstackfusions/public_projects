from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import List

from ...schemas.validation import ValidationTask

_STATUSES = ["Pending", "In Progress", "Completed", "Failed", "Cancelled"]
_DESCRIPTIONS = [
    "Update firewall rules for DMZ segment",
    "Configure BGP peering with ISP",
    "Migrate VLAN configuration to new switch",
    "Implement QoS policies for VoIP traffic",
    "Upgrade router firmware to latest version",
    "Add new subnet for IoT devices",
    "Configure OSPF area for branch office",
    "Update ACLs for compliance requirements",
    "Enable SNMP monitoring on core switches",
    "Configure port security on access ports",
    "Set up DHCP relay for remote site",
    "Implement HSRP for gateway redundancy",
    "Configure NTP synchronization cluster",
    "Update DNS server entries",
    "Enable syslog forwarding to SIEM",
    "Configure RADIUS authentication",
    "Add static routes for partner network",
    "Update interface descriptions",
    "Enable CDP/LLDP on uplinks",
    "Configure spanning-tree root bridge",
]
_PATHS = [
    "/network/core/router-01",
    "/network/core/router-02",
    "/network/distribution/switch-01",
    "/network/distribution/switch-02",
    "/network/access/switch-floor-1",
    "/network/access/switch-floor-2",
    "/network/dmz/firewall-01",
    "/network/dmz/firewall-02",
    "/network/branch/site-001",
    "/network/branch/site-002",
]

_tasks_cache: List[ValidationTask] = []


def generate_validation_tasks(count: int = 20) -> List[ValidationTask]:
    tasks: List[ValidationTask] = []
    base_date = datetime.now()
    for i in range(count):
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        created = base_date - timedelta(days=days_ago, hours=hours_ago)
        tasks.append(
            ValidationTask(
                change_request_id=f"CR{random.randint(100000, 999999)}",
                change_description=_DESCRIPTIONS[i % len(_DESCRIPTIONS)],
                change_status=random.choice(_STATUSES),
                created_at=created.strftime("%Y-%m-%d %H:%M:%S"),
                path=random.choice(_PATHS),
            )
        )
    return tasks


def get_or_create_validation_tasks() -> List[ValidationTask]:
    global _tasks_cache
    if not _tasks_cache:
        _tasks_cache = generate_validation_tasks(20)
    return _tasks_cache


def clear_tasks_cache() -> None:
    global _tasks_cache
    _tasks_cache = []
