FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false

# Create working user
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml poetry.lock* ./

# Install dependencies (including dev dependencies for development)
RUN poetry install --no-interaction --no-ansi

# Copy application code
COPY . .

# Change file ownership
RUN chown -R app:app /app

# Switch to app user
USER app

EXPOSE 5000

# Keep container running for development
CMD ["sleep", "infinity"] 