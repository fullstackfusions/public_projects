from __future__ import annotations

from fastapi import APIRouter

from ..domain.investment import compute_investment
from ..schemas.finance import ComputeResponse, InvestmentParams
from shared.errors import ValidationError as AppValidationError

router = APIRouter(prefix="/investment", tags=["investment"])


@router.post("/compute", response_model=ComputeResponse)
def compute(params: InvestmentParams) -> ComputeResponse:
    try:
        result = compute_investment(params)
        return ComputeResponse(ok=True, result=result)
    except ValueError as exc:
        raise AppValidationError(str(exc)) from exc
