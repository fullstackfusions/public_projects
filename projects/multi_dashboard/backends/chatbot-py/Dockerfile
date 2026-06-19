FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY shared-py /shared-py
RUN pip install --no-cache-dir -e /shared-py
COPY backends/chatbot-py/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backends/chatbot-py/app ./app
EXPOSE 8003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
