#!/bin/bash
set -e

echo "🚀 Démarrage de l'application One HCM SEEG Backend..."

# Attendre que la base de données soit disponible
echo "⏳ Attente de la base de données..."
sleep 10

# Exécuter les migrations Alembic depuis le bon répertoire
echo "📊 Exécution des migrations de base de données..."
cd /app
alembic upgrade head

# Démarrer l'application
echo "�� Démarrage du serveur FastAPI..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --access-log --log-level info
