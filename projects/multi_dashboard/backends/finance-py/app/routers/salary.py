from __future__ import annotations

from fastapi import APIRouter

from ..domain.salary import compute_salary_projection
from ..schemas.finance import ComputeResponse, SalaryProjectionParams
from shared.errors import ValidationError as AppValidationError

router = APIRouter(prefix="/salary", tags=["salary"])


@router.post("/compute", response_model=ComputeResponse)
def compute(params: SalaryProjectionParams) -> ComputeResponse:
    try:
        result = compute_salary_projection(params)
        return ComputeResponse(ok=True, result=result)
    except ValueError as exc:
        raise AppValidationError(str(exc)) from exc
