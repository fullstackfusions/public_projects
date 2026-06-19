from __future__ import annotations

from typing import Any

from bson import ObjectId

from ..models.corporation import CorporationDoc


async def list_corporations(db: Any) -> list[CorporationDoc]:
    docs = await db["corporations"].find({}).sort("name", 1).to_list(None)
    return [CorporationDoc.from_mongo(d) for d in docs]


async def get_corporation(db: Any, corp_id: str) -> CorporationDoc | None:
    if not ObjectId.is_valid(corp_id):
        return None
    # _id is stored as a string (from _new_id()); query with the string directly.
    doc = await db["corporations"].find_one({"_id": corp_id})
    return CorporationDoc.from_mongo(doc) if doc else None


async def create_corporation(db: Any, data: dict[str, Any]) -> CorporationDoc:
    doc = CorporationDoc(**data)
    await db["corporations"].insert_one(doc.to_mongo())
    return doc


async def update_corporation(
    db: Any, corp_id: str, updates: dict[str, Any]
) -> CorporationDoc | None:
    if not ObjectId.is_valid(corp_id):
        return None
    await db["corporations"].update_one({"_id": corp_id}, {"$set": updates})
    return await get_corporation(db, corp_id)


async def delete_corporation(db: Any, corp_id: str) -> bool:
    if not ObjectId.is_valid(corp_id):
        return False
    await db["corporations"].delete_one({"_id": corp_id})
    # Cascade: remove all filings and nil T2 reports for this corp
    await db["tax_filing_records"].delete_many({"corp_id": corp_id})
    await db["nil_t2_reports"].delete_many({"corp_id": corp_id})
    return True
