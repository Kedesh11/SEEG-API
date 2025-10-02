# Script de deploiement pour Azure avec optimisations et gestion d'erreurs
$ErrorActionPreference = "Stop"

Write-Host "Deploiement du backend FastAPI optimise sur Azure..." -ForegroundColor Cyan

# Variables de configuration
$RESOURCE_GROUP = "seeg-backend-rg"
$APP_SERVICE_NAME = "seeg-backend-api"
$LOCATION = "France Central"
$SKU = "B2"
$ACR_NAME = "seegbackend"
$IMAGE_NAME = "seeg-backend"
$DATABASE_PASSWORD = "Sevan%40Seeg"  # A externaliser dans un vault

# Verifier que l'utilisateur est connecte a Azure
Write-Host "Verification de la connexion Azure..." -ForegroundColor Yellow
try {
    az account show 2>&1 | Out-Null
    Write-Host "Connecte a Azure" -ForegroundColor Green
}
catch {
    Write-Host "Vous devez etre connecte a Azure CLI" -ForegroundColor Red
    Write-Host "Executez: az login" -ForegroundColor Yellow
    exit 1
}

# Creer le groupe de ressources
Write-Host "Creation du groupe de ressources..." -ForegroundColor Yellow
az group create --name $RESOURCE_GROUP --location $LOCATION --output table

# Creer l'Azure Container Registry
Write-Host "Creation du Container Registry..." -ForegroundColor Yellow
az acr create `
    --name $ACR_NAME `
    --resource-group $RESOURCE_GROUP `
    --location $LOCATION `
    --sku Basic `
    --admin-enabled true `
    --output table

# Obtenir les credentials du registry
Write-Host "Recuperation des credentials du registry..." -ForegroundColor Yellow
$ACR_LOGIN_SERVER = az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query loginServer --output tsv
$ACR_USERNAME = az acr credential show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query username --output tsv
$ACR_PASSWORD = az acr credential show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query passwords[0].value --output tsv

# Construire et pousser l'image Docker
Write-Host "Construction et push de l'image Docker..." -ForegroundColor Yellow
docker build -t "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest" .
docker login $ACR_LOGIN_SERVER -u $ACR_USERNAME -p $ACR_PASSWORD
docker push "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest"

# Creer l'App Service Plan
Write-Host "Creation du plan App Service..." -ForegroundColor Yellow
az appservice plan create `
    --name "${APP_SERVICE_NAME}-plan" `
    --resource-group $RESOURCE_GROUP `
    --location $LOCATION `
    --sku $SKU `
    --is-linux `
    --output table

# Creer l'App Service
Write-Host "Creation de l'App Service..." -ForegroundColor Yellow
az webapp create `
    --name $APP_SERVICE_NAME `
    --resource-group $RESOURCE_GROUP `
    --plan "${APP_SERVICE_NAME}-plan" `
    --runtime "PYTHON:3.11" `
    --output table

# Configurer l'App Service pour utiliser le container
Write-Host "Configuration du container..." -ForegroundColor Yellow
az webapp config container set `
    --name $APP_SERVICE_NAME `
    --resource-group $RESOURCE_GROUP `
    --docker-custom-image-name "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest" `
    --docker-registry-server-url "https://${ACR_LOGIN_SERVER}" `
    --docker-registry-server-user $ACR_USERNAME `
    --docker-registry-server-password $ACR_PASSWORD

# Recuperation de la connection string Application Insights
Write-Host "Recuperation de la connection string Application Insights..." -ForegroundColor Yellow
$APP_INSIGHTS_NAME = "seeg-api-insights"
$APP_INSIGHTS_CONNECTION_STRING = ""

# Essayer de recuperer la connection string existante
try {
    $result = az monitor app-insights component show --app $APP_INSIGHTS_NAME --resource-group $RESOURCE_GROUP 2>&1
    if ($LASTEXITCODE -eq 0) {
        $appInsights = $result | ConvertFrom-Json
        $APP_INSIGHTS_CONNECTION_STRING = $appInsights.connectionString
        Write-Host "Application Insights trouve et configure" -ForegroundColor Green
    }
}
catch {
    Write-Host "Application Insights non trouve, deploiement sans monitoring" -ForegroundColor Yellow
}

# Configurer les variables d'environnement (version securisee)
Write-Host "Configuration des variables d'environnement..." -ForegroundColor Yellow
$secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | ForEach-Object {[char]$_})

az webapp config appsettings set `
    --name $APP_SERVICE_NAME `
    --resource-group $RESOURCE_GROUP `
    --settings `
        DATABASE_URL="postgresql+asyncpg://Sevan:${DATABASE_PASSWORD}@seeg-postgres-server.postgres.database.azure.com:5432/postgres" `
        SECRET_KEY="$secretKey" `
        ALLOWED_ORIGINS="https://www.seeg-talentsource.com,https://seeg-talentsource.com,https://seeg-backend-api.azurewebsites.net" `
        ENVIRONMENT="production" `
        DEBUG="false" `
        LOG_LEVEL="INFO" `
        WORKERS="4" `
        MAX_REQUESTS="1000" `
        MAX_REQUESTS_JITTER="100" `
        TIMEOUT_KEEP_ALIVE="5" `
        TIMEOUT_GRACEFUL_SHUTDOWN="30" `
        WEBSITES_PORT="8000" `
        WEBSITES_ENABLE_APP_SERVICE_STORAGE="false" `
        APPLICATIONINSIGHTS_CONNECTION_STRING="$APP_INSIGHTS_CONNECTION_STRING"

# Configurer les logs
Write-Host "Configuration des logs..." -ForegroundColor Yellow
az webapp log config `
    --name $APP_SERVICE_NAME `
    --resource-group $RESOURCE_GROUP `
    --docker-container-logging filesystem `
    --level information

# Configurer le scaling automatique (optionnel - seulement si necessaire)
Write-Host "Configuration du scaling automatique..." -ForegroundColor Yellow
az monitor autoscale create `
    --resource-group $RESOURCE_GROUP `
    --resource "${APP_SERVICE_NAME}-plan" `
    --resource-type Microsoft.Web/serverfarms `
    --name "${APP_SERVICE_NAME}-autoscale" `
    --min-count 1 `
    --max-count 3 `
    --count 1

az monitor autoscale rule create `
    --resource-group $RESOURCE_GROUP `
    --autoscale-name "${APP_SERVICE_NAME}-autoscale" `
    --condition "CpuPercentage > 70 avg 5m" `
    --scale out 1

az monitor autoscale rule create `
    --resource-group $RESOURCE_GROUP `
    --autoscale-name "${APP_SERVICE_NAME}-autoscale" `
    --condition "CpuPercentage < 30 avg 5m" `
    --scale in 1

# Redemarrer l'App Service
Write-Host "Redemarrage de l'App Service..." -ForegroundColor Yellow
az webapp restart --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP

# Attendre que l'application soit disponible
Write-Host "Attente du demarrage de l'application..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

# Verifier le statut de deploiement
Write-Host "Verification du deploiement..." -ForegroundColor Yellow
$DEPLOYMENT_STATUS = az webapp show --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP --query state --output tsv

if ($DEPLOYMENT_STATUS -eq "Running") {
    Write-Host ""
    Write-Host "Deploiement termine avec succes !" -ForegroundColor Green
    Write-Host "URL de l'API: https://${APP_SERVICE_NAME}.azurewebsites.net" -ForegroundColor Cyan
    Write-Host "Documentation: https://${APP_SERVICE_NAME}.azurewebsites.net/docs" -ForegroundColor Cyan
    Write-Host "Health Check: https://${APP_SERVICE_NAME}.azurewebsites.net/health" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Commandes utiles:" -ForegroundColor Yellow
    Write-Host "   - Voir les logs: az webapp log tail --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP"
    Write-Host "   - Redemarrer: az webapp restart --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP"
    Write-Host "   - Mettre a jour: docker push ${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest && az webapp restart --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP"
}
else {
    Write-Host "Erreur lors du deploiement. Statut: $DEPLOYMENT_STATUS" -ForegroundColor Red
    Write-Host "Verifiez les logs: az webapp log tail --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP" -ForegroundColor Yellow
    exit 1
}

