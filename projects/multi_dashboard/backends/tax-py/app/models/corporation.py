from __future__ import annotations

from datetime import UTC, datetime

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


def _new_id() -> str:
    return str(ObjectId())


class CorporationDoc(BaseModel):
    """Maps to the ``corporations`` collection."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id, alias="_id")
    name: str
    corp_number: str | None = None
    business_number: str | None = None
    gst_hst_number: str | None = None
    province: str | None = None
    fiscal_year_end_month: int
    incorporation_date: str  # ISO date string "YYYY-MM-DD"
    contact_email: str | None = None
    contact_phone: str | None = None  # E.164, e.g. +14155552671 — used for WhatsApp/SMS notifications
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_mongo(self) -> dict:  # type: ignore[type-arg]
        return self.model_dump(by_alias=True)

    @classmethod
    def from_mongo(cls, doc: dict) -> CorporationDoc:  # type: ignore[type-arg]
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)
