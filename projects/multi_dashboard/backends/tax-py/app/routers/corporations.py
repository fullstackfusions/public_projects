from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Request, Response, status
from shared.auth import TokenClaims
from shared.errors import NotFoundError

from ..config import get_settings
from ..crud import corporations as corp_crud
from ..crud import filings as filing_crud
from ..deps import get_current_user, get_db
from ..domain import tax_dates
from ..schemas.corporations import (
    CorporationCreate,
    CorporationOut,
    CorporationUpdate,
    CorporationWithFilings,
)
from ..schemas.filings import FilingScheduleItem, TaxFilingOut
from ..services import notifications, reminders

router = APIRouter(prefix="/corporations", tags=["corporations"])


@router.get("", response_model=list[CorporationOut])
async def list_corporations(
    db: Any = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> list[CorporationOut]:
    corps = await corp_crud.list_corporations(db)
    return [CorporationOut(**c.model_dump(by_alias=False)) for c in corps]


@router.post("", response_model=CorporationOut, status_code=status.HTTP_201_CREATED)
async def create_corporation(
    payload: CorporationCreate,
    db: Any = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> CorporationOut:
    data = payload.model_dump()
    data["incorporation_date"] = data["incorporation_date"].isoformat()
    corp = await corp_crud.create_corporation(db, data)
    return CorporationOut(**corp.model_dump(by_alias=False))


@router.get("/{corp_id}", response_model=CorporationWithFilings)
async def read_corporation(
    corp_id: str,
    db: Any = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> CorporationWithFilings:
    corp = await corp_crud.get_corporation(db, corp_id)
    if corp is None:
        raise NotFoundError("Corporation not found", detail={"corp_id": corp_id})
    filings = await filing_crud.list_filings_for_corp(db, corp_id)
    filings_out = [TaxFilingOut(**f.model_dump(by_alias=False)) for f in filings]
    return CorporationWithFilings(**corp.model_dump(by_alias=False), filings=filings_out)


@router.put("/{corp_id}", response_model=CorporationOut)
async def update_corporation(
    corp_id: str,
    payload: CorporationUpdate,
    db: Any = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> CorporationOut:
    corp = await corp_crud.get_corporation(db, corp_id)
    if corp is None:
        raise NotFoundError("Corporation not found", detail={"corp_id": corp_id})
    updates = payload.model_dump(exclude_unset=True)
    if "incorporation_date" in updates and updates["incorporation_date"] is not None:
        updates["incorporation_date"] = updates["incorporation_date"].isoformat()
    updated = await corp_crud.update_corporation(db, corp_id, updates)
    return CorporationOut(**updated.model_dump(by_alias=False))  # type: ignore[union-attr]


@router.delete("/{corp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_corporation(
    corp_id: str,
    db: Any = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> Response:
    corp = await corp_crud.get_corporation(db, corp_id)
    if corp is None:
        raise NotFoundError("Corporation not found", detail={"corp_id": corp_id})
    await corp_crud.delete_corporation(db, corp_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{corp_id}/filing-schedule", response_model=list[FilingScheduleItem])
async def filing_schedule(
    corp_id: str,
    db: Any = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> list[FilingScheduleItem]:
    corp = await corp_crud.get_corporation(db, corp_id)
    if corp is None:
        raise NotFoundError("Corporation not found", detail={"corp_id": corp_id})
    inc_date = date.fromisoformat(corp.incorporation_date)
    schedule = tax_dates.compute_full_schedule(
        inc_date, corp.fiscal_year_end_month, date.today()
    )
    return [
        FilingScheduleItem(
            filing_type=item.filing_type,
            period_label=item.period_label,
            due_date=item.due_date,
        )
        for item in schedule
    ]


@router.post("/{corp_id}/setup-reminders", response_model=list[TaxFilingOut])
async def setup_reminders_endpoint(
    corp_id: str,
    request: Request,
    db: Any = Depends(get_db),
    user: TokenClaims = Depends(get_current_user),
) -> list[TaxFilingOut]:
    settings = get_settings()
    raw_token = (request.headers.get("Authorization", "") or "").removeprefix("Bearer ").strip()
    filings = await reminders.setup_reminders(corp_id, db, settings, auth_token=raw_token)

    # Best-effort: fan out notifications via notification-py.
    corp = await corp_crud.get_corporation(db, corp_id)
    if corp is not None and raw_token:
        await notifications.notify_filing_deadlines(
            corp=corp,
            filings=filings,
            user_id=user.sub,
            auth_token=raw_token,
            settings=settings,
        )

    return [TaxFilingOut(**f.model_dump(by_alias=False)) for f in filings]
