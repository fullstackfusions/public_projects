from __future__ import annotations

from functools import lru_cache

from pydantic import Field

class Settings():
    service_name: str = "agentic-chat-backend"

    openai_api_key: str = Field("")
    anthropic_api_key: str = Field("")

    default_llm_provider: str = Field("anthropic")
    default_model: str = Field("claude-sonnet-4-6")

    redis_url: str = Field("redis://localhost:6379")

    job_ttl_seconds: int = Field(3600)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


# Backwards-compat singleton used by existing modules (redis_store, agents)
settings = get_settings()
