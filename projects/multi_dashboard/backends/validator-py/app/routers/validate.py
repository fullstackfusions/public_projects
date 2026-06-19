from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Query

from ..domain import rules
from ..schemas.validation import PaginatedTasksResponse

router = APIRouter(tags=["validation"])


@router.get("/tasks", response_model=PaginatedTasksResponse)
def get_validation_tasks(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(5, ge=1, le=50, description="Items per page"),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[Literal["asc", "desc"]] = Query(None),
    change_request_id: Optional[str] = Query(None),
    change_description: Optional[str] = Query(None),
    change_status: Optional[str] = Query(None),
    path: Optional[str] = Query(None),
) -> PaginatedTasksResponse:
    tasks = rules.get_or_create_validation_tasks()
    filtered = list(tasks)

    if change_request_id:
        filtered = [t for t in filtered if change_request_id.lower() in t.change_request_id.lower()]
    if change_description:
        filtered = [t for t in filtered if change_description.lower() in t.change_description.lower()]
    if change_status:
        filtered = [t for t in filtered if change_status.lower() in t.change_status.lower()]
    if path:
        filtered = [t for t in filtered if path.lower() in t.path.lower()]

    if sort_by and sort_order:
        reverse = sort_order == "desc"
        valid_cols = {"change_request_id", "change_description", "change_status", "created_at", "path"}
        if sort_by in valid_cols:
            filtered.sort(key=lambda t: getattr(t, sort_by, ""), reverse=reverse)

    total = len(filtered)
    total_pages = max(1, (total + page_size - 1) // page_size)
    start = (page - 1) * page_size
    paginated = filtered[start : start + page_size]

    return PaginatedTasksResponse(
        tasks=paginated, total=total, page=page, page_size=page_size, total_pages=total_pages
    )


@router.delete("/tasks/cache")
def clear_tasks_cache() -> dict:
    rules.clear_tasks_cache()
    return {"message": "Tasks cache cleared"}
