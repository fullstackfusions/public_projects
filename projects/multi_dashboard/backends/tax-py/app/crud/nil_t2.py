from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from ..models.nil_t2 import NilT2Doc


async def get_nil_t2(
    db: Any, corp_id: str, fiscal_year_end: str
) -> NilT2Doc | None:
    doc = await db["nil_t2_reports"].find_one(
        {"corp_id": corp_id, "fiscal_year_end": fiscal_year_end}
    )
    return NilT2Doc.from_mongo(doc) if doc else None


async def upsert_nil_t2(
    db: Any,
    corp_id: str,
    fiscal_year_end: str,
    has_income: bool,
    has_expenses: bool,
    report: dict[str, Any],
) -> NilT2Doc:
    now = datetime.now(UTC).isoformat()
    existing = await db["nil_t2_reports"].find_one(
        {"corp_id": corp_id, "fiscal_year_end": fiscal_year_end}
    )
    if existing:
        await db["nil_t2_reports"].update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "has_income": has_income,
                    "has_expenses": has_expenses,
                    "report": report,
                    "generated_at": now,
                }
            },
        )
        updated = await db["nil_t2_reports"].find_one({"_id": existing["_id"]})
        assert updated is not None
        return NilT2Doc.from_mongo(updated)

    doc = NilT2Doc(
        corp_id=corp_id,
        fiscal_year_end=fiscal_year_end,
        has_income=has_income,
        has_expenses=has_expenses,
        report=report,
    )
    result = await db["nil_t2_reports"].insert_one(doc.to_mongo())
    doc.id = str(result.inserted_id)
    return doc
