# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies if needed (e.g. for sqlite3)
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage cache
COPY apps/agent/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
# We copy the entire apps/agent directory to /app/apps/agent
# and other necessary files if they exist in root
COPY apps/agent ./apps/agent
COPY deploy_lookml.py .

# Copy .env example to avoid errors if .env is missing (actual env vars passed at runtime)
COPY apps/agent/.env.example ./apps/agent/.env

# Create empty __init__.py in apps if needed
RUN mkdir -p apps && touch apps/__init__.py

# Expose port
EXPOSE 8080

# Command to run the application
# We run from /app so python path works correctly
CMD ["uvicorn", "apps.agent.main:app", "--host", "0.0.0.0", "--port", "8080"]
