from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


def _new_id() -> str:
    return str(ObjectId())


class NilT2Doc(BaseModel):
    """Maps to the ``nil_t2_reports`` collection."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id, alias="_id")
    corp_id: str
    fiscal_year_end: str  # ISO date string "YYYY-MM-DD"
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    has_income: bool = False
    has_expenses: bool = False
    report: dict[str, Any] = Field(default_factory=dict)

    def to_mongo(self) -> dict:  # type: ignore[type-arg]
        return self.model_dump(by_alias=True)

    @classmethod
    def from_mongo(cls, doc: dict) -> NilT2Doc:  # type: ignore[type-arg]
        if doc and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return cls(**doc)
