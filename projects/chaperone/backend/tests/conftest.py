import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "tests" / "fixtures"


@pytest.fixture(scope="session")
def day0():
    """90 real CloudTrail events from Day 0 (agent building the hello-world site),
    sanitized: account 111122223333, documentation IPs, tokens redacted."""
    return json.loads((FIXTURES / "day0_agent_events.json").read_text())


def by_name(events, name):
    return [e for e in events if e["eventName"] == name]
