from __future__ import annotations

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    sub: str
    role: str = "user"
    email: str = ""


class RefreshRequest(BaseModel):
    refresh_token: str
