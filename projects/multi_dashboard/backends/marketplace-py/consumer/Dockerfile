FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Use -u flag for unbuffered output (see logs immediately)
CMD ["python", "-u", "payment_consumer.py"]
