from config import BENCHMARK_COMMANDS
from utils import run_shell, count_tokens, savings_pct
from shell_tools import rtk_available


def benchmark_command(command: str) -> dict:
    raw_out = run_shell(command)
    raw_tokens = count_tokens(raw_out)

    rtk_out = rtk_tokens = pct = None
    if rtk_available():
        rtk_out = run_shell(f"rtk {command}")
        rtk_tokens = count_tokens(rtk_out)
        pct = savings_pct(raw_tokens, rtk_tokens)

    return {
        "command": command,
        "raw_tokens": raw_tokens,
        "rtk_tokens": rtk_tokens,
        "savings_pct": pct,
    }


def run_benchmark(commands: list[str] | None = None) -> list[dict]:
    return [benchmark_command(cmd) for cmd in (commands or BENCHMARK_COMMANDS)]
