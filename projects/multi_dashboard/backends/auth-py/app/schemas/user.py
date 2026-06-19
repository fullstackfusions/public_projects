from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class UserOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    email: str
    name: str | None = None
    picture_url: str | None = None
    role: str
    is_active: bool


class UserCreate(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str | None = None
    role: str = "user"
