from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any

import httpx
from shared.errors import BadGatewayError, NotFoundError

from ..crud import corporations as corp_crud
from ..crud import filings as filing_crud
from ..domain import tax_dates
from ..models.filing import TaxFilingDoc

if TYPE_CHECKING:
    from ..config import Settings


async def setup_reminders(
    corp_id: str,
    db: Any,
    settings: Settings,
    auth_token: str = "",
) -> list[TaxFilingDoc]:
    """Compute the full tax schedule for a corporation, upsert filing records, and
    create calendar events + reminders in the scheduler service for any filing that
    doesn't already have a linked event.

    Returns the full list of filing docs for the corporation after the operation.
    """
    corp = await corp_crud.get_corporation(db, corp_id)
    if corp is None:
        raise NotFoundError("Corporation not found", detail={"corp_id": corp_id})

    inc_date = date.fromisoformat(corp.incorporation_date)
    schedule = tax_dates.compute_full_schedule(
        inc_date, corp.fiscal_year_end_month, date.today()
    )

    # Prune stale (non-filed) records not in the current schedule
    current_keys = {(item.filing_type, item.period_label) for item in schedule}
    await filing_crud.delete_stale_filings(db, corp_id, current_keys)

    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    async with httpx.AsyncClient(
        base_url=settings.scheduler_api_url, timeout=5.0, headers=headers
    ) as client:
        for item in schedule:
            filing = await filing_crud.upsert_filing(
                db, corp_id, item.filing_type, item.period_label, item.due_date
            )

            if filing.scheduler_event_id is not None:
                continue  # already linked — skip scheduler call

            event_start = datetime.combine(item.due_date, time(9, 0))
            event_end = datetime.combine(item.due_date, time(10, 0))
            event_payload = {
                "title": f"{corp.name} — {item.period_label} due",
                "description": (
                    f"{item.filing_type.replace('_', ' ').title()} filing for "
                    f"{corp.name}. Due {item.due_date.isoformat()}."
                ),
                "start_time": event_start.isoformat(),
                "end_time": event_end.isoformat(),
                "location": None,
            }

            try:
                resp = await client.post("/events", json=event_payload)
                resp.raise_for_status()
                event = resp.json()
            except httpx.HTTPError as exc:
                raise BadGatewayError(
                    "Failed to create scheduler event",
                    detail={"error": str(exc), "filing_type": item.filing_type},
                ) from exc

            await filing_crud.set_scheduler_event_id(db, filing.id, event["id"])

            for offset in tax_dates.reminder_offsets(item.filing_type):
                remind_at = datetime.combine(
                    item.due_date - timedelta(days=offset), time(9, 0)
                )
                try:
                    await client.post(
                        "/reminders",
                        json={
                            "event_id": event["id"],
                            "message": f"{item.period_label} due in {offset} days",
                            "remind_at": remind_at.isoformat(),
                        },
                    )
                except httpx.HTTPError:
                    continue  # best-effort; reminder failures don't abort the operation

    return await filing_crud.list_filings_for_corp(db, corp_id)
