# Guía de Deploy y Rollback — Postor Cafe

## Deploy inicial

```bash
# 1. Clonar el repositorio
git clone <url-repo> postor-cafe
cd postor-cafe

# 2. Crear el archivo .env de producción con tus valores reales
cp .env.production.example .env.production
nano .env.production  # Editar valores reales

# 3. Construir y levantar (primera vez)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# 4. Crear las tablas de la base de datos
docker compose exec app python manage.py migrate

# 5. Recopilar archivos estáticos
docker compose exec app python manage.py collectstatic --noinput

# 6. Verificar que todo está saludable
docker ps
curl http://localhost/health/
```

---

## Actualizar la aplicación (sin downtime)

```bash
# 1. Obtener los últimos cambios del repositorio
git pull origin main

# 2. Reconstruir SOLO la app sin tocar los otros servicios
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --build app

# 3. Aplicar migraciones si las hay
docker compose exec app python manage.py migrate

# 4. Verificar estado post-deploy
docker ps
docker logs postor-app --tail 50
curl http://localhost/health/
```

---

## Rollback a versión anterior

### Opción A: Rollback rápido con tag de imagen anterior

```bash
# Ver imágenes disponibles con sus tags
docker images postor-cafe-app

# Levantar la versión anterior (reemplazar TAG con la versión deseada)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps \
  --build app  # O usar: image: postor-cafe-app:TAG

# Verificar
curl http://localhost/health/
```

### Opción B: Rollback con git

```bash
# Ver el historial de commits
git log --oneline -10

# Volver al commit estable previo (reemplazar COMMIT_HASH)
git checkout COMMIT_HASH

# Reconstruir y desplegar
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --build app

# Verificar
curl http://localhost/health/
docker logs postor-app --tail 50
```

---

## Comandos de mantenimiento útiles

```bash
# Ver logs de la app
docker logs postor-app --tail 100 -f

# Ver logs de Nginx
docker logs postor-nginx --tail 50

# Revisar estado de los servicios
docker ps
docker stats

# Acceder al shell de Django
docker compose exec app python manage.py shell

# Backup de la base de datos
docker compose exec db pg_dump -U $DB_USER $DB_NAME > backup_$(date +%Y%m%d_%H%M%S).sql

# Restaurar backup
docker compose exec -T db psql -U $DB_USER $DB_NAME < backup.sql
```
