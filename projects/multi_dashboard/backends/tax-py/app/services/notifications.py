"""Tax filing notification producer.

Calls notification-py's POST /notify/template endpoint after setup_reminders.
Best-effort: any HTTP failure is logged and swallowed — it NEVER aborts the
calling request.

Mirrors the pattern in reminders.py (httpx.AsyncClient, 5s timeout,
best-effort exception handling).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from shared.logging import get_logger

from ..models.corporation import CorporationDoc
from ..models.filing import TaxFilingDoc

if TYPE_CHECKING:
    from ..config import Settings

logger = get_logger(__name__)

# Reminder offsets (days before due date) for which we send notifications.
# Matches the scheduler reminder offsets defined in tax_dates.py.
_NOTIFICATION_OFFSETS: dict[str, list[int]] = {
    "annual_return": [90, 60, 30, 7],
    "t2": [90, 60, 30, 14],
    # GST/HST quarterly
    "gst_hst_q1": [30, 14, 7, 1],
    "gst_hst_q2": [30, 14, 7, 1],
    "gst_hst_q3": [30, 14, 7, 1],
    "gst_hst_q4": [30, 14, 7, 1],
}


async def notify_filing_deadlines(
    corp: CorporationDoc,
    filings: list[TaxFilingDoc],
    user_id: str,
    auth_token: str,
    settings: Settings,
) -> None:
    """Fan notifications out for all filings for a corporation.

    Sends one /notify/template call per (filing × offset) combination.
    ``auth_token`` is the raw JWT from the incoming HTTP request — forwarded
    so the notification service can verify it locally.
    """
    notification_url = getattr(settings, "notification_api_url", None)
    if not notification_url:
        logger.debug("NOTIFICATION_API_URL not set — skipping notifications")
        return

    async with httpx.AsyncClient(base_url=notification_url, timeout=5.0) as client:
        for filing in filings:
            offsets = _NOTIFICATION_OFFSETS.get(filing.filing_type, [30, 7])
            for days_before in offsets:
                dedup_key = (
                    f"tax_deadline_{user_id}_{filing.filing_type}"
                    f"_{filing.period_label}_{days_before}"
                )
                try:
                    await client.post(
                        "/notify/template",
                        json={
                            "user_id": user_id,
                            "template_id": "tax_deadline",
                            "dedup_key": dedup_key,
                            "context": {
                                "corp_name": corp.name,
                                "filing_type": filing.filing_type,
                                "period_label": filing.period_label,
                                "due_date": filing.due_date,
                                "days_before": days_before,
                            },
                        },
                        headers={"Authorization": f"Bearer {auth_token}"},
                    )
                except httpx.HTTPError as exc:
                    logger.warning(
                        "Notification dispatch failed (best-effort, continuing)",
                        extra={
                            "filing_type": filing.filing_type,
                            "dedup_key": dedup_key,
                            "error": str(exc),
                        },
                    )
                    continue  # never abort the calling request
