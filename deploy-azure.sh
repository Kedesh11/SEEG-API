#!/bin/bash

# Script de déploiement pour Azure avec optimisations
echo "🚀 Déploiement du backend FastAPI optimisé sur Azure..."

# Variables de configuration
RESOURCE_GROUP="seeg-backend-rg"
APP_SERVICE_NAME="seeg-backend-api"
LOCATION="France Central"
SKU="B2"  # Augmenté pour les optimisations
CONTAINER_REGISTRY="seegbackend.azurecr.io"
IMAGE_NAME="seeg-backend"

# Vérifier que l'utilisateur est connecté à Azure
if ! az account show &> /dev/null; then
    echo "❌ Vous devez être connecté à Azure CLI"
    echo "Exécutez: az login"
    exit 1
fi

# Créer le groupe de ressources
echo "📦 Création du groupe de ressources..."
az group create --name $RESOURCE_GROUP --location "$LOCATION" --output table

# Créer l'Azure Container Registry
echo "🐳 Création du Container Registry..."
az acr create \
    --name seegbackend \
    --resource-group $RESOURCE_GROUP \
    --location "$LOCATION" \
    --sku Basic \
    --admin-enabled true \
    --output table

# Obtenir les credentials du registry
echo "🔑 Récupération des credentials du registry..."
ACR_LOGIN_SERVER=$(az acr show --name seegbackend --resource-group $RESOURCE_GROUP --query loginServer --output tsv)
ACR_USERNAME=$(az acr credential show --name seegbackend --resource-group $RESOURCE_GROUP --query username --output tsv)
ACR_PASSWORD=$(az acr credential show --name seegbackend --resource-group $RESOURCE_GROUP --query passwords[0].value --output tsv)

# Construire et pousser l'image Docker
echo "🔨 Construction et push de l'image Docker..."
docker build -t $ACR_LOGIN_SERVER/$IMAGE_NAME:latest .
docker login $ACR_LOGIN_SERVER -u $ACR_USERNAME -p $ACR_PASSWORD
docker push $ACR_LOGIN_SERVER/$IMAGE_NAME:latest

# Créer l'App Service Plan
echo "🏗️ Création du plan App Service..."
az appservice plan create \
    --name "${APP_SERVICE_NAME}-plan" \
    --resource-group $RESOURCE_GROUP \
    --location "$LOCATION" \
    --sku $SKU \
    --is-linux \
    --output table

# Créer l'App Service
echo "🌐 Création de l'App Service..."
az webapp create \
    --name $APP_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --plan "${APP_SERVICE_NAME}-plan" \
    --deployment-local-git \
    --output table

# Configurer l'App Service pour utiliser le container
echo "🐳 Configuration du container..."
az webapp config container set \
    --name $APP_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --docker-custom-image-name $ACR_LOGIN_SERVER/$IMAGE_NAME:latest \
    --docker-registry-server-url https://$ACR_LOGIN_SERVER \
    --docker-registry-server-user $ACR_USERNAME \
    --docker-registry-server-password $ACR_PASSWORD

# Configurer les variables d'environnement
echo "⚙️ Configuration des variables d'environnement..."
az webapp config appsettings set \
    --name $APP_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        DATABASE_URL="postgresql+asyncpg://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres" \
        SECRET_KEY="CHANGE-THIS-SECRET-KEY-IN-PRODUCTION-$(date +%s)" \
        ALLOWED_ORIGINS="https://www.seeg-talentsource.com,https://seeg-talentsource.com,https://seeg-backend-api.azurewebsites.net" \
        ENVIRONMENT="production" \
        DEBUG="false" \
        LOG_LEVEL="INFO" \
        WORKERS="4" \
        MAX_REQUESTS="1000" \
        MAX_REQUESTS_JITTER="100" \
        TIMEOUT_KEEP_ALIVE="5" \
        TIMEOUT_GRACEFUL_SHUTDOWN="30" \
        WEBSITES_PORT="8000" \
        WEBSITES_ENABLE_APP_SERVICE_STORAGE="false"

# Configurer les logs
echo "📝 Configuration des logs..."
az webapp log config \
    --name $APP_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --application-logging filesystem \
    --level information \
    --web-server-logging filesystem

# Configurer le scaling automatique
echo "📈 Configuration du scaling automatique..."
az monitor autoscale create \
    --resource-group $RESOURCE_GROUP \
    --resource $APP_SERVICE_NAME \
    --resource-type Microsoft.Web/sites \
    --name "${APP_SERVICE_NAME}-autoscale" \
    --min-count 1 \
    --max-count 10 \
    --count 2

# Configurer les règles d'autoscaling
az monitor autoscale rule create \
    --resource-group $RESOURCE_GROUP \
    --autoscale-name "${APP_SERVICE_NAME}-autoscale" \
    --condition "CpuPercentage > 70 avg 5m" \
    --scale out 1

az monitor autoscale rule create \
    --resource-group $RESOURCE_GROUP \
    --autoscale-name "${APP_SERVICE_NAME}-autoscale" \
    --condition "CpuPercentage < 30 avg 5m" \
    --scale in 1

# Configurer le déploiement depuis GitHub
echo "🔗 Configuration du déploiement GitHub..."
az webapp deployment source config \
    --name $APP_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --repo-url "https://github.com/Kedesh11/SEEG-API" \
    --branch main \
    --manual-integration

# Redémarrer l'App Service
echo "🔄 Redémarrage de l'App Service..."
az webapp restart --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP

# Afficher les informations de déploiement
echo ""
echo "✅ Déploiement terminé avec succès !"
echo "🌐 URL de l'API: https://${APP_SERVICE_NAME}.azurewebsites.net"
echo "📚 Documentation: https://${APP_SERVICE_NAME}.azurewebsites.net/docs"
echo "🔍 Health Check: https://${APP_SERVICE_NAME}.azurewebsites.net/health"
echo "📊 Endpoints optimisés:"
echo "   - https://${APP_SERVICE_NAME}.azurewebsites.net/api/v1/optimized/applications/optimized"
echo "   - https://${APP_SERVICE_NAME}.azurewebsites.net/api/v1/optimized/dashboard/stats/optimized"
echo ""
echo "🔧 Commandes utiles:"
echo "   - Voir les logs: az webapp log tail --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP"
echo "   - Redémarrer: az webapp restart --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP"
echo "   - Mettre à jour l'image: docker push $ACR_LOGIN_SERVER/$IMAGE_NAME:latest && az webapp restart --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP"
