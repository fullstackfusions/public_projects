# One image for api, worker, prodsim and bench; the compose `command` picks the role.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    TIKTOKEN_CACHE_DIR=/opt/tiktoken

COPY --from=ghcr.io/astral-sh/uv:0.9.8 /uv /usr/local/bin/uv
WORKDIR /app

# Dependency layer: only invalidated when pyproject.toml changes.
COPY pyproject.toml ./
RUN uv pip install --system -r pyproject.toml

COPY src ./src
RUN uv pip install --system --no-deps . \
 && python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')" \
 && useradd --create-home --uid 10001 app \
 && mkdir -p /app/results && chown app /app/results

USER app
