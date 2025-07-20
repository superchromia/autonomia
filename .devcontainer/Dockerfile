FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Create working user
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Change file ownership
RUN chown -R app:app /app

# Switch to app user
USER app

EXPOSE 5000

# Production command
CMD ["sleep", "infinity"] 