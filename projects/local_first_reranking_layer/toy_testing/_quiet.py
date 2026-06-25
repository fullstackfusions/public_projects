"""
Silence the third-party noise (HF download bars, httpx request logs, Headroom
INFO chatter) so the experiment tables are the only thing on screen. Import and
call quiet() as the first line of each runner's main(), before any model loads.
"""

from __future__ import annotations

import logging
import os
import warnings


def quiet() -> None:
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")

    warnings.filterwarnings("ignore")
    logging.disable(logging.INFO)  # drops httpx + headroom + ST INFO lines
    for name in ("httpx", "headroom", "sentence_transformers", "transformers", "urllib3"):
        logging.getLogger(name).setLevel(logging.WARNING)

    try:
        from transformers.utils.logging import set_verbosity_error, disable_progress_bar
        set_verbosity_error()
        disable_progress_bar()
    except Exception:
        pass
