FROM python:3.11-slim

# Install Poetry via pip (more stable)
RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false

# Create working user
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml poetry.lock* ./

# Install dependencies (production only)
RUN poetry install --only=main --no-interaction --no-ansi

# Copy application code
COPY . .

# Change file ownership
RUN chown -R app:app /app

# Switch to app user
USER app

# Default render port
EXPOSE 10000

# Production command
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"] 