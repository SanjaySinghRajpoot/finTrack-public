# Stage 1: Builder
FROM debian:bookworm-slim AS builder

# Install Python and build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3.11 python3-pip python3-venv \
        build-essential \
        libxml2-dev libxslt1-dev \
        libjpeg-dev zlib1g-dev libpng-dev \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv

# Create virtual environment
RUN python3.11 -m venv $VIRTUAL_ENV
# Activate virtual environment implicitly by setting PATH
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    rm -rf ~/.cache/pip

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_HOME=/app \
    VIRTUAL_ENV=/opt/venv
# Set PATH to include the virtual environment
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install only necessary runtime dependencies.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libxml2 \
        libxslt1.1 \
        libjpeg62-turbo \
        zlib1g \
        libpng16-16 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV

# Set work directory
WORKDIR $APP_HOME

# Copy only necessary application files
COPY app/ ./app/

# Create non-root user and set permissions
RUN groupadd -r appuser && useradd -r -g appuser appuser && \
    chown -R appuser:appuser $APP_HOME

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; try: urllib.request.urlopen('http://localhost:8000/api/', timeout=1); exit(0) except urllib.error.URLError as e: exit(1)"]

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]