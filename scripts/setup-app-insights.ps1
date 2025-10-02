# Script PowerShell pour créer et configurer Azure Application Insights
# Pour Windows

$ErrorActionPreference = "Stop"

Write-Host "🚀 Configuration d'Azure Application Insights pour SEEG-API" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Variables de configuration
$RESOURCE_GROUP = "seeg-rg"
$LOCATION = "francecentral"
$APP_INSIGHTS_NAME = "seeg-api-insights"
$LOG_WORKSPACE_NAME = "seeg-logs-workspace"
$APP_SERVICE_NAME = "seeg-api-prod"

Write-Host ""
Write-Host "📋 Configuration:"
Write-Host "  - Resource Group: $RESOURCE_GROUP"
Write-Host "  - Location: $LOCATION"
Write-Host "  - App Insights: $APP_INSIGHTS_NAME"
Write-Host "  - Log Workspace: $LOG_WORKSPACE_NAME"
Write-Host ""

# Vérifier la connexion Azure
Write-Host "🔐 Vérification de la connexion Azure..." -ForegroundColor Yellow
try {
    $account = az account show 2>$null | ConvertFrom-Json
    Write-Host "✅ Connecté à Azure" -ForegroundColor Green
    Write-Host "📌 Abonnement actif: $($account.name)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Non connecté à Azure. Exécutez: az login" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Vérifier si le resource group existe
Write-Host "🔍 Vérification du resource group..." -ForegroundColor Yellow
$rgExists = az group exists --name $RESOURCE_GROUP
if ($rgExists -eq "true") {
    Write-Host "✅ Resource group '$RESOURCE_GROUP' existe" -ForegroundColor Green
} else {
    Write-Host "❌ Resource group '$RESOURCE_GROUP' n'existe pas" -ForegroundColor Red
    $createRg = Read-Host "Voulez-vous le créer ? (y/n)"
    if ($createRg -eq "y") {
        Write-Host "📦 Création du resource group..." -ForegroundColor Yellow
        az group create --name $RESOURCE_GROUP --location $LOCATION
        Write-Host "✅ Resource group créé" -ForegroundColor Green
    } else {
        exit 1
    }
}
Write-Host ""

# Vérifier/Créer le Log Analytics Workspace
Write-Host "🔍 Vérification du Log Analytics Workspace..." -ForegroundColor Yellow
try {
    $workspace = az monitor log-analytics workspace show `
        --resource-group $RESOURCE_GROUP `
        --workspace-name $LOG_WORKSPACE_NAME 2>$null | ConvertFrom-Json
    Write-Host "✅ Workspace '$LOG_WORKSPACE_NAME' existe" -ForegroundColor Green
    $WORKSPACE_ID = $workspace.id
} catch {
    Write-Host "📊 Création du Log Analytics Workspace..." -ForegroundColor Yellow
    $workspace = az monitor log-analytics workspace create `
        --resource-group $RESOURCE_GROUP `
        --workspace-name $LOG_WORKSPACE_NAME `
        --location $LOCATION | ConvertFrom-Json
    $WORKSPACE_ID = $workspace.id
    Write-Host "✅ Workspace créé: $WORKSPACE_ID" -ForegroundColor Green
}
Write-Host ""

# Créer Application Insights
Write-Host "📈 Création d'Application Insights..." -ForegroundColor Yellow
try {
    $appInsights = az monitor app-insights component show `
        --app $APP_INSIGHTS_NAME `
        --resource-group $RESOURCE_GROUP 2>$null | ConvertFrom-Json
    Write-Host "⚠️  Application Insights '$APP_INSIGHTS_NAME' existe déjà" -ForegroundColor Yellow
} catch {
    az monitor app-insights component create `
        --app $APP_INSIGHTS_NAME `
        --location $LOCATION `
        --resource-group $RESOURCE_GROUP `
        --workspace $WORKSPACE_ID `
        --application-type web `
        --kind web
    Write-Host "✅ Application Insights créé" -ForegroundColor Green
}
Write-Host ""

# Récupérer la connection string
Write-Host "🔑 Récupération de la connection string..." -ForegroundColor Yellow
$appInsights = az monitor app-insights component show `
    --app $APP_INSIGHTS_NAME `
    --resource-group $RESOURCE_GROUP | ConvertFrom-Json
$CONNECTION_STRING = $appInsights.connectionString

if ([string]::IsNullOrEmpty($CONNECTION_STRING)) {
    Write-Host "❌ Impossible de récupérer la connection string" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Connection string récupérée" -ForegroundColor Green
Write-Host ""

# Afficher la connection string
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "🎉 Configuration réussie !" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📋 Informations Application Insights:"
Write-Host ""
Write-Host "Nom: $APP_INSIGHTS_NAME"
Write-Host "Resource Group: $RESOURCE_GROUP"
Write-Host "Location: $LOCATION"
Write-Host ""
Write-Host "🔑 Connection String:"
Write-Host $CONNECTION_STRING -ForegroundColor Yellow
Write-Host ""

# Sauvegarder dans un fichier .env.insights
Write-Host "💾 Sauvegarde de la configuration..." -ForegroundColor Yellow
@"
# Azure Application Insights Configuration
# Généré le: $(Get-Date)

APPLICATIONINSIGHTS_CONNECTION_STRING=$CONNECTION_STRING
"@ | Out-File -FilePath ".env.insights" -Encoding UTF8
Write-Host "✅ Configuration sauvegardée dans .env.insights" -ForegroundColor Green
Write-Host ""

# Configurer l'App Service si elle existe
Write-Host "🔧 Configuration de l'App Service..." -ForegroundColor Yellow
try {
    $webapp = az webapp show --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP 2>$null | ConvertFrom-Json
    Write-Host "📱 Configuration de '$APP_SERVICE_NAME'..." -ForegroundColor Yellow
    az webapp config appsettings set `
        --name $APP_SERVICE_NAME `
        --resource-group $RESOURCE_GROUP `
        --settings "APPLICATIONINSIGHTS_CONNECTION_STRING=$CONNECTION_STRING"
    Write-Host "✅ App Service configuré" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠️  N'oubliez pas de redémarrer l'App Service:" -ForegroundColor Yellow
    Write-Host "   az webapp restart --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP"
} catch {
    Write-Host "⚠️  App Service '$APP_SERVICE_NAME' non trouvé" -ForegroundColor Yellow
    Write-Host "   Vous devrez configurer manuellement la variable d'environnement"
}
Write-Host ""

# Instructions finales
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "📝 Prochaines étapes:" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Pour le développement local:"
Write-Host "   Ajoutez à votre fichier .env:"
Write-Host "   APPLICATIONINSIGHTS_CONNECTION_STRING=`"$CONNECTION_STRING`""
Write-Host ""
Write-Host "2. Vérifiez la configuration:"
Write-Host "   python -c `"from app.main import app; from app.core.monitoring import app_insights; print('App Insights:', app_insights.enabled)`""
Write-Host ""
Write-Host "3. Testez l'application:"
Write-Host "   uvicorn app.main:app --reload"
Write-Host "   curl http://localhost:8000/info | jq .monitoring"
Write-Host ""
Write-Host "4. Consultez les données (après 2-5 minutes):"
Write-Host "   Portal Azure > Application Insights > $APP_INSIGHTS_NAME > Live Metrics"
Write-Host ""
Write-Host "5. URL du portail:" -ForegroundColor Cyan
$subscriptionId = (az account show | ConvertFrom-Json).id
Write-Host "   https://portal.azure.com/#@/resource/subscriptions/$subscriptionId/resourceGroups/$RESOURCE_GROUP/providers/microsoft.insights/components/$APP_INSIGHTS_NAME" -ForegroundColor Blue
Write-Host ""
Write-Host "✅ Configuration terminée avec succès !" -ForegroundColor Green
Write-Host ""

