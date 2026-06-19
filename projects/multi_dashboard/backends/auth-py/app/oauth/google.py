"""Google OAuth 2.0 + PKCE client using authlib."""
from __future__ import annotations

from typing import Any

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import JsonWebKey
from authlib.jose import jwt as authlib_jwt


def make_google_client(client_id: str, client_secret: str, redirect_uri: str) -> AsyncOAuth2Client:
    return AsyncOAuth2Client(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope="openid email profile",
    )


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_URI = "https://www.googleapis.com/oauth2/v3/certs"


async def fetch_google_user_info(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    code: str,
    code_verifier: str,
) -> dict[str, Any]:
    """Exchange the auth code for tokens and verify the ID token against Google JWKS.

    Returns the verified claims dict (sub, email, email_verified, name, picture).
    """
    client = make_google_client(client_id, client_secret, redirect_uri)
    token_response = await client.fetch_token(
        GOOGLE_TOKEN_URL,
        code=code,
        code_verifier=code_verifier,
    )
    await client.aclose()

    id_token = token_response.get("id_token")
    if not id_token:
        raise ValueError("Google did not return an id_token")

    # Fetch Google's public JWKS to verify the id_token signature (RS256).
    async with httpx.AsyncClient(timeout=5.0) as http:
        jwks_resp = await http.get(GOOGLE_JWKS_URI)
        jwks_resp.raise_for_status()
        jwks_data = jwks_resp.json()

    key_set = JsonWebKey.import_key_set(jwks_data)
    claims = authlib_jwt.decode(id_token, key_set)
    claims.validate()  # validates exp, iat, nbf

    if not claims.get("email_verified"):
        raise ValueError("Google email is not verified")

    return dict(claims)
