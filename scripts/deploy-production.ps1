# Script de deploiement robuste pour One HCM SEEG Backend
# Implemente les meilleures pratiques DevOps

$ErrorActionPreference = "Stop"

# Configuration des couleurs pour les logs
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Configuration
$RESOURCE_GROUP = "one-hcm-seeg-rg"
$APP_SERVICE_NAME = "one-hcm-seeg-backend"
$LOCATION = "France Central"
$SKU = "B2"
$CONTAINER_REGISTRY = "onehcmseeg.azurecr.io"
$IMAGE_NAME = "one-hcm-seeg-backend"
$IMAGE_TAG = "latest"

# Validation des prerequis
function Test-Prerequisites {
    Write-Info "Validation des prerequis..."
    
    # Verifier Azure CLI
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        Write-Error-Custom "Azure CLI n'est pas installe"
        exit 1
    }
    
    # Verifier Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error-Custom "Docker n'est pas installe"
        exit 1
    }
    
    # Verifier la connexion Azure
    try {
        az account show 2>&1 | Out-Null
        Write-Success "Tous les prerequis sont satisfaits"
    }
    catch {
        Write-Error-Custom "Vous devez etre connecte a Azure CLI"
        Write-Info "Executez: az login"
        exit 1
    }
}

# Construction de l'image Docker
function Build-DockerImage {
    Write-Info "Construction de l'image Docker..."
    
    try {
        docker build -t "${CONTAINER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}" .
        Write-Success "Image Docker construite avec succes"
    }
    catch {
        Write-Error-Custom "Echec de la construction de l'image Docker"
        exit 1
    }
}

# Push de l'image vers Azure Container Registry
function Push-DockerImage {
    Write-Info "Push de l'image vers Azure Container Registry..."
    
    # Connexion a ACR
    try {
        $registryName = $CONTAINER_REGISTRY.Split('.')[0]
        az acr login --name $registryName --resource-group $RESOURCE_GROUP
        Write-Success "Connexion a ACR reussie"
    }
    catch {
        Write-Error-Custom "Echec de la connexion a ACR"
        exit 1
    }
    
    # Push de l'image
    try {
        docker push "${CONTAINER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
        Write-Success "Image poussee avec succes vers ACR"
    }
    catch {
        Write-Error-Custom "Echec du push de l'image"
        exit 1
    }
}

# Deploiement sur Azure App Service
function Deploy-ToAppService {
    Write-Info "Deploiement sur Azure App Service..."
    
    # Configuration de l'App Service pour utiliser le container
    try {
        az webapp config container set `
            --name $APP_SERVICE_NAME `
            --resource-group $RESOURCE_GROUP `
            --docker-custom-image-name "${CONTAINER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
        Write-Success "Configuration du container mise a jour"
    }
    catch {
        Write-Error-Custom "Echec de la configuration du container"
        exit 1
    }
    
    # Recuperation de la connection string Application Insights
    Write-Info "Recuperation de la connection string Application Insights..."
    $APP_INSIGHTS_NAME = "seeg-api-insights"
    $APP_INSIGHTS_CONNECTION_STRING = ""
    
    # Essayer de recuperer la connection string existante
    try {
        $result = az monitor app-insights component show --app $APP_INSIGHTS_NAME --resource-group $RESOURCE_GROUP 2>&1
        if ($LASTEXITCODE -eq 0) {
            $appInsights = $result | ConvertFrom-Json
            $APP_INSIGHTS_CONNECTION_STRING = $appInsights.connectionString
            Write-Success "Application Insights trouve et configure"
        }
    }
    catch {
        Write-Warning "Application Insights non trouve, deploiement sans monitoring"
    }
    
    # Configuration des variables d'environnement
    Write-Info "Configuration des variables d'environnement..."
    try {
        $secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
        
        az webapp config appsettings set `
            --name $APP_SERVICE_NAME `
            --resource-group $RESOURCE_GROUP `
            --settings `
                DATABASE_URL="postgresql+asyncpg://Sevan:Azure%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres" `
                SECRET_KEY="$secretKey" `
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
                SMTP_HOST="smtp.gmail.com" `
                SMTP_PORT="587" `
                SMTP_USERNAME="support@seeg-talentsource.com" `
                SMTP_PASSWORD="njev urja zsbc spfn" `
                SMTP_TLS="true" `
                SMTP_SSL="false" `
                MAIL_FROM_NAME="One HCM - SEEG Talent Source" `
                MAIL_FROM_EMAIL="support@seeg-talentsource.com" `
                PUBLIC_APP_URL="https://www.seeg-talentsource.com" `
                APPLICATIONINSIGHTS_CONNECTION_STRING="$APP_INSIGHTS_CONNECTION_STRING"
        
        Write-Success "Variables d'environnement configurees"
    }
    catch {
        Write-Error-Custom "Echec de la configuration des variables d'environnement"
        exit 1
    }
}

# Redemarrage de l'App Service
function Restart-AppService {
    Write-Info "Redemarrage de l'App Service..."
    
    try {
        az webapp restart --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP
        Write-Success "App Service redemarre"
    }
    catch {
        Write-Error-Custom "Echec du redemarrage de l'App Service"
        exit 1
    }
}

# Tests de sante post-deploiement
function Test-HealthCheck {
    Write-Info "Tests de sante post-deploiement..."
    
    $maxAttempts = 30
    $attempt = 1
    $appUrl = "https://${APP_SERVICE_NAME}.azurewebsites.net"
    
    while ($attempt -le $maxAttempts) {
        Write-Info "Tentative $attempt/$maxAttempts - Test de sante..."
        
        try {
            $response = Invoke-WebRequest -Uri "$appUrl/health" -UseBasicParsing -TimeoutSec 10
            if ($response.StatusCode -eq 200) {
                Write-Success "Test de sante reussi !"
                Write-Success "Application deployee avec succes : $appUrl"
                Write-Success "Documentation API : $appUrl/docs"
                return $true
            }
        }
        catch {
            Write-Warning "Test de sante echoue, attente de 10 secondes..."
            Start-Sleep -Seconds 10
            $attempt++
        }
    }
    
    Write-Error-Custom "Tests de sante echoues apres $maxAttempts tentatives"
    return $false
}

# Execution des migrations
function Invoke-Migrations {
    Write-Info "Execution des migrations de base de donnees..."
    
    # Attendre que l'application soit prete
    Start-Sleep -Seconds 30
    
    # Executer les migrations via SSH
    try {
        az webapp ssh --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP --command "cd /home/site/wwwroot && alembic upgrade head"
        Write-Success "Migrations executees avec succes"
    }
    catch {
        Write-Warning "Echec de l'execution des migrations (peut etre normal si deja a jour)"
    }
}

# Fonction principale
function Main {
    Write-Info "Debut du deploiement de One HCM SEEG Backend"
    
    Test-Prerequisites
    Build-DockerImage
    Push-DockerImage
    Deploy-ToAppService
    Restart-AppService
    
    if (Test-HealthCheck) {
        Invoke-Migrations
        Write-Success "Deploiement termine avec succes !"
        Write-Info "URL de l'API: https://${APP_SERVICE_NAME}.azurewebsites.net"
        Write-Info "Documentation: https://${APP_SERVICE_NAME}.azurewebsites.net/docs"
        Write-Info "Health Check: https://${APP_SERVICE_NAME}.azurewebsites.net/health"
    }
    else {
        Write-Error-Custom "Deploiement echoue"
        exit 1
    }
}

# Gestion des signaux
trap {
    Write-Error-Custom "Deploiement interrompu"
    exit 1
}

# Execution du script
Main

