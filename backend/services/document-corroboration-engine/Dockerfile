FROM python:3.11-slim

WORKDIR /app

# Set pip configuration for better reliability
ENV PIP_DEFAULT_TIMEOUT=300 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# Use a reliable PyPI mirror in China
RUN echo "[global]\n\
index-url = https://pypi.tuna.tsinghua.edu.cn/simple\n\
trusted-host = pypi.tuna.tsinghua.edu.cn" > /etc/pip.conf

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Function to install packages with retry
RUN echo '\
    retry_pip_install() {\
        for i in {1..3}; do\
            pip install --default-timeout=300 "$@" && break || {\
                echo "Attempt $i failed, retrying...";\
                sleep 5;\
                if [ $i -eq 3 ]; then\
                    echo "Failed to install after 3 attempts";\
                    exit 1;\
                fi;\
            };\
        done\
    }' >> ~/.bashrc

# Install Python dependencies with retry
RUN . ~/.bashrc && \
    pip install --upgrade pip && \
    # Install core dependencies first
    retry_pip_install -r requirements.txt

# Copy application code
COPY . .

# Install the package in development mode with retry
RUN . ~/.bashrc && retry_pip_install -e .

# Create necessary directories with proper permissions
RUN mkdir -p /app/data/uploads /app/data/processed && \
    chmod -R 777 /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]