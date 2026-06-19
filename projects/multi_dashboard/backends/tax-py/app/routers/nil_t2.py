from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends
from shared.auth import TokenClaims
from shared.errors import NotFoundError, ValidationError

from ..crud import corporations as corp_crud
from ..crud import nil_t2 as nil_t2_crud
from ..deps import get_current_user, get_db
from ..domain.nil_t2 import build_nil_t2_report
from ..schemas.nil_t2 import NilT2GenerateRequest, NilT2Out

router = APIRouter(prefix="/corporations", tags=["nil_t2"])


@router.post("/{corp_id}/nil-t2", response_model=NilT2Out)
async def generate_nil_t2(
    corp_id: str,
    payload: NilT2GenerateRequest,
    db: Any = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> NilT2Out:
    corp = await corp_crud.get_corporation(db, corp_id)
    if corp is None:
        raise NotFoundError("Corporation not found", detail={"corp_id": corp_id})
    if payload.has_income or payload.has_expenses:
        raise ValidationError(
            "Nil T2 requires no income and no expenses",
            detail={"has_income": payload.has_income, "has_expenses": payload.has_expenses},
        )
    report = build_nil_t2_report(corp, payload.fiscal_year_end)
    record = await nil_t2_crud.upsert_nil_t2(
        db,
        corp_id=corp_id,
        fiscal_year_end=payload.fiscal_year_end.isoformat(),
        has_income=payload.has_income,
        has_expenses=payload.has_expenses,
        report=report,
    )
    return NilT2Out(**record.model_dump(by_alias=False))


@router.get("/{corp_id}/nil-t2/{fiscal_year_end}", response_model=NilT2Out)
async def read_nil_t2(
    corp_id: str,
    fiscal_year_end: date,
    db: Any = Depends(get_db),
    _user: TokenClaims = Depends(get_current_user),
) -> NilT2Out:
    record = await nil_t2_crud.get_nil_t2(db, corp_id, fiscal_year_end.isoformat())
    if record is None:
        raise NotFoundError(
            "Nil T2 report not found",
            detail={"corp_id": corp_id, "fiscal_year_end": fiscal_year_end.isoformat()},
        )
    return NilT2Out(**record.model_dump(by_alias=False))
