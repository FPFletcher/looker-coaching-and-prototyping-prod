FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if needed (e.g. for potential packages)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port 8080
EXPOSE 8080

# Run with uvicorn
CMD ["sh", "-c", "uvicorn apps.agent.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
