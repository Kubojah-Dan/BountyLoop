FROM python:3.12-slim

WORKDIR /app

# System dependencies (for psycopg binary, GeoAlchemy2, image libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (including dev dependencies for testing)
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e ".[dev]"

# Copy application source
COPY . .

# Create storage directory for uploaded photos
RUN mkdir -p /app/storage/photos

EXPOSE 8000

# Run with uvicorn; non-root user for security
RUN useradd -m -u 1001 appuser && chown -R appuser /app
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
