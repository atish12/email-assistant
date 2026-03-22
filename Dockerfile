# =============================================================================
# Stage 1 — Test
# Install all deps (including pytest), run tests.
# Build fails here if any test fails.
# =============================================================================
FROM python:3.11-slim AS tester

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

COPY pyproject.toml poetry.lock* ./

# Install ALL deps including pytest
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi

COPY . .

# Run tests — build stops here if any test fails
RUN python -m pytest tests/ -v


# =============================================================================
# Stage 2 — Runtime
# Fresh image, runtime deps only, no test files, no .pyc files.
# =============================================================================
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry

COPY pyproject.toml poetry.lock* ./

# Install runtime deps only — no pytest
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction --no-ansi

# Copy only what the app needs — tests/ intentionally excluded
COPY src/       ./src/
COPY config/    ./config/
COPY data/      ./data/

# Clean any .pyc files that snuck in
RUN find . -name "*.pyc" -delete && \
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

ENV PYTHONPATH=/app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "src/ui/streamlit_app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
