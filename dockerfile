FROM python:3.10-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .


# ==================================
# Worker image
# ==================================
FROM base AS worker

CMD ["celery", "-A", "ECHOME", "worker", "-l", "info"]


# ==================================
# Web image
# ==================================
FROM base AS web

# Collect static files for WhiteNoise
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "ECHOME.wsgi:application", "--bind", "0.0.0.0:8000"]