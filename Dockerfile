# ──────────────────────────────────────────────────────────
# STAGE 1: Builder
# ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
# ──────────────────────────────────────────────────────────
# STAGE 2: Production
# ──────────────────────────────────────────────────────────
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && groupadd -r postor && useradd -r -g postor postor
COPY --from=builder /install /usr/local
COPY . /app/
RUN mkdir -p /app/staticfiles /app/media \
    && chown -R postor:postor /app
USER postor
EXPOSE 8000
CMD ["gunicorn", "restaurante.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "--worker-tmp-dir", "/dev/shm"]
