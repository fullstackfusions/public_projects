from __future__ import annotations

from datetime import date
from typing import Any

from bson import ObjectId

from ..models.filing import TaxFilingDoc


async def list_filings_for_corp(db: Any, corp_id: str) -> list[TaxFilingDoc]:
    docs = await db["tax_filing_records"].find({"corp_id": corp_id}).sort("due_date", 1).to_list(None)
    return [TaxFilingDoc.from_mongo(d) for d in docs]


async def get_filing(db: Any, filing_id: str) -> TaxFilingDoc | None:
    if not ObjectId.is_valid(filing_id):
        return None
    # _id is stored as a string; query with the string directly.
    doc = await db["tax_filing_records"].find_one({"_id": filing_id})
    return TaxFilingDoc.from_mongo(doc) if doc else None


async def upsert_filing(
    db: Any,
    corp_id: str,
    filing_type: str,
    period_label: str,
    due_date: date,
) -> TaxFilingDoc:
    """Insert or update a filing record. Preserves existing scheduler_event_id and status."""
    filter_ = {"corp_id": corp_id, "filing_type": filing_type, "period_label": period_label}
    existing = await db["tax_filing_records"].find_one(filter_)
    if existing:
        await db["tax_filing_records"].update_one(
            filter_, {"$set": {"due_date": due_date.isoformat()}}
        )
        updated = await db["tax_filing_records"].find_one(filter_)
        assert updated is not None
        return TaxFilingDoc.from_mongo(updated)

    doc = TaxFilingDoc(
        corp_id=corp_id,
        filing_type=filing_type,
        period_label=period_label,
        due_date=due_date.isoformat(),
        status="pending",
    )
    result = await db["tax_filing_records"].insert_one(doc.to_mongo())
    doc.id = str(result.inserted_id)
    return doc


async def update_filing_status(
    db: Any, filing_id: str, status_value: str
) -> TaxFilingDoc | None:
    if not ObjectId.is_valid(filing_id):
        return None
    await db["tax_filing_records"].update_one(
        {"_id": filing_id},
        {"$set": {"status": status_value}},
    )
    return await get_filing(db, filing_id)


async def set_scheduler_event_id(db: Any, filing_id: str, event_id: int) -> None:
    if ObjectId.is_valid(filing_id):
        await db["tax_filing_records"].update_one(
            {"_id": filing_id},
            {"$set": {"scheduler_event_id": event_id}},
        )


async def delete_stale_filings(
    db: Any, corp_id: str, current_keys: set[tuple[str, str]]
) -> None:
    """Remove non-filed filings whose (filing_type, period_label) is no longer current."""
    docs = await db["tax_filing_records"].find(
        {"corp_id": corp_id, "status": {"$ne": "filed"}}
    ).to_list(None)
    stale_ids = [
        d["_id"]
        for d in docs
        if (d["filing_type"], d["period_label"]) not in current_keys
    ]
    if stale_ids:
        await db["tax_filing_records"].delete_many({"_id": {"$in": stale_ids}})


async def list_upcoming_filings(db: Any) -> list[TaxFilingDoc]:
    docs = await db["tax_filing_records"].find(
        {"status": {"$ne": "filed"}}
    ).sort("due_date", 1).to_list(None)
    return [TaxFilingDoc.from_mongo(d) for d in docs]
