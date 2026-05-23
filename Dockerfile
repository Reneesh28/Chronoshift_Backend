FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PORT=8000

WORKDIR /app

# Install system dependencies (e.g. net-tools, curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    net-tools \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to optimize layer caching
COPY requirements.txt .

# Install dependencies (including supervisor)
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir supervisor

# Copy the entire backend project
COPY . .

# Expose port 8000 (Daphne ASGI Gateway)
EXPOSE 8000

# Start Supervisor to orchestrate Django, FastAPI, and Flask
CMD ["sh", "-c", "cd /app/django_core && python manage.py migrate && supervisord -c /app/supervisord.conf"]