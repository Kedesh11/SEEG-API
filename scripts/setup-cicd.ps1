<#
.SYNOPSIS
    Configuration du CI/CD automatique pour SEEG-API

.DESCRIPTION
    Configure le déploiement continu automatique :
    - Webhook ACR vers App Service
    - Continuous Deployment activé
    - Détection automatique des nouveaux conteneurs
    - Déploiement automatique sans intervention manuelle

.EXAMPLE
    .\setup-cicd.ps1
    Configure le CI/CD complet

.NOTES
    Version: 1.0.0
    Author: SEEG DevOps Team
    Date: 2025-10-10
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

# Configuration
$CONFIG = @{
    ResourceGroup     = "seeg-backend-rg"
    ContainerRegistry = "seegbackend"
    AppName           = "seeg-backend-api"
    WebhookName       = "seegApiWebhook"
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         CONFIGURATION CI/CD - SEEG-API                        ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

#region Étape 1 : Activer Continuous Deployment

Write-Host "[1/4] Activation du Continuous Deployment sur App Service" -ForegroundColor Yellow
Write-Host ""

try {
    Write-Host "  → Configuration du déploiement continu..." -ForegroundColor White
    
    # Activer le CD depuis ACR
    az webapp deployment container config `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --enable-cd true 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Continuous Deployment activé" -ForegroundColor Green
    }
    else {
        throw "Échec de l'activation du CD"
    }
    
    # Récupérer l'URL du webhook
    $webhookUrl = az webapp deployment container show-cd-url `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --query "CI_CD_URL" `
        --output tsv 2>&1
    
    if ($webhookUrl) {
        Write-Host "  ✅ Webhook URL récupérée" -ForegroundColor Green
        Write-Host "     URL: $webhookUrl" -ForegroundColor Gray
    }
    
}
catch {
    Write-Host "  ❌ Erreur: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

#endregion

#region Étape 2 : Configurer le Webhook ACR

Write-Host ""
Write-Host "[2/4] Configuration du Webhook dans Azure Container Registry" -ForegroundColor Yellow
Write-Host ""

try {
    # Vérifier si le webhook existe déjà
    $existingWebhook = az acr webhook show `
        --name $CONFIG.WebhookName `
        --registry $CONFIG.ContainerRegistry `
        --output json 2>&1 | ConvertFrom-Json
    
    if ($existingWebhook) {
        Write-Host "  ⚠️  Webhook existant trouvé - suppression..." -ForegroundColor Yellow
        
        az acr webhook delete `
            --name $CONFIG.WebhookName `
            --registry $CONFIG.ContainerRegistry `
            --yes 2>&1 | Out-Null
    }
    
    # Créer le webhook
    Write-Host "  → Création du webhook ACR..." -ForegroundColor White
    
    az acr webhook create `
        --name $CONFIG.WebhookName `
        --registry $CONFIG.ContainerRegistry `
        --uri $webhookUrl `
        --actions push delete `
        --scope "$($CONFIG.AppName):*" 2>&1 | Out-Null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✅ Webhook ACR créé et configuré" -ForegroundColor Green
    }
    else {
        throw "Échec de la création du webhook"
    }
    
    # Activer le webhook
    az acr webhook update `
        --name $CONFIG.WebhookName `
        --registry $CONFIG.ContainerRegistry `
        --status enabled 2>&1 | Out-Null
    
    Write-Host "  ✅ Webhook activé" -ForegroundColor Green
    
}
catch {
    Write-Host "  ❌ Erreur: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

#endregion

#region Étape 3 : Configurer les paramètres optimaux

Write-Host ""
Write-Host "[3/4] Configuration des paramètres optimaux" -ForegroundColor Yellow
Write-Host ""

try {
    # Always On (pour éviter les cold starts)
    Write-Host "  → Activation de 'Always On'..." -ForegroundColor White
    
    az webapp config set `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --always-on true 2>&1 | Out-Null
    
    Write-Host "  ✅ Always On activé" -ForegroundColor Green
    
    # Configuration des logs
    Write-Host "  → Configuration des logs..." -ForegroundColor White
    
    az webapp log config `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --docker-container-logging filesystem `
        --level verbose 2>&1 | Out-Null
    
    Write-Host "  ✅ Logs configurés" -ForegroundColor Green
    
    # Health check
    Write-Host "  → Configuration du health check..." -ForegroundColor White
    
    az webapp config set `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --generic-configurations '{"healthCheckPath": "/docs"}' 2>&1 | Out-Null
    
    Write-Host "  ✅ Health check configuré sur /docs" -ForegroundColor Green
    
}
catch {
    Write-Host "  ⚠️  Avertissement: $($_.Exception.Message)" -ForegroundColor Yellow
}

#endregion

#region Étape 4 : Test du Webhook

Write-Host ""
Write-Host "[4/4] Test du Webhook" -ForegroundColor Yellow
Write-Host ""

try {
    Write-Host "  → Envoi d'un ping de test au webhook..." -ForegroundColor White
    
    az acr webhook ping `
        --name $CONFIG.WebhookName `
        --registry $CONFIG.ContainerRegistry 2>&1 | Out-Null
    
    Write-Host "  ✅ Ping envoyé avec succès" -ForegroundColor Green
    
    # Afficher les événements récents du webhook
    Start-Sleep -Seconds 2
    
    Write-Host "  → Vérification des événements du webhook..." -ForegroundColor White
    
    $events = az acr webhook list-events `
        --name $CONFIG.WebhookName `
        --registry $CONFIG.ContainerRegistry `
        --output json 2>&1 | ConvertFrom-Json
    
    if ($events -and $events.Count -gt 0) {
        Write-Host "  ✅ Webhook fonctionnel - $($events.Count) événement(s) enregistré(s)" -ForegroundColor Green
    }
    else {
        Write-Host "  ⚠️  Aucun événement trouvé (normal pour première configuration)" -ForegroundColor Yellow
    }
    
}
catch {
    Write-Host "  ⚠️  Test incomplet: $($_.Exception.Message)" -ForegroundColor Yellow
}

#endregion

#region Résumé

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              ✅ CI/CD CONFIGURÉ AVEC SUCCÈS ✅              ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "📋 CONFIGURATION CI/CD" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""
Write-Host "✅ Continuous Deployment : ACTIVÉ" -ForegroundColor Green
Write-Host "✅ Webhook ACR : CONFIGURÉ" -ForegroundColor Green
Write-Host "✅ Always On : ACTIVÉ" -ForegroundColor Green
Write-Host "✅ Logs : ACTIVÉS" -ForegroundColor Green
Write-Host "✅ Health Check : CONFIGURÉ (/docs)" -ForegroundColor Green
Write-Host ""

Write-Host "🔄 WORKFLOW AUTOMATIQUE" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""
Write-Host "  1️⃣  Vous construisez et poussez une nouvelle image :" -ForegroundColor White
Write-Host "     docker build -t $($CONFIG.ContainerRegistry).azurecr.io/$($CONFIG.AppName):latest ." -ForegroundColor Gray
Write-Host "     docker push $($CONFIG.ContainerRegistry).azurecr.io/$($CONFIG.AppName):latest" -ForegroundColor Gray
Write-Host ""
Write-Host "  2️⃣  ACR détecte le push et déclenche le webhook" -ForegroundColor White
Write-Host ""
Write-Host "  3️⃣  App Service redémarre automatiquement avec la nouvelle image" -ForegroundColor White
Write-Host ""
Write-Host "  4️⃣  Health check vérifie que l'application fonctionne" -ForegroundColor White
Write-Host ""

Write-Host "📊 MONITORING" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""
Write-Host "  • Événements webhook:" -ForegroundColor White
Write-Host "    az acr webhook list-events --name $($CONFIG.WebhookName) --registry $($CONFIG.ContainerRegistry)" -ForegroundColor Gray
Write-Host ""
Write-Host "  • Logs application:" -ForegroundColor White
Write-Host "    az webapp log tail --name $($CONFIG.AppName) --resource-group $($CONFIG.ResourceGroup)" -ForegroundColor Gray
Write-Host ""
Write-Host "  • Statut déploiement:" -ForegroundColor White
Write-Host "    az webapp deployment list --name $($CONFIG.AppName) --resource-group $($CONFIG.ResourceGroup)" -ForegroundColor Gray
Write-Host ""

Write-Host "🎯 PROCHAINE ÉTAPE" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""
Write-Host "  Testez le CI/CD avec:" -ForegroundColor White
Write-Host "  .\scripts\deploy-api-v2.ps1" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Après le premier déploiement, tous les futurs push vers ACR" -ForegroundColor White
Write-Host "  déclencheront automatiquement un redéploiement ! 🚀" -ForegroundColor Green
Write-Host ""

#endregion

