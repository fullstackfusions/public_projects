"""Runtime configuration, read once from the environment (docker compose sets it)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All knobs for api, worker, prodsim and bench. Defaults match docker-compose.yml."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Infra
    database_url: str = "postgresql://oncall:oncall@postgres:5432/oncall"
    redis_url: str = "redis://redis:6379/0"
    prodsim_url: str = "http://prodsim:8100"
    api_url: str = "http://api:8000"

    # Agent model (CPU-only Ollama in docker)
    ollama_base_url: str = "http://ollama:11434"
    agent_model: str = "qwen3:8b"
    agent_num_ctx: int = 32768
    agent_temperature: float = 0.0
    # Local judge for the circuit breaker's `local` detector.
    judge_model: str = "qwen3:1.7b"

    # ScaleDown
    scaledown_api_key: str | None = None
    scaledown_base_url: str | None = None

    # OpenAI: only for the frontier-vs-ScaleDown component bench, never the agent.
    openai_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("OPENAI_API_KEY", "OPEN_AI_API_KEY"))

    # Queue
    stream_key: str = "oncall:runs"
    consumer_group: str = "workers"
    # A pending run whose owner has not heartbeated for this long is reclaimed.
    reclaim_idle_ms: int = 90_000
    heartbeat_s: float = 15.0

    # Run budget (applies to every profile so baselines cannot run forever).
    max_model_calls: int = 40
    run_timeout_s: int = 3600

    # Summarization trigger, as a fraction of agent_num_ctx (explicit: ChatOllama has
    # no model profile, so Deep Agents would otherwise default to 170k tokens).
    summarize_at_fraction: float = 0.6
    summarize_keep_messages: int = 6

    worker_name: str = Field(default_factory=lambda: __import__("socket").gethostname())

    @property
    def scaledown_enabled(self) -> bool:
        return bool(self.scaledown_api_key)


@lru_cache
def settings() -> Settings:
    """Process-wide settings singleton."""
    return Settings()
