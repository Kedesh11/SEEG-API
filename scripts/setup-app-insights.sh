#!/bin/bash
# Script pour créer et configurer Azure Application Insights

set -e

echo "🚀 Configuration d'Azure Application Insights pour SEEG-API"
echo "=========================================================="

# Variables de configuration
RESOURCE_GROUP="seeg-rg"
LOCATION="francecentral"
APP_INSIGHTS_NAME="seeg-api-insights"
LOG_WORKSPACE_NAME="seeg-logs-workspace"
APP_SERVICE_NAME="seeg-api-prod"

echo ""
echo "📋 Configuration:"
echo "  - Resource Group: $RESOURCE_GROUP"
echo "  - Location: $LOCATION"
echo "  - App Insights: $APP_INSIGHTS_NAME"
echo "  - Log Workspace: $LOG_WORKSPACE_NAME"
echo ""

# Vérifier la connexion Azure
echo "🔐 Vérification de la connexion Azure..."
if ! az account show &> /dev/null; then
    echo "❌ Non connecté à Azure. Exécutez: az login"
    exit 1
fi
echo "✅ Connecté à Azure"

# Afficher l'abonnement actuel
SUBSCRIPTION=$(az account show --query name -o tsv)
echo "📌 Abonnement actif: $SUBSCRIPTION"
echo ""

# Vérifier si le resource group existe
echo "🔍 Vérification du resource group..."
if az group show --name $RESOURCE_GROUP &> /dev/null; then
    echo "✅ Resource group '$RESOURCE_GROUP' existe"
else
    echo "❌ Resource group '$RESOURCE_GROUP' n'existe pas"
    read -p "Voulez-vous le créer ? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 Création du resource group..."
        az group create --name $RESOURCE_GROUP --location $LOCATION
        echo "✅ Resource group créé"
    else
        exit 1
    fi
fi
echo ""

# Vérifier/Créer le Log Analytics Workspace
echo "🔍 Vérification du Log Analytics Workspace..."
if az monitor log-analytics workspace show \
    --resource-group $RESOURCE_GROUP \
    --workspace-name $LOG_WORKSPACE_NAME &> /dev/null; then
    echo "✅ Workspace '$LOG_WORKSPACE_NAME' existe"
    WORKSPACE_ID=$(az monitor log-analytics workspace show \
        --resource-group $RESOURCE_GROUP \
        --workspace-name $LOG_WORKSPACE_NAME \
        --query id -o tsv)
else
    echo "📊 Création du Log Analytics Workspace..."
    WORKSPACE_ID=$(az monitor log-analytics workspace create \
        --resource-group $RESOURCE_GROUP \
        --workspace-name $LOG_WORKSPACE_NAME \
        --location $LOCATION \
        --query id -o tsv)
    echo "✅ Workspace créé: $WORKSPACE_ID"
fi
echo ""

# Créer Application Insights
echo "📈 Création d'Application Insights..."
if az monitor app-insights component show \
    --app $APP_INSIGHTS_NAME \
    --resource-group $RESOURCE_GROUP &> /dev/null; then
    echo "⚠️  Application Insights '$APP_INSIGHTS_NAME' existe déjà"
else
    az monitor app-insights component create \
        --app $APP_INSIGHTS_NAME \
        --location $LOCATION \
        --resource-group $RESOURCE_GROUP \
        --workspace $WORKSPACE_ID \
        --application-type web \
        --kind web
    echo "✅ Application Insights créé"
fi
echo ""

# Récupérer la connection string
echo "🔑 Récupération de la connection string..."
CONNECTION_STRING=$(az monitor app-insights component show \
    --app $APP_INSIGHTS_NAME \
    --resource-group $RESOURCE_GROUP \
    --query connectionString -o tsv)

if [ -z "$CONNECTION_STRING" ]; then
    echo "❌ Impossible de récupérer la connection string"
    exit 1
fi

echo "✅ Connection string récupérée"
echo ""

# Afficher la connection string
echo "=========================================================="
echo "🎉 Configuration réussie !"
echo "=========================================================="
echo ""
echo "📋 Informations Application Insights:"
echo ""
echo "Nom: $APP_INSIGHTS_NAME"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo ""
echo "🔑 Connection String:"
echo "$CONNECTION_STRING"
echo ""

# Sauvegarder dans un fichier .env.insights
echo "💾 Sauvegarde de la configuration..."
cat > .env.insights << EOF
# Azure Application Insights Configuration
# Généré le: $(date)

APPLICATIONINSIGHTS_CONNECTION_STRING=$CONNECTION_STRING
EOF
echo "✅ Configuration sauvegardée dans .env.insights"
echo ""

# Configurer l'App Service si elle existe
echo "🔧 Configuration de l'App Service..."
if az webapp show --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP &> /dev/null; then
    echo "📱 Configuration de '$APP_SERVICE_NAME'..."
    az webapp config appsettings set \
        --name $APP_SERVICE_NAME \
        --resource-group $RESOURCE_GROUP \
        --settings APPLICATIONINSIGHTS_CONNECTION_STRING="$CONNECTION_STRING"
    echo "✅ App Service configuré"
    echo ""
    echo "⚠️  N'oubliez pas de redémarrer l'App Service:"
    echo "   az webapp restart --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP"
else
    echo "⚠️  App Service '$APP_SERVICE_NAME' non trouvé"
    echo "   Vous devrez configurer manuellement la variable d'environnement"
fi
echo ""

# Instructions finales
echo "=========================================================="
echo "📝 Prochaines étapes:"
echo "=========================================================="
echo ""
echo "1. Pour le développement local:"
echo "   Ajoutez à votre fichier .env:"
echo "   APPLICATIONINSIGHTS_CONNECTION_STRING=\"$CONNECTION_STRING\""
echo ""
echo "2. Vérifiez la configuration:"
echo "   python -c \"from app.main import app; from app.core.monitoring import app_insights; print('App Insights:', app_insights.enabled)\""
echo ""
echo "3. Testez l'application:"
echo "   uvicorn app.main:app --reload"
echo "   curl http://localhost:8000/info | jq .monitoring"
echo ""
echo "4. Consultez les données (après 2-5 minutes):"
echo "   Portal Azure > Application Insights > $APP_INSIGHTS_NAME > Live Metrics"
echo ""
echo "5. URL du portail:"
echo "   https://portal.azure.com/#@/resource/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/microsoft.insights/components/$APP_INSIGHTS_NAME"
echo ""
echo "✅ Configuration terminée avec succès !"
echo ""

