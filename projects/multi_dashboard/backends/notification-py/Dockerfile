FROM python:3.11-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY shared-py /shared-py
RUN pip install --no-cache-dir -e /shared-py[sql]

COPY backends/notification-py/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backends/notification-py/app ./app
COPY backends/notification-py/migrations ./migrations
COPY backends/notification-py/alembic.ini ./alembic.ini
COPY backends/notification-py/templates ./templates

EXPOSE 8008

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8008"]
