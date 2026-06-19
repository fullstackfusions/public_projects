from __future__ import annotations

from fastapi import FastAPI
from shared.cors import add_cors
from shared.errors import ValidationError as AppValidationError, register_exception_handlers
from shared.middleware import install_middleware

from .config import get_settings
from .domain import investment as inv_domain
from .domain import mortgage as mort_domain
from .domain import salary as sal_domain
from .routers import health, investment, mortgage, salary
from .schemas.finance import ComputeRequest, ComputeResponse, InvestmentParams, MortgageParams, SalaryProjectionParams


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Finance API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    install_middleware(app)
    register_exception_handlers(app)
    add_cors(app, settings.cors_origins)

    app.include_router(health.router)
    app.include_router(investment.router)
    app.include_router(mortgage.router)
    app.include_router(salary.router)

    # Legacy single-dispatch endpoint — kept for frontend compatibility
    @app.post("/compute", response_model=ComputeResponse, tags=["legacy"])
    def compute(body: ComputeRequest) -> ComputeResponse:
        try:
            if body.kind == "investment":
                result = inv_domain.compute_investment(InvestmentParams(**body.params))
            elif body.kind == "mortgage":
                result = mort_domain.compute_mortgage(MortgageParams(**body.params))
            elif body.kind == "salary_projection":
                result = sal_domain.compute_salary_projection(SalaryProjectionParams(**body.params))
            else:
                raise AppValidationError(f"Unsupported kind: {body.kind}")
            return ComputeResponse(ok=True, result=result)
        except (ValueError, Exception) as exc:
            if isinstance(exc, AppValidationError):
                raise
            raise AppValidationError(str(exc)) from exc

    return app


app = create_app()
