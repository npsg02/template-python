FROM python:3.11-slim AS base

# Set Python environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Install basic dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip

FROM base AS builder

# Create and activate virtual environment
RUN python -m venv /.venv
ENV PATH="/.venv/bin:$PATH"

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

FROM base as runtime

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

# Copy application code
COPY . .

# Expose port (adjust if needed)
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]