FROM python:3.11-slim

WORKDIR /app

# Set pip configuration for better reliability
ENV PIP_DEFAULT_TIMEOUT=300 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# Use a reliable PyPI mirror
RUN echo "[global]\n\
index-url = https://pypi.org/simple\n\
trusted-host = pypi.org" > /etc/pip.conf

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies with retry
RUN pip install --upgrade pip && \
    pip install --default-timeout=300 \
    --retries 5 \
    --prefer-binary \
    --no-cache-dir \
    -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8004

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Start application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]