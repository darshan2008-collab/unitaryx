FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies first for better build caching.
COPY requirements-docker.txt /tmp/requirements-docker.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements-docker.txt

# Copy application source.
COPY . /app

# Ensure writable app data directory exists for runtime artifacts.
RUN mkdir -p /app/data

EXPOSE 10184

CMD ["gunicorn", "app:app"]
