FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY shared-py /shared-py
RUN pip install --no-cache-dir -e /shared-py
COPY backends/auth-py/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backends/auth-py/app ./app
COPY backends/auth-py/migrations ./migrations
COPY backends/auth-py/alembic.ini ./alembic.ini
EXPOSE 8005
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8005"]
