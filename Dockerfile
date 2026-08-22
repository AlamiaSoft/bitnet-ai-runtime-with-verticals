FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and README.md
COPY pyproject.toml README.md ./

# Install python package dependencies
RUN pip install --no-cache-dir -e .

# Copy application source code
COPY bitnet_runtime/ ./bitnet_runtime/
COPY verticals/ ./verticals/
COPY .env.example ./.env

# Create data and models directories
RUN mkdir -p /app/data /app/models /app/workspace

EXPOSE 8000

ENV HOST=0.0.0.0
ENV PORT=8000

CMD ["python", "-m", "bitnet_runtime.cli.main", "serve", "--host", "0.0.0.0", "--port", "8000"]
