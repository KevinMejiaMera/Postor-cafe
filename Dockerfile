
# Usar una imagen base oficial de Python (ligera y segura)
FROM python:3.11-slim

# Evitar que Python escriba archivos .pyc y asegurar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Directorio de trabajo en el contenedor
WORKDIR /app

# Instalar dependencias del sistema y crear usuario no-root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r postor && useradd -r -g postor postor

# Copiar el archivo de requerimientos e instalar dependencias de Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del proyecto
COPY . /app/
RUN chown -R postor:postor /app

# Cambiar al usuario postor
USER postor

# Exponer el puerto donde correrá Gunicorn
EXPOSE 8000

# Comando por defecto para arrancar la aplicación (enfocado a Postor Cafe)
CMD ["gunicorn", "restaurante.wsgi:application", "--bind", "0.0.0.0:8000"]
