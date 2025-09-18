#!/bin/bash

# Script de déploiement pour Azure
echo "🚀 Déploiement du backend FastAPI sur Azure..."

# Variables de configuration
RESOURCE_GROUP="seeg-backend-rg"
APP_SERVICE_NAME="seeg-backend-api"
LOCATION="West Europe"
SKU="B1"

# Créer le groupe de ressources
echo "📦 Création du groupe de ressources..."
az group create --name $RESOURCE_GROUP --location "$LOCATION"

# Créer l'App Service Plan
echo "🏗️ Création du plan App Service..."
az appservice plan create \
    --name "${APP_SERVICE_NAME}-plan" \
    --resource-group $RESOURCE_GROUP \
    --location "$LOCATION" \
    --sku $SKU \
    --is-linux

# Créer l'App Service
echo "🌐 Création de l'App Service..."
az webapp create \
    --name $APP_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --plan "${APP_SERVICE_NAME}-plan" \
    --runtime "PYTHON|3.11"

# Configurer les variables d'environnement
echo "⚙️ Configuration des variables d'environnement..."
az webapp config appsettings set \
    --name $APP_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        DATABASE_URL="postgresql+asyncpg://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres" \
        SECRET_KEY="CHANGE-THIS-SECRET-KEY-IN-PRODUCTION" \
        ALLOWED_ORIGINS="https://www.seeg-talentsource.com,https://seeg-talentsource.com" \
        ENVIRONMENT="production" \
        DEBUG="false"

# Configurer le déploiement depuis GitHub
echo "🔗 Configuration du déploiement GitHub..."
az webapp deployment source config \
    --name $APP_SERVICE_NAME \
    --resource-group $RESOURCE_GROUP \
    --repo-url "https://github.com/your-username/one-hcm-seeg" \
    --branch main \
    --manual-integration

echo "✅ Déploiement configuré !"
echo "🌐 URL de l'API: https://${APP_SERVICE_NAME}.azurewebsites.net"
echo "📚 Documentation: https://${APP_SERVICE_NAME}.azurewebsites.net/docs"
