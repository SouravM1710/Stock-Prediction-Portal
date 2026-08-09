# Stock Prediction Portal - Backend (Django + TensorFlow)
# Hosts that run Docker containers (Railway, Render, Fly.io, Cloud Run, VPS).
# NOTE: Python 3.10 is required - TensorFlow 2.15 has no wheels for 3.12+.
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# TensorFlow's OpenMP runtime on slim images
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Apply migrations on boot, then serve via gunicorn.
# 1 worker keeps TensorFlow's memory footprint predictable.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn stock_prediction_main.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 4 --timeout 300"]
