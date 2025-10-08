# Dockerfile multi-stage pour SEEG-API
# Build optimisé pour production avec sécurité renforcée

# Stage 1: Builder
FROM python:3.12-slim as builder

# Variables d'environnement pour Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Installer les dépendances système nécessaires pour la compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    libmagic1 \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --user --no-warn-script-location -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/appuser/.local/bin:$PATH \
    ENVIRONMENT=production

# Installer seulement les dépendances runtime nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libmagic1 \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copier les dépendances Python depuis le builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copier le code de l'application
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser alembic.ini ./

# Copier le script de démarrage
COPY --chown=appuser:appuser docker-entrypoint.sh ./

# Copier la configuration de logging
COPY --chown=appuser:appuser logging.yaml ./

# Passer à l'utilisateur non-root
USER appuser

# Rendre le script exécutable
RUN chmod +x docker-entrypoint.sh

# Exposer les ports
EXPOSE 8000 9090

# Variables d'environnement pour le monitoring
ENV LOG_LEVEL=INFO \
    ENABLE_TRACING=true \
    METRICS_ENABLED=true

# Health check amélioré
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/monitoring/health || exit 1

# Commande de démarrage
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--access-log", "--log-config", "logging.yaml"]
