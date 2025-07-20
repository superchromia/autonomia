FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry  && poetry config virtualenvs.create false

# Create working user
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy application code
COPY . .

# Install dependencies
RUN poetry install --only=main --no-interaction --no-ansi

# Change file ownership
RUN chown -R app:app /app

# Switch to app user
USER app

EXPOSE 5000

# Production command
CMD ["sleep", "infinity"] 