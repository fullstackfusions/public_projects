FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY shared-py /shared-py
RUN pip install --no-cache-dir -e /shared-py
COPY backends/agentic-chat-py/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Install Node.js + Elastic MCP server so FlowIqAgent can spawn it as a
# stdio subprocess (the package does not support SSE/HTTP transport yet).
RUN apt-get update && apt-get install -y --no-install-recommends nodejs npm \
    && npm install -g @elastic/mcp-server-elasticsearch \
    && sed -i \
    -e "s|import '@elastic/opentelemetry-node';||g" \
    -e "s|import './telemetry.js';||g" \
    /usr/local/lib/node_modules/@elastic/mcp-server-elasticsearch/dist/index.js \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY backends/agentic-chat-py/app ./app
EXPOSE 8010
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
