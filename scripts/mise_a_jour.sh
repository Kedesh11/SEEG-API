#!/bin/bash

set -euo pipefail

# Couleurs
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Variables à adapter si besoin
RESOURCE_GROUP="seeg-backend-rg"
APP_SERVICE_NAME="seeg-backend-api"
CONTAINER_REGISTRY_NAME="seegbackend"
CONTAINER_REGISTRY="seegbackend.azurecr.io"
IMAGE_NAME="seeg-backend"
IMAGE_TAG="latest"

echo -e "${CYAN}"
echo "========================================"
echo "  MISE A JOUR CONTINUE - SEEG-API"
echo "========================================"
echo -e "${NC}"

# Demander si les migrations doivent être exécutées
echo -e "${YELLOW}Voulez-vous executer les migrations avant la mise a jour? (y/n)${NC}"
read -r RUN_MIGRATIONS

if [[ "$RUN_MIGRATIONS" =~ ^[Yy]$ ]]; then
    echo -e "\n${CYAN}Execution des migrations...${NC}"
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if bash "$SCRIPT_DIR/run-migrations.sh"; then
        echo -e "${GREEN}Migrations terminees avec succes${NC}\n"
    else
        echo -e "${YELLOW}Erreur lors des migrations. Voulez-vous continuer? (y/n)${NC}"
        read -r CONTINUE
        if [[ ! "$CONTINUE" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

echo "🔄 Construction de l'image Docker..."
docker build -t "${CONTAINER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}" .

echo "🔐 Connexion à Azure Container Registry..."
az acr login --name "${CONTAINER_REGISTRY_NAME}" --resource-group "${RESOURCE_GROUP}"

echo "⬆️  Push de l'image vers ACR..."
docker push "${CONTAINER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "🔄 Mise à jour de l'App Service avec la nouvelle image..."
az webapp config container set \
  --name "${APP_SERVICE_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --docker-custom-image-name "${CONTAINER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "📊 Vérification de la configuration Application Insights..."
APP_INSIGHTS_NAME="seeg-api-insights"

# Vérifier si Application Insights est configuré
CURRENT_APP_INSIGHTS=$(az webapp config appsettings list \
  --name "${APP_SERVICE_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[?name=='APPLICATIONINSIGHTS_CONNECTION_STRING'].value" -o tsv)

if [ -z "$CURRENT_APP_INSIGHTS" ]; then
  echo "⚠️  Application Insights non configuré, récupération de la connection string..."
  
  # Récupérer la connection string
  if az monitor app-insights component show --app "${APP_INSIGHTS_NAME}" --resource-group "seeg-rg" &> /dev/null; then
    APP_INSIGHTS_CONNECTION_STRING=$(az monitor app-insights component show \
      --app "${APP_INSIGHTS_NAME}" \
      --resource-group "seeg-rg" \
      --query connectionString -o tsv)
    
    echo "📊 Configuration d'Application Insights..."
    az webapp config appsettings set \
      --name "${APP_SERVICE_NAME}" \
      --resource-group "${RESOURCE_GROUP}" \
      --settings APPLICATIONINSIGHTS_CONNECTION_STRING="$APP_INSIGHTS_CONNECTION_STRING"
    
    echo "✅ Application Insights configuré"
  else
    echo "⚠️  Application Insights non trouvé dans Azure"
  fi
else
  echo "✅ Application Insights déjà configuré"
fi

echo "♻️  Redémarrage de l'App Service..."
az webapp restart --name "${APP_SERVICE_NAME}" --resource-group "${RESOURCE_GROUP}"

echo "✅ Mise à jour continue terminée !"