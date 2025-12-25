# Dockerfile for GPU-enabled Dubbing Pipeline
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    nodejs \
    npm \
    ffmpeg \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.10 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1

# Copy Python requirements
COPY python/requirements.txt /app/python/requirements.txt

# Install Python dependencies
RUN pip3 install --no-cache-dir -r /app/python/requirements.txt

# Copy Node.js files
COPY node/package.json /app/node/package.json
COPY node/src /app/node/src

# Install Node.js dependencies
WORKDIR /app/node
RUN npm install

# Copy Python application
WORKDIR /app
COPY python /app/python

# Create directories
RUN mkdir -p /app/data/input /app/data/output /app/data/temp /app/models

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MODEL_CACHE_DIR=/app/models
ENV INPUT_DIR=/app/data/input
ENV OUTPUT_DIR=/app/data/output
ENV TEMP_DIR=/app/data/temp
ENV API_PORT=8000

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start FastAPI server
CMD ["python3", "/app/python/app.py"]
