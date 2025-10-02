# Script pour executer les migrations Alembic avant deploiement
$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  EXECUTION DES MIGRATIONS ALEMBIC" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

# Configuration
$RESOURCE_GROUP = "seeg-backend-rg"
$APP_SERVICE_NAME = "seeg-backend-api"

# Verifier la connexion Azure
Write-Host "[1/4] Verification de la connexion Azure..." -ForegroundColor Yellow
try {
    az account show 2>&1 | Out-Null
    $account = az account show | ConvertFrom-Json
    Write-Host "      Connecte a: $($account.name)" -ForegroundColor Green
}
catch {
    Write-Host "      ERREUR: Non connecte a Azure" -ForegroundColor Red
    Write-Host "      Executez: az login" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Verifier que l'App Service existe
Write-Host "[2/4] Verification de l'App Service..." -ForegroundColor Yellow
try {
    $webapp = az webapp show --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP 2>&1 | ConvertFrom-Json
    Write-Host "      App Service: $APP_SERVICE_NAME" -ForegroundColor Green
    Write-Host "      Status: $($webapp.state)" -ForegroundColor Green
}
catch {
    Write-Host "      ERREUR: App Service '$APP_SERVICE_NAME' introuvable" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Verifier l'etat actuel des migrations
Write-Host "[3/4] Verification de l'etat actuel des migrations..." -ForegroundColor Yellow
Write-Host "      Connexion SSH a l'App Service..." -ForegroundColor Gray

try {
    # Executer alembic current pour voir l'etat actuel via API Kudu
    Write-Host "      Tentative de recuperation de l'etat via API Kudu..." -ForegroundColor Gray
    $creds = az webapp deployment list-publishing-credentials --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP | ConvertFrom-Json
    $base64AuthInfo = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("$($creds.publishingUserName):$($creds.publishingPassword)"))
    
    $body = @{
        command = "cd /home/site/wwwroot && alembic current"
        dir = "site\wwwroot"
    } | ConvertTo-Json
    
    $result = Invoke-RestMethod -Uri "https://$APP_SERVICE_NAME.scm.azurewebsites.net/api/command" `
        -Method Post `
        -Headers @{Authorization=("Basic {0}" -f $base64AuthInfo)} `
        -Body $body `
        -ContentType "application/json" `
        -ErrorAction SilentlyContinue
    
    if ($result.Output) {
        Write-Host "      Etat actuel des migrations:" -ForegroundColor Green
        Write-Host "      $($result.Output)" -ForegroundColor White
    }
    else {
        Write-Host "      Impossible de recuperer l'etat (normal si premiere migration)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "      Avertissement: Impossible de verifier l'etat actuel" -ForegroundColor Yellow
}
Write-Host ""

# Executer les migrations
Write-Host "[4/4] Execution des migrations..." -ForegroundColor Yellow
Write-Host "      Commande: alembic upgrade head" -ForegroundColor Gray
Write-Host ""

try {
    # Executer les migrations via API Kudu
    $creds = az webapp deployment list-publishing-credentials --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP | ConvertFrom-Json
    $base64AuthInfo = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("$($creds.publishingUserName):$($creds.publishingPassword)"))
    
    $body = @{
        command = "cd /home/site/wwwroot && alembic upgrade head"
        dir = "site\wwwroot"
    } | ConvertTo-Json
    
    $migrationResult = Invoke-RestMethod -Uri "https://$APP_SERVICE_NAME.scm.azurewebsites.net/api/command" `
        -Method Post `
        -Headers @{Authorization=("Basic {0}" -f $base64AuthInfo)} `
        -Body $body `
        -ContentType "application/json"
    
    $migrationOutput = $migrationResult.Output + $migrationResult.Error
    
    if ($migrationResult.ExitCode -eq 0) {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "  MIGRATIONS EXECUTEES AVEC SUCCES" -ForegroundColor Green
        Write-Host "========================================`n" -ForegroundColor Cyan
        
        Write-Host "Sortie des migrations:" -ForegroundColor Yellow
        Write-Host "$migrationOutput" -ForegroundColor White
        Write-Host ""
        
        # Verifier l'etat final
        Write-Host "Verification de l'etat final..." -ForegroundColor Yellow
        $finalBody = @{
            command = "cd /home/site/wwwroot && alembic current"
            dir = "site\wwwroot"
        } | ConvertTo-Json
        
        $finalResult = Invoke-RestMethod -Uri "https://$APP_SERVICE_NAME.scm.azurewebsites.net/api/command" `
            -Method Post `
            -Headers @{Authorization=("Basic {0}" -f $base64AuthInfo)} `
            -Body $finalBody `
            -ContentType "application/json" `
            -ErrorAction SilentlyContinue
        
        if ($finalResult.Output) {
            Write-Host "Etat final: $($finalResult.Output)" -ForegroundColor Green
        }
        Write-Host ""
        
        Write-Host "Prochaines etapes:" -ForegroundColor Cyan
        Write-Host "  1. Executer: .\scripts\mise_a_jour.ps1 (mise a jour application)" -ForegroundColor White
        Write-Host "  2. Ou executer: .\scripts\deploy-production.ps1 (deploiement complet)" -ForegroundColor White
        Write-Host ""
    }
    else {
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "  ERREUR LORS DES MIGRATIONS" -ForegroundColor Red
        Write-Host "========================================`n" -ForegroundColor Cyan
        
        Write-Host "Sortie d'erreur:" -ForegroundColor Red
        Write-Host "$migrationOutput" -ForegroundColor White
        Write-Host ""
        
        Write-Host "Suggestions:" -ForegroundColor Yellow
        Write-Host "  1. Verifiez la connexion a la base de donnees" -ForegroundColor White
        Write-Host "  2. Verifiez les fichiers de migration dans app/db/migrations/versions/" -ForegroundColor White
        Write-Host "  3. Consultez les logs: az webapp log tail --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP" -ForegroundColor White
        Write-Host ""
        
        exit 1
    }
}
catch {
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  ERREUR DE CONNEXION SSH" -ForegroundColor Red
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    Write-Host "Erreur: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Verifications:" -ForegroundColor Yellow
    Write-Host "  1. L'App Service est-il demarre?" -ForegroundColor White
    Write-Host "  2. SSH est-il active sur l'App Service?" -ForegroundColor White
    Write-Host "  3. Consultez le portail Azure pour plus de details" -ForegroundColor White
    Write-Host ""
    
    exit 1
}

Write-Host "========================================`n" -ForegroundColor Cyan

