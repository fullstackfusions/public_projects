import subprocess
import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def savings_pct(raw: int, compressed: int) -> float:
    if raw == 0:
        return 0.0
    return (raw - compressed) / raw * 100


def run_shell(command: str) -> str:
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = result.stdout
    if result.returncode != 0 and result.stderr:
        output += result.stderr
    return output
