FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY shared-py /shared-py
RUN pip install --no-cache-dir -e /shared-py[sql]

COPY backends/scheduler-py/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backends/scheduler-py/app ./app
COPY backends/scheduler-py/migrations ./migrations
COPY backends/scheduler-py/alembic.ini ./alembic.ini

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
