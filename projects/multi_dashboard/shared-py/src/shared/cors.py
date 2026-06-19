"""CORS factory — forces explicit origins, never ``*`` in production."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def add_cors(
    app: FastAPI,
    origins: list[str],
    *,
    allow_credentials: bool = True,
    allow_methods: list[str] | None = None,
    allow_headers: list[str] | None = None,
) -> None:
    """Attach a CORS middleware. Pass an explicit origin list — no wildcards
    when credentials are allowed (CWE-942)."""
    if allow_credentials and "*" in origins:
        raise ValueError(
            "CORS allow_credentials=True is incompatible with origin '*'. "
            "Pass an explicit origin list."
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods or ["*"],
        allow_headers=allow_headers or ["*"],
    )


__all__ = ["add_cors"]
