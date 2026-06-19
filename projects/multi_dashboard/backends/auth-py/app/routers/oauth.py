from __future__ import annotations

import base64
import hashlib
import secrets

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from shared.errors import AuthError, BadGatewayError
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..crud.users import upsert_google_user
from ..deps import get_db, get_redis
from ..oauth.google import GOOGLE_AUTH_URL, fetch_google_user_info, make_google_client
from ..oauth.state import OAuthStateStore
from ..routers.auth import _issue_tokens

router = APIRouter(prefix="/auth", tags=["oauth"])

_ALLOWED_RETURN_TO = {"/", "/dashboard", "/scheduler", "/tax", "/corporations"}


def _safe_return_to(return_to: str) -> str:
    return return_to if return_to in _ALLOWED_RETURN_TO else "/"


@router.get("/google/login")
async def google_login(
    return_to: str = Query("/"),
    redis: object = Depends(get_redis),
) -> RedirectResponse:
    settings = get_settings()
    if not settings.google_client_id:
        raise BadGatewayError("Google OAuth not configured", detail={})

    client = make_google_client(
        settings.google_client_id, settings.google_client_secret, settings.google_redirect_uri
    )

    # PKCE — generate code_verifier manually; authlib returns only (uri, state)
    code_verifier = secrets.token_urlsafe(96)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    # Generate our own opaque state token and store PKCE data keyed by it.
    # Pass it as `state` so Google echoes it back on callback — no duplicate param.
    state_token = secrets.token_urlsafe(32)
    store = OAuthStateStore(redis)  # type: ignore[arg-type]
    await store.save(
        {
            "state": state_token,
            "code_verifier": code_verifier,
            "return_to": _safe_return_to(return_to),
        },
        key=state_token,
    )

    uri, _ = client.create_authorization_url(
        GOOGLE_AUTH_URL,
        state=state_token,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    await client.aclose()

    return RedirectResponse(uri)


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    redis: object = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    settings = get_settings()

    store = OAuthStateStore(redis)  # type: ignore[arg-type]
    state_data = await store.pop(state)
    if state_data is None:
        raise AuthError("Invalid or expired OAuth state — possible CSRF")

    try:
        user_info = await fetch_google_user_info(
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            redirect_uri=settings.google_redirect_uri,
            code=code,
            code_verifier=state_data["code_verifier"],
        )
    except Exception as exc:
        raise BadGatewayError("Google token exchange failed", detail={"error": str(exc)}) from exc

    user = await upsert_google_user(
        db,
        google_sub=user_info["sub"],
        email=user_info["email"],
        name=user_info.get("name"),
        picture_url=user_info.get("picture"),
    )
    await db.commit()

    token = _issue_tokens(str(user.id), user.email, user.role, settings)
    return_to = state_data.get("return_to", "/")

    fragment = (
        f"access_token={token.access_token}"
        f"&refresh_token={token.refresh_token}"
        f"&return_to={return_to}"
    )
    return RedirectResponse(f"{settings.frontend_redirect_uri}#{fragment}")
