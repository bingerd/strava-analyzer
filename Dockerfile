FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY strava_analyzer ./strava_analyzer

# Copy frontend files
COPY frontend ./frontend

# Cloud Run expects PORT env var
ENV PORT=8080

# Run with uvicorn
CMD ["uv", "run", "uvicorn", "strava_analyzer.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
