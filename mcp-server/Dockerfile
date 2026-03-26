FROM python:3.12-slim

WORKDIR /app

# Install package
COPY pyproject.toml README.md LICENSE ./
COPY src/ src/
RUN pip install --no-cache-dir .

# Default env
ENV AGENTICTRADE_BASE_URL=https://agentictrade.io

# MCP stdio transport
ENTRYPOINT ["agentictrade-mcp"]
