FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install shared-py first (build context = repo root)
COPY shared-py /shared-py
RUN pip install --no-cache-dir -e /shared-py

COPY backends/tax-py/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backends/tax-py/app ./app

EXPOSE 8007

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007"]
