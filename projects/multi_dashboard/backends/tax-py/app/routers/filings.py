from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from shared.auth import TokenClaims
from shared.errors import NotFoundError

from ..crud import corporations as corp_crud
from ..crud import filings as filing_crud
from ..deps import get_current_user, get_db
from ..schemas.filings import FilingStatusUpdate, TaxFilingOut, UpcomingFiling

router = APIRouter(tags=["filings"])


@router.get("/filings/upcoming", response_model=list[UpcomingFiling])
async def upcoming_filings(
    db: Any = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> list[UpcomingFiling]:
    today = date.today()
    records = await filing_crud.list_upcoming_filings(db)
    corps = {c.id: c for c in await corp_crud.list_corporations(db)}
    out: list[UpcomingFiling] = []
    for r in records:
        corp = corps.get(r.corp_id)
        due = date.fromisoformat(r.due_date)
        out.append(
            UpcomingFiling(
                **r.model_dump(by_alias=False),
                corporation_name=corp.name if corp else "Unknown",
                days_remaining=(due - today).days,
            )
        )
    return out


@router.put(
    "/corporations/{corp_id}/filings/{filing_id}",
    response_model=TaxFilingOut,
)
async def update_filing(
    corp_id: str,
    filing_id: str,
    payload: FilingStatusUpdate,
    db: Any = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> TaxFilingOut:
    filing = await filing_crud.get_filing(db, filing_id)
    if filing is None or filing.corp_id != corp_id:
        raise NotFoundError("Filing not found", detail={"filing_id": filing_id})
    updated = await filing_crud.update_filing_status(db, filing_id, payload.status)
    return TaxFilingOut(**updated.model_dump(by_alias=False))  # type: ignore[union-attr]
