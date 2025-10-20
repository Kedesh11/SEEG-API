#!/bin/bash
# Script d'entrée pour SEEG-API avec monitoring

# Configurer les variables d'environnement par défaut
export PYTHONPATH=/app:$PYTHONPATH

# Attendre que PostgreSQL soit prêt
echo "Waiting for PostgreSQL..."
while ! nc -z ${DB_HOST:-localhost} ${DB_PORT:-5432}; do
  sleep 0.1
done
echo "PostgreSQL started"

# Attendre que Redis soit prêt (si configuré)
if [ ! -z "$REDIS_URL" ]; then
  echo "Waiting for Redis..."
  REDIS_HOST=$(echo $REDIS_URL | sed -e 's/redis:\/\///' -e 's/:.*$//')
  REDIS_PORT=$(echo $REDIS_URL | sed -e 's/.*://' -e 's/\/.*//')
  while ! nc -z ${REDIS_HOST:-localhost} ${REDIS_PORT:-6379}; do
    sleep 0.1
  done
  echo "Redis started"
fi

# Exécuter les migrations Alembic
echo "Running database migrations..."
alembic upgrade head

# Démarrer l'agent de collecte de métriques système en arrière-plan
if [ "$METRICS_ENABLED" = "true" ]; then
  echo "Starting metrics collector..."
  python -c "
import time
import psutil
from app.core.metrics import metrics_collector
while True:
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    metrics_collector.update_system_metrics(cpu, mem.used)
    time.sleep(30)
" &
fi

# Démarrer l'application
echo "Starting SEEG-API..."
exec "$@"
