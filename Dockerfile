# Use Python 3.12 as the base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1

# Create working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# First copy just the pyproject.toml and uv.lock files to leverage Docker cache
COPY pyproject.toml uv.lock ./

# Copy the rest of the application code
COPY . .

# Install the package in development mode using pip directly (more reliable in Docker)
RUN pip install -e ".[redis]"

# Alternative: Use uv with system Python for installation
# RUN UV_SYSTEM_PYTHON=1 uv pip install --system -e ".[redis]"

# Create a data directory for file storage
RUN mkdir -p /app/search_results && chmod 777 /app/search_results

# Set entrypoint to the CLI tool
ENTRYPOINT ["tavily"]
# Default command to show help
CMD ["--help"]
