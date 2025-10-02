# Script de mise a jour continue pour One HCM SEEG Backend
$ErrorActionPreference = "Stop"

# Variables a adapter si besoin
$RESOURCE_GROUP = "seeg-backend-rg"
$APP_SERVICE_NAME = "seeg-backend-api"
$CONTAINER_REGISTRY_NAME = "seegbackend"
$CONTAINER_REGISTRY = "seegbackend.azurecr.io"
$IMAGE_NAME = "seeg-backend"
$IMAGE_TAG = "latest"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  MISE A JOUR CONTINUE - SEEG-API" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

# Demander si les migrations doivent etre executees
Write-Host "Voulez-vous executer les migrations avant la mise a jour? (y/n)" -ForegroundColor Yellow
$runMigrations = Read-Host
if ($runMigrations -eq "y" -or $runMigrations -eq "Y") {
    Write-Host "`nExecution des migrations..." -ForegroundColor Cyan
    try {
        & "$PSScriptRoot\run-migrations.ps1"
        Write-Host "Migrations terminees avec succes`n" -ForegroundColor Green
    }
    catch {
        Write-Host "Erreur lors des migrations. Voulez-vous continuer? (y/n)" -ForegroundColor Yellow
        $continue = Read-Host
        if ($continue -ne "y" -and $continue -ne "Y") {
            exit 1
        }
    }
}

Write-Host "Construction de l'image Docker..." -ForegroundColor Cyan
docker build -t "${CONTAINER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}" .

Write-Host "Connexion a Azure Container Registry..." -ForegroundColor Yellow
az acr login --name $CONTAINER_REGISTRY_NAME --resource-group $RESOURCE_GROUP

Write-Host "Push de l'image vers ACR..." -ForegroundColor Yellow
docker push "${CONTAINER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

Write-Host "Mise a jour de l'App Service avec la nouvelle image..." -ForegroundColor Yellow
az webapp config container set `
  --name $APP_SERVICE_NAME `
  --resource-group $RESOURCE_GROUP `
  --docker-custom-image-name "${CONTAINER_REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"

Write-Host "Verification de la configuration Application Insights..." -ForegroundColor Yellow
$APP_INSIGHTS_NAME = "seeg-api-insights"

# Verifier si Application Insights est configure
$CURRENT_APP_INSIGHTS = az webapp config appsettings list `
  --name $APP_SERVICE_NAME `
  --resource-group $RESOURCE_GROUP `
  --query "[?name=='APPLICATIONINSIGHTS_CONNECTION_STRING'].value" -o tsv

if ([string]::IsNullOrEmpty($CURRENT_APP_INSIGHTS)) {
  Write-Host "Application Insights non configure, recuperation de la connection string..." -ForegroundColor Yellow
  
  # Recuperer la connection string
  try {
    $result = az monitor app-insights component show --app $APP_INSIGHTS_NAME --resource-group "seeg-rg" 2>&1
    if ($LASTEXITCODE -eq 0) {
      $appInsights = $result | ConvertFrom-Json
      $APP_INSIGHTS_CONNECTION_STRING = $appInsights.connectionString
      
      Write-Host "Configuration d'Application Insights..." -ForegroundColor Yellow
      az webapp config appsettings set `
        --name $APP_SERVICE_NAME `
        --resource-group $RESOURCE_GROUP `
        --settings APPLICATIONINSIGHTS_CONNECTION_STRING="$APP_INSIGHTS_CONNECTION_STRING"
      
      Write-Host "Application Insights configure" -ForegroundColor Green
    }
  }
  catch {
    Write-Host "Application Insights non trouve dans Azure" -ForegroundColor Yellow
  }
}
else {
  Write-Host "Application Insights deja configure" -ForegroundColor Green
}

Write-Host "Redemarrage de l'App Service..." -ForegroundColor Yellow
az webapp restart --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP

Write-Host "Mise a jour continue terminee !" -ForegroundColor Green

