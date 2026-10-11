# Football Analyzer — one-command container
# Build & run:  docker compose up   →  http://localhost:8000
FROM python:3.12-slim

# System libs matplotlib/scipy need at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code + committed data/models
COPY . .

# Train the xG model at build time if it isn't already committed
RUN python src/xg_model.py || true

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
