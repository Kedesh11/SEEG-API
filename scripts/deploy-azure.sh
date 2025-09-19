#!/bin/bash
# Script de déploiement Azure
# Respecte les meilleures pratiques de déploiement

set -e  # Arrêter en cas d'erreur

# Configuration
RESOURCE_GROUP="one-hcm-seeg-rg"
APP_NAME="sg-vision-pictures"
LOCATION="France Central"
SKU="B1"
PYTHON_VERSION="3.11"

# Configuration de la base de données PostgreSQL Azure
DB_SERVER="seegrecruiter"
DB_NAME="postgres"
DB_USER="Sevan"
DB_PASSWORD="Azure@Seeg"

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérification des prérequis
check_prerequisites() {
    log_info "Vérification des prérequis..."
    
    # Vérifier Azure CLI
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI n'est pas installé. Veuillez l'installer d'abord."
        exit 1
    fi
    
    # Vérifier la connexion Azure
    if ! az account show &> /dev/null; then
        log_error "Vous n'êtes pas connecté à Azure. Exécutez 'az login' d'abord."
        exit 1
    fi
    
    log_info "Prérequis vérifiés avec succès."
}

# Création du groupe de ressources
create_resource_group() {
    log_info "Création du groupe de ressources..."
    
    if az group show --name $RESOURCE_GROUP &> /dev/null; then
        log_warn "Le groupe de ressources $RESOURCE_GROUP existe déjà."
    else
        az group create \
            --name $RESOURCE_GROUP \
            --location "$LOCATION"
        log_info "Groupe de ressources créé avec succès."
    fi
}

# Création du plan App Service
create_app_service_plan() {
    log_info "Création du plan App Service..."
    
    if az appservice plan show --name "${APP_NAME}-plan" --resource-group $RESOURCE_GROUP &> /dev/null; then
        log_warn "Le plan App Service ${APP_NAME}-plan existe déjà."
    else
        az appservice plan create \
            --name "${APP_NAME}-plan" \
            --resource-group $RESOURCE_GROUP \
            --location "$LOCATION" \
            --sku $SKU \
            --is-linux
        log_info "Plan App Service créé avec succès."
    fi
}

# Création de l'application web
create_web_app() {
    log_info "Création de l'application web..."
    
    if az webapp show --name $APP_NAME --resource-group $RESOURCE_GROUP &> /dev/null; then
        log_warn "L'application web $APP_NAME existe déjà."
    else
        az webapp create \
            --name $APP_NAME \
            --resource-group $RESOURCE_GROUP \
            --plan "${APP_NAME}-plan" \
            --runtime "PYTHON|${PYTHON_VERSION}"
        log_info "Application web créée avec succès."
    fi
}

# Configuration de la base de données
configure_database() {
    log_info "Configuration de la base de données..."
    
    # Mettre à jour les variables d'environnement avec les informations de la DB
    DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_SERVER}.postgres.database.azure.com:5432/${DB_NAME}"
    DATABASE_URL_SYNC="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_SERVER}.postgres.database.azure.com:5432/${DB_NAME}"
    
    az webapp config appsettings set \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --settings \
            DATABASE_URL="$DATABASE_URL" \
            DATABASE_URL_SYNC="$DATABASE_URL_SYNC" \
            SECRET_KEY="your-super-secret-key-here-change-in-production-123456789" \
            ALGORITHM="HS256" \
            ACCESS_TOKEN_EXPIRE_MINUTES="30" \
            REFRESH_TOKEN_EXPIRE_DAYS="7" \
            ALLOWED_ORIGINS="https://www.seeg-talentsource.com,http://localhost:8000" \
            ALLOWED_CREDENTIALS="true" \
            DEBUG="false" \
            ENVIRONMENT="production" \
            APP_NAME="One HCM SEEG Backend" \
            APP_VERSION="1.0.0"
    
    log_info "Base de données configurée avec succès."
}

# Déploiement du code
deploy_code() {
    log_info "Déploiement du code..."
    
    # Créer un fichier de déploiement temporaire
    cat > .deployment << EOF_DEPLOYMENT
[config]
SCM_DO_BUILD_DURING_DEPLOYMENT=true
ENABLE_ORYX_BUILD=true
PYTHON_VERSION=${PYTHON_VERSION}
EOF_DEPLOYMENT

    # Déployer via Git
    az webapp deployment source config \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --repo-url "https://github.com/Kedesh11/SEEG-API.git" \
        --branch main \
        --manual-integration
    
    log_info "Code déployé avec succès."
}

# Configuration des logs
configure_logging() {
    log_info "Configuration des logs..."
    
    az webapp log config \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --application-logging filesystem \
        --level information \
        --web-server-logging filesystem
    
    log_info "Logs configurés avec succès."
}

# Configuration de la surveillance
configure_monitoring() {
    log_info "Configuration de la surveillance..."
    
    # Activer Application Insights si disponible
    if az extension show --name application-insights &> /dev/null; then
        az monitor app-insights component create \
            --app $APP_NAME \
            --location "$LOCATION" \
            --resource-group $RESOURCE_GROUP \
            --kind web
        
        INSTRUMENTATION_KEY=$(az monitor app-insights component show \
            --app $APP_NAME \
            --resource-group $RESOURCE_GROUP \
            --query instrumentationKey -o tsv)
        
        az webapp config appsettings set \
            --name $APP_NAME \
            --resource-group $RESOURCE_GROUP \
            --settings \
                APPINSIGHTS_INSTRUMENTATIONKEY="$INSTRUMENTATION_KEY"
        
        log_info "Application Insights configuré avec succès."
    else
        log_warn "Application Insights non disponible. Surveillance basique activée."
    fi
}

# Test de l'application
test_application() {
    log_info "Test de l'application..."
    
    # Attendre que l'application soit prête
    sleep 30
    
    # Tester l'endpoint de santé
    APP_URL="https://${APP_NAME}.azurewebsites.net"
    
    if curl -f "${APP_URL}/health" &> /dev/null; then
        log_info "Application testée avec succès. URL: $APP_URL"
    else
        log_warn "L'application pourrait ne pas être encore prête. Vérifiez les logs."
    fi
}

# Fonction principale
main() {
    log_info "Démarrage du déploiement Azure..."
    
    check_prerequisites
    create_resource_group
    create_app_service_plan
    create_web_app
    configure_database
    deploy_code
    configure_logging
    configure_monitoring
    test_application
    
    log_info "Déploiement terminé avec succès!"
    log_info "URL de l'application: https://${APP_NAME}.azurewebsites.net"
    log_info "URL de l'API: https://${APP_NAME}.azurewebsites.net/api/v1"
    log_info "Documentation API: https://${APP_NAME}.azurewebsites.net/docs"
}

# Exécution du script
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
