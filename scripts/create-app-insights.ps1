# Script pour creer Application Insights et recuperer la connection string
$ErrorActionPreference = "Continue"

Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  Creation Application Insights pour SEEG-API" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

$RESOURCE_GROUP = "seeg-rg"
$LOCATION = "francecentral"
$APP_INSIGHTS_NAME = "seeg-api-insights"

# Verifier la connexion Azure
Write-Host "[1/4] Verification connexion Azure..." -ForegroundColor Yellow
$accountJson = az account show 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "      ERREUR: Non connecte a Azure" -ForegroundColor Red
    Write-Host "      Executez: az login" -ForegroundColor Yellow
    exit 1
}
$account = $accountJson | ConvertFrom-Json
Write-Host "      Connecte a: $($account.name)" -ForegroundColor Green
Write-Host ""

# Verifier si le resource group existe
Write-Host "[2/4] Verification du Resource Group..." -ForegroundColor Yellow
$rgExists = az group exists --name $RESOURCE_GROUP
if ($rgExists -eq "false") {
    Write-Host "      Resource Group '$RESOURCE_GROUP' introuvable" -ForegroundColor Red
    Write-Host "      Creation du Resource Group..." -ForegroundColor Yellow
    az group create --name $RESOURCE_GROUP --location $LOCATION | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      Resource Group cree!" -ForegroundColor Green
    } else {
        Write-Host "      ERREUR: Impossible de creer le Resource Group" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "      Resource Group existe" -ForegroundColor Green
}
Write-Host ""

# Creer Application Insights
Write-Host "[3/4] Creation Application Insights..." -ForegroundColor Yellow
Write-Host "      Ceci peut prendre 1-2 minutes..." -ForegroundColor Gray

$createResult = az monitor app-insights component create `
    --app $APP_INSIGHTS_NAME `
    --location $LOCATION `
    --resource-group $RESOURCE_GROUP `
    --application-type web `
    --kind web 2>&1

if ($LASTEXITCODE -ne 0) {
    # Peut-etre qu'il existe deja
    Write-Host "      Tentative de recuperation..." -ForegroundColor Yellow
    $showResult = az monitor app-insights component show `
        --app $APP_INSIGHTS_NAME `
        --resource-group $RESOURCE_GROUP 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "      Application Insights existe deja!" -ForegroundColor Green
        $appInsights = $showResult | ConvertFrom-Json
    } else {
        Write-Host "      ERREUR: $createResult" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "      Application Insights cree!" -ForegroundColor Green
    $appInsights = $createResult | ConvertFrom-Json
}
Write-Host ""

# Recuperer la connection string
Write-Host "[4/4] Recuperation Connection String..." -ForegroundColor Yellow
if (-not $appInsights) {
    $showResult = az monitor app-insights component show `
        --app $APP_INSIGHTS_NAME `
        --resource-group $RESOURCE_GROUP
    $appInsights = $showResult | ConvertFrom-Json
}

$CONNECTION_STRING = $appInsights.connectionString
$INSTRUMENTATION_KEY = $appInsights.instrumentationKey

if ([string]::IsNullOrEmpty($CONNECTION_STRING)) {
    Write-Host "      ERREUR: Connection string vide" -ForegroundColor Red
    exit 1
}

Write-Host "      Connection String recuperee!" -ForegroundColor Green
Write-Host ""

# Afficher les resultats
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  SUCCES!" -ForegroundColor Green
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Informations Application Insights:" -ForegroundColor White
Write-Host "  - Nom: $APP_INSIGHTS_NAME"
Write-Host "  - Resource Group: $RESOURCE_GROUP"
Write-Host "  - Location: $LOCATION"
Write-Host "  - Instrumentation Key: $INSTRUMENTATION_KEY"
Write-Host ""
Write-Host "Connection String:" -ForegroundColor Yellow
Write-Host "$CONNECTION_STRING" -ForegroundColor Green
Write-Host ""

# Sauvegarder dans .env.insights
$envContent = @"
# Azure Application Insights Configuration
# Genere le: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

APPLICATIONINSIGHTS_CONNECTION_STRING=$CONNECTION_STRING
"@

$envContent | Out-File -FilePath ".env.insights" -Encoding UTF8
Write-Host "Sauvegarde dans: .env.insights" -ForegroundColor Green
Write-Host ""

# Instructions
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  PROCHAINES ETAPES" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Ajoutez cette variable a votre fichier .env:" -ForegroundColor White
Write-Host ""
Write-Host "   APPLICATIONINSIGHTS_CONNECTION_STRING=`"$CONNECTION_STRING`"" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Redemarrez l'application:" -ForegroundColor White
Write-Host "   uvicorn app.main:app --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Verifiez l'activation:" -ForegroundColor White
Write-Host "   curl http://localhost:8000/info" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Consultez les donnees (apres 2-5 min):" -ForegroundColor White
Write-Host "   Portal Azure > Application Insights > $APP_INSIGHTS_NAME" -ForegroundColor Gray
Write-Host ""
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

