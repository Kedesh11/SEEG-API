# Script pour executer les migrations Alembic sur Azure
# A executer APRES le deploiement de l'image
$ErrorActionPreference = "Stop"

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "EXECUTION DES MIGRATIONS SUR AZURE" -ForegroundColor Yellow
Write-Host "=========================================`n" -ForegroundColor Cyan

$RESOURCE_GROUP = "seeg-backend-rg"
$APP_SERVICE_NAME = "seeg-backend-api"

Write-Host "Execution de la commande de migration via Azure CLI..." -ForegroundColor Yellow

# Executer alembic upgrade head via Azure CLI
az webapp ssh --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP --command "cd /app && alembic upgrade head"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Migrations appliquees avec succes !`n" -ForegroundColor Green
}
else {
    Write-Host "`n❌ Erreur lors de l'application des migrations`n" -ForegroundColor Red
    Write-Host "Verifiez les logs: az webapp log tail --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP" -ForegroundColor Yellow
    exit 1
}

