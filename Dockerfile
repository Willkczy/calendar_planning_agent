# =============================================================================
# Calendar Planning Agent — Production Dockerfile
# =============================================================================
# Multi-stage build for a lean production image.
#
# HOW TO BUILD:
#   docker build -t calendar-agent .
#
# HOW TO RUN LOCALLY:
#   docker run --env-file .env -p 8501:8501 calendar-agent

FROM python:3.11-slim AS base

WORKDIR /app

# Install OS-level dependencies (none currently, placeholder)
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

# Streamlit requires these flags for containerised deployment
CMD ["streamlit", "run", "src/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
