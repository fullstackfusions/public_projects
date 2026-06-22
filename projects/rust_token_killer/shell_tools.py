import shutil
from dataclasses import dataclass, field
from langchain_core.tools import tool
from utils import run_shell, count_tokens


@dataclass
class CallRecord:
    command: str
    tokens: int


@dataclass
class ToolTracker:
    mode: str
    records: list = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return sum(r.tokens for r in self.records)

    def record(self, command: str, output: str):
        self.records.append(CallRecord(command, count_tokens(output)))

    def reset(self):
        self.records.clear()


raw_tracker = ToolTracker("raw")
rtk_tracker = ToolTracker("rtk")


def rtk_available() -> bool:
    return shutil.which("rtk") is not None


@tool
def bash_raw(command: str) -> str:
    """Execute a shell command and return the full raw output.
    Use for: git, ls, find, pytest, cargo, docker, kubectl and other dev tools."""
    output = run_shell(command)
    raw_tracker.record(command, output)
    return output


@tool
def bash_rtk(command: str) -> str:
    """Execute a shell command through RTK compression for token-optimized output.
    Use for: git, ls, find, pytest, cargo, docker, kubectl and other dev tools."""
    if not rtk_available():
        raise RuntimeError("RTK not installed. Run: brew install rtk")
    output = run_shell(f"rtk {command}")
    rtk_tracker.record(command, output)
    return output
