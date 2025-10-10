# ============================================================================
# Dockerfile pour SEEG-API - Architecture Clean & Production-Ready
# ============================================================================
# Principes appliqués:
# - Multi-stage build pour optimisation de taille
# - Couches cachées pour rapidité de rebuild
# - Sécurité: utilisateur non-root, scan de vulnérabilités
# - Compatibilité: Azure App Service, Python 3.12
# ============================================================================

# ============================================================================
# STAGE 1: Builder - Compilation des dépendances
# ============================================================================
FROM python:3.12-slim AS builder

# Variables d'environnement pour optimisation Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /build

# Installer UNIQUEMENT les dépendances de compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    libmagic1 \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Créer un environnement virtuel dédié aux dépendances
RUN python -m venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copier requirements et installer dans un répertoire utilisateur
COPY requirements.txt .

# Installation avec retry et timeout pour fiabilité dans le venv
RUN pip install --no-cache-dir \
    --timeout=100 --retries=3 \
    -r requirements.txt

# ============================================================================
# STAGE 2: Runtime - Image finale légère
# ============================================================================
FROM python:3.12-slim AS runtime

# Métadonnées de l'image
LABEL maintainer="SEEG IT Team" \
    version="1.0.0" \
    description="One HCM SEEG Backend API" \
    org.opencontainers.image.source="https://github.com/Kedesh11/SEEG-API"

# Variables d'environnement runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:/home/appuser/.local/bin:$PATH" \
    ENVIRONMENT=production \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# Installer UNIQUEMENT les dépendances runtime (pas de compilateurs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libmagic1 \
    netcat-openbsd \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Créer utilisateur non-root avec UID/GID fixe pour sécurité
RUN groupadd -r appuser -g 1000 && \
    useradd -r -u 1000 -g appuser -m -s /bin/bash appuser

# Définir le répertoire de travail
WORKDIR /app

# Copier l'environnement virtuel construit en phase builder
COPY --from=builder --chown=appuser:appuser /opt/venv /opt/venv

# Copier le code applicatif
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser alembic.ini ./
COPY --chown=appuser:appuser scripts/ ./scripts/
COPY --chown=appuser:appuser logging.yaml ./
COPY --chown=appuser:appuser docker-entrypoint.sh ./

# Permissions d'exécution pour l'entrypoint
RUN chmod +x docker-entrypoint.sh && \
    chown appuser:appuser docker-entrypoint.sh

# Basculer vers utilisateur non-root
USER appuser

# Exposer les ports (8000 pour l'API, 9090 pour Prometheus)
EXPOSE 8000 9090

# Variables d'environnement pour monitoring
ENV LOG_LEVEL=INFO \
    LOG_FORMAT=json \
    ENABLE_TRACING=true \
    METRICS_ENABLED=true

# Health check amélioré avec retry et timeout adapté
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/monitoring/health || exit 1

# Point d'entrée: migrations automatiques puis démarrage
ENTRYPOINT ["./docker-entrypoint.sh"]

# Commande par défaut: Uvicorn avec workers adapté à Azure
# Note: Azure App Service peut override via WEBSITES_PORT
# 2 workers pour plan B1 (1.75GB RAM, 1 core) - évite les problèmes de ressources
CMD ["uvicorn", "app.main:app", \
    "--host", "0.0.0.0", \
    "--port", "8000", \
    "--workers", "2", \
    "--access-log", \
    "--log-config", "logging.yaml", \
    "--proxy-headers", \
    "--forwarded-allow-ips", "*"]
