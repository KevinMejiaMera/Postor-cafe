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

# Directorio de trabajo
WORKDIR /app

# Instalar solo librerías de ejecución necesarias (libpq para Postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    postgresql-client \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && groupadd -r postor && useradd -r -g postor postor

# Copiar dependencias instaladas desde el builder
COPY --from=builder /install /usr/local

# Copiar el código del proyecto
COPY . /app/

# Permisos para el usuario no-root
RUN chown -R postor:postor /app

USER postor

EXPOSE 8000

CMD ["gunicorn", "restaurante.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
