from __future__ import annotations

from fastapi import APIRouter

from ..domain.mortgage import compute_mortgage
from ..schemas.finance import ComputeResponse, MortgageParams
from shared.errors import ValidationError as AppValidationError

router = APIRouter(prefix="/mortgage", tags=["mortgage"])


@router.post("/compute", response_model=ComputeResponse)
def compute(params: MortgageParams) -> ComputeResponse:
    try:
        result = compute_mortgage(params)
        return ComputeResponse(ok=True, result=result)
    except ValueError as exc:
        raise AppValidationError(str(exc)) from exc
