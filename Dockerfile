FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml, README, and source code
COPY pyproject.toml README.md ./
COPY bitnet_runtime/ ./bitnet_runtime/
COPY verticals/ ./verticals/
COPY .env.example ./.env

# Install python package and llama-cpp-python pre-built CPU wheels
RUN pip install --no-cache-dir --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu "llama-cpp-python>=0.2.56" && \
    pip install --no-cache-dir -e .

# Create data and models directories
RUN mkdir -p /app/data /app/models /app/workspace

EXPOSE 8000

ENV HOST=0.0.0.0
ENV PORT=8000

CMD ["python", "-m", "bitnet_runtime.cli.main", "serve", "--host", "0.0.0.0", "--port", "8000"]
