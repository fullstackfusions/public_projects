"""
Shared reporting helpers: pretty tables (rich, with a plain fallback) and
results JSON I/O. Kept dependency-light so the runners stay readable.
"""

from __future__ import annotations

import json
from pathlib import Path


def print_table(title: str, headers: list[str], rows: list[list],
                caption: str | None = None):
    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box

        t = Table(title=title, box=box.ROUNDED, show_lines=False, caption=caption)
        for i, h in enumerate(headers):
            t.add_column(h, justify="left" if i == 0 else "right",
                         style="cyan" if i == 0 else None)
        for r in rows:
            t.add_row(*[str(c) for c in r])
        Console().print(t)
    except ImportError:
        _plain(title, headers, rows, caption)


def _plain(title, headers, rows, caption):
    print(f"\n=== {title} ===")
    widths = [max(len(str(headers[i])), *(len(str(r[i])) for r in rows)) if rows
              else len(str(headers[i])) for i in range(len(headers))]
    line = "  ".join(str(headers[i]).ljust(widths[i]) for i in range(len(headers)))
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(str(r[i]).ljust(widths[i]) for i in range(len(headers))))
    if caption:
        print(caption)


def save_results(path: str | Path, payload: dict):
    Path(path).write_text(json.dumps(payload, indent=2, default=str))
    print(f"\nSaved → {path}")
