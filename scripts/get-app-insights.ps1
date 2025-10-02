# Script pour recuperer la connection string Application Insights
$ErrorActionPreference = "Stop"

Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host "  Recuperation Connection String Application Insights" -ForegroundColor Cyan
Write-Host "===========================================================" -ForegroundColor Cyan
Write-Host ""

$RESOURCE_GROUP = "seeg-rg"
$APP_INSIGHTS_NAME = "seeg-api-insights"

# Verifier la connexion Azure
Write-Host "[1/3] Verification connexion Azure..." -ForegroundColor Yellow
try {
    $account = az account show 2>$null | ConvertFrom-Json
    Write-Host "      Connecte a: $($account.name)" -ForegroundColor Green
} catch {
    Write-Host "      ERREUR: Non connecte a Azure" -ForegroundColor Red
    Write-Host "      Executez: az login" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Recherche Application Insights
Write-Host "[2/3] Recherche Application Insights..." -ForegroundColor Yellow
try {
    $result = az monitor app-insights component show --app $APP_INSIGHTS_NAME --resource-group $RESOURCE_GROUP 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "      ERREUR: Application Insights '$APP_INSIGHTS_NAME' introuvable" -ForegroundColor Red
        Write-Host ""
        Write-Host "Pour le creer, executez:" -ForegroundColor Cyan
        Write-Host "az monitor app-insights component create --app $APP_INSIGHTS_NAME --location francecentral --resource-group $RESOURCE_GROUP --application-type web" -ForegroundColor Yellow
        Write-Host ""
        exit 1
    }
    
    $appInsights = $result | ConvertFrom-Json
    $CONNECTION_STRING = $appInsights.connectionString
    
    if ([string]::IsNullOrEmpty($CONNECTION_STRING)) {
        Write-Host "      ERREUR: Connection string vide" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "      Application Insights trouve!" -ForegroundColor Green
    Write-Host ""
    
    # Afficher les informations
    Write-Host "[3/3] Sauvegarde configuration..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "===========================================================" -ForegroundColor Cyan
    Write-Host "  CONNECTION STRING RECUPEREE AVEC SUCCES!" -ForegroundColor Green
    Write-Host "===========================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Informations:" -ForegroundColor White
    Write-Host "  - Nom: $APP_INSIGHTS_NAME"
    Write-Host "  - Resource Group: $RESOURCE_GROUP"
    Write-Host "  - Instrumentation Key: $($appInsights.instrumentationKey)"
    Write-Host ""
    Write-Host "Connection String:" -ForegroundColor Yellow
    Write-Host "$CONNECTION_STRING" -ForegroundColor Green
    Write-Host ""
    
    # Sauvegarder dans .env.insights
    $envContent = @"
# Azure Application Insights Configuration
# Genere le: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# Resource Group: $RESOURCE_GROUP
# App Insights: $APP_INSIGHTS_NAME

APPLICATIONINSIGHTS_CONNECTION_STRING=$CONNECTION_STRING
"@
    
    $envContent | Out-File -FilePath ".env.insights" -Encoding UTF8 -NoNewline
    Write-Host "Sauvegarde dans: .env.insights" -ForegroundColor Green
    Write-Host ""
    
    # Instructions
    Write-Host "===========================================================" -ForegroundColor Cyan
    Write-Host "  PROCHAINES ETAPES" -ForegroundColor Cyan
    Write-Host "===========================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Ajoutez cette ligne a votre fichier .env:" -ForegroundColor White
    Write-Host ""
    Write-Host "APPLICATIONINSIGHTS_CONNECTION_STRING=`"$CONNECTION_STRING`"" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "2. Ou copiez le fichier .env.insights cree" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Redemarrez votre application:" -ForegroundColor White
    Write-Host "   uvicorn app.main:app --reload" -ForegroundColor Gray
    Write-Host ""
    Write-Host "4. Verifiez que c'est active:" -ForegroundColor White
    Write-Host "   curl http://localhost:8000/info" -ForegroundColor Gray
    Write-Host ""
    Write-Host "===========================================================" -ForegroundColor Cyan
    Write-Host "  TERMINE!" -ForegroundColor Green
    Write-Host "===========================================================" -ForegroundColor Cyan
    Write-Host ""
    
} catch {
    Write-Host "ERREUR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
