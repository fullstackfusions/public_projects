from __future__ import annotations

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


def _new_id() -> str:
    return str(ObjectId())


class TaxFilingDoc(BaseModel):
    """Maps to the ``tax_filing_records`` collection."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id, alias="_id")
    corp_id: str  # string ObjectId ref to corporations._id
    filing_type: str  # "annual_return" | "t2" | "gst_hst_q1"…
    period_label: str
    due_date: str  # ISO date string "YYYY-MM-DD"
    status: str = "pending"  # "pending" | "filed" | "overdue"
    scheduler_event_id: int | None = None

    def to_mongo(self) -> dict:  # type: ignore[type-arg]
        return self.model_dump(by_alias=True)

    @classmethod
    def from_mongo(cls, doc: dict) -> TaxFilingDoc:  # type: ignore[type-arg]
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)
