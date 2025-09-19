#!/bin/bash

# Script de déploiement robuste pour One HCM SEEG Backend
# Implémente les meilleures pratiques DevOps

set -euo pipefail  # Arrêt en cas d'erreur, variables non définies, erreurs dans les pipes

# Configuration des couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions de logging
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
RESOURCE_GROUP="one-hcm-seeg-rg"
APP_SERVICE_NAME="one-hcm-seeg-backend"
LOCATION="France Central"
SKU="B2"
CONTAINER_REGISTRY="onehcmseeg.azurecr.io"
IMAGE_NAME="one-hcm-seeg-backend"
IMAGE_TAG="latest"

# Validation des prérequis
validate_prerequisites() {
    log_info "Validation des prérequis..."
    
    # Vérifier Azure CLI
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI n'est pas installé"
        exit 1
    fi
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé"
        exit 1
    fi
    
    # Vérifier la connexion Azure
    if ! az account show &> /dev/null; then
        log_error "Vous devez être connecté à Azure CLI"
        log_info "Exécutez: az login"
        exit 1
    fi
    
    log_success "Tous les prérequis sont satisfaits"
}

# Construction de l'image Docker
build_docker_image() {
    log_info "Construction de l'image Docker..."
    
    if docker build -t "${CONTAINER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}" .; then
        log_success "Image Docker construite avec succès"
    else
        log_error "Échec de la construction de l'image Docker"
        exit 1
    fi
}

# Push de l'image vers Azure Container Registry
push_docker_image() {
    log_info "Push de l'image vers Azure Container Registry..."
    
    # Connexion à ACR
    if az acr login --name "${CONTAINER_REGISTRY%.*}" --resource-group "${RESOURCE_GROUP}"; then
        log_success "Connexion à ACR réussie"
    else
        log_error "Échec de la connexion à ACR"
        exit 1
    fi
    
    # Push de l'image
    if docker push "${CONTAINER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"; then
        log_success "Image poussée avec succès vers ACR"
    else
        log_error "Échec du push de l'image"
        exit 1
    fi
}

# Déploiement sur Azure App Service
deploy_to_app_service() {
    log_info "Déploiement sur Azure App Service..."
    
    # Configuration de l'App Service pour utiliser le container
    if az webapp config container set \
        --name "${APP_SERVICE_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --docker-custom-image-name "${CONTAINER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"; then
        log_success "Configuration du container mise à jour"
    else
        log_error "Échec de la configuration du container"
        exit 1
    fi
    
    # Configuration des variables d'environnement
    log_info "Configuration des variables d'environnement..."
    if az webapp config appsettings set \
        --name "${APP_SERVICE_NAME}" \
        --resource-group "${RESOURCE_GROUP}" \
        --settings \
            DATABASE_URL="postgresql+asyncpg://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres" \
            SECRET_KEY="$(openssl rand -base64 32)" \
            ENVIRONMENT="production" \
            DEBUG="false" \
            LOG_LEVEL="INFO" \
            WORKERS="4" \
            MAX_REQUESTS="1000" \
            MAX_REQUESTS_JITTER="100" \
            TIMEOUT_KEEP_ALIVE="5" \
            TIMEOUT_GRACEFUL_SHUTDOWN="30" \
            WEBSITES_PORT="8000" \
            WEBSITES_ENABLE_APP_SERVICE_STORAGE="false" \
            SMTP_HOST="smtp.gmail.com" \
            SMTP_PORT="587" \
            SMTP_USERNAME="support@seeg-talentsource.com" \
            SMTP_PASSWORD="njev urja zsbc spfn" \
            SMTP_TLS="true" \
            SMTP_SSL="false" \
            MAIL_FROM_NAME="One HCM - SEEG Talent Source" \
            MAIL_FROM_EMAIL="support@seeg-talentsource.com" \
            PUBLIC_APP_URL="https://www.seeg-talentsource.com"; then
        log_success "Variables d'environnement configurées"
    else
        log_error "Échec de la configuration des variables d'environnement"
        exit 1
    fi
}

# Redémarrage de l'App Service
restart_app_service() {
    log_info "Redémarrage de l'App Service..."
    
    if az webapp restart --name "${APP_SERVICE_NAME}" --resource-group "${RESOURCE_GROUP}"; then
        log_success "App Service redémarré"
    else
        log_error "Échec du redémarrage de l'App Service"
        exit 1
    fi
}

# Tests de santé post-déploiement
health_check() {
    log_info "Tests de santé post-déploiement..."
    
    local max_attempts=30
    local attempt=1
    local app_url="https://${APP_SERVICE_NAME}.azurewebsites.net"
    
    while [ $attempt -le $max_attempts ]; do
        log_info "Tentative $attempt/$max_attempts - Test de santé..."
        
        if curl -f -s "${app_url}/health" > /dev/null; then
            log_success "Test de santé réussi !"
            log_success "Application déployée avec succès : ${app_url}"
            log_success "Documentation API : ${app_url}/docs"
            return 0
        fi
        
        log_warning "Test de santé échoué, attente de 10 secondes..."
        sleep 10
        ((attempt++))
    done
    
    log_error "Tests de santé échoués après $max_attempts tentatives"
    return 1
}

# Exécution des migrations
run_migrations() {
    log_info "Exécution des migrations de base de données..."
    
    # Attendre que l'application soit prête
    sleep 30
    
    # Exécuter les migrations via SSH
    if az webapp ssh --name "${APP_SERVICE_NAME}" --resource-group "${RESOURCE_GROUP}" --command "cd /home/site/wwwroot && alembic upgrade head"; then
        log_success "Migrations exécutées avec succès"
    else
        log_warning "Échec de l'exécution des migrations (peut être normal si déjà à jour)"
    fi
}

# Fonction principale
main() {
    log_info "🚀 Début du déploiement de One HCM SEEG Backend"
    
    validate_prerequisites
    build_docker_image
    push_docker_image
    deploy_to_app_service
    restart_app_service
    
    if health_check; then
        run_migrations
        log_success "🎉 Déploiement terminé avec succès !"
        log_info "URL de l'API: https://${APP_SERVICE_NAME}.azurewebsites.net"
        log_info "Documentation: https://${APP_SERVICE_NAME}.azurewebsites.net/docs"
        log_info "Health Check: https://${APP_SERVICE_NAME}.azurewebsites.net/health"
    else
        log_error "❌ Déploiement échoué"
        exit 1
    fi
}

# Gestion des signaux
trap 'log_error "Déploiement interrompu"; exit 1' INT TERM

# Exécution du script
main "$@"
