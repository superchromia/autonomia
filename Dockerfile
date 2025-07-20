FROM python:3.11-slim

# Install Poetry via pip (more stable)
RUN pip install poetry \
    && poetry config virtualenvs.create false

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

# Default render port
EXPOSE 10000

# Production command
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000"] 