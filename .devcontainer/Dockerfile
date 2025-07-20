FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create working user
RUN useradd --create-home --shell /bin/bash app

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Change file ownership
RUN chown -R app:app /app

# Switch to app user
USER app

EXPOSE 5000

# Production command
CMD ["sleep", "infinity"] 