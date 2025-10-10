<#
.SYNOPSIS
    Tests complets du déploiement SEEG-API

.DESCRIPTION
    Vérifie que tous les aspects du déploiement fonctionnent correctement :
    - API accessible
    - Endpoints fonctionnels
    - Monitoring actif
    - CI/CD configuré
    - Performance optimale

.EXAMPLE
    .\test-deployment.ps1
    Lance tous les tests

.NOTES
    Version: 1.0.0
    Author: SEEG DevOps Team
    Date: 2025-10-10
#>

[CmdletBinding()]
param()

$ErrorActionPreference = "Continue"

# Configuration
$CONFIG = @{
    ResourceGroup = "seeg-backend-rg"
    AppName       = "seeg-backend-api"
    BaseUrl       = "https://seeg-backend-api.azurewebsites.net"
}

$RESULTS = @{
    Passed   = 0
    Failed   = 0
    Warnings = 0
    Tests    = @()
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           TESTS DE DÉPLOIEMENT - SEEG-API                         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [int]$ExpectedStatus = 200,
        [int]$TimeoutSec = 15
    )
    
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec $TimeoutSec -UseBasicParsing -ErrorAction Stop
        
        if ($response.StatusCode -eq $ExpectedStatus) {
            Write-Host "  ✅ $Name" -ForegroundColor Green
            Write-Host "     Status: $($response.StatusCode) | Temps: $($response.Headers.'X-Response-Time')" -ForegroundColor Gray
            $RESULTS.Passed++
            $RESULTS.Tests += @{ Name = $Name; Status = "PASS"; Details = "Status $($response.StatusCode)" }
            return $true
        }
        else {
            Write-Host "  ❌ $Name" -ForegroundColor Red
            Write-Host "     Attendu: $ExpectedStatus | Reçu: $($response.StatusCode)" -ForegroundColor Yellow
            $RESULTS.Failed++
            $RESULTS.Tests += @{ Name = $Name; Status = "FAIL"; Details = "Wrong status code" }
            return $false
        }
    }
    catch {
        Write-Host "  ❌ $Name" -ForegroundColor Red
        Write-Host "     Erreur: $($_.Exception.Message)" -ForegroundColor Yellow
        $RESULTS.Failed++
        $RESULTS.Tests += @{ Name = $Name; Status = "FAIL"; Details = $_.Exception.Message }
        return $false
    }
}

#region Test 1 : Accessibilité de l'API

Write-Host "[1/7] 🌐 Tests d'accessibilité" -ForegroundColor Yellow
Write-Host ""

Test-Endpoint -Name "Endpoint racine (/)" -Url "$($CONFIG.BaseUrl)/"
Test-Endpoint -Name "Documentation Swagger (/docs)" -Url "$($CONFIG.BaseUrl)/docs"
Test-Endpoint -Name "API Schema (/openapi.json)" -Url "$($CONFIG.BaseUrl)/openapi.json"
Test-Endpoint -Name "Redoc (/redoc)" -Url "$($CONFIG.BaseUrl)/redoc"

#endregion

#region Test 2 : Endpoints API

Write-Host ""
Write-Host "[2/7] 🔌 Tests des endpoints API" -ForegroundColor Yellow
Write-Host ""

# Test endpoints publics (devrait retourner 405 ou 401 mais pas 404)
$authTest = Test-Endpoint -Name "Auth Login (POST)" -Url "$($CONFIG.BaseUrl)/api/v1/auth/login" -ExpectedStatus 405
if (-not $authTest) {
    # 401 est aussi acceptable pour un endpoint qui existe
    Write-Host "     (405 ou 401 sont acceptables)" -ForegroundColor Gray
}

#endregion

#region Test 3 : Performance

Write-Host ""
Write-Host "[3/7] ⚡ Tests de performance" -ForegroundColor Yellow
Write-Host ""

try {
    $iterations = 5
    $responseTimes = @()
    
    Write-Host "  → Exécution de $iterations requêtes..." -ForegroundColor White
    
    for ($i = 1; $i -le $iterations; $i++) {
        $start = Get-Date
        $response = Invoke-WebRequest -Uri "$($CONFIG.BaseUrl)/docs" -UseBasicParsing -ErrorAction Stop
        $end = Get-Date
        $duration = ($end - $start).TotalMilliseconds
        $responseTimes += $duration
        Write-Host "     Requête $i : ${duration}ms" -ForegroundColor Gray
    }
    
    $avgTime = ($responseTimes | Measure-Object -Average).Average
    $maxTime = ($responseTimes | Measure-Object -Maximum).Maximum
    $minTime = ($responseTimes | Measure-Object -Minimum).Minimum
    
    Write-Host ""
    Write-Host "  📊 Résultats:" -ForegroundColor Cyan
    Write-Host "     Temps moyen: ${avgTime}ms" -ForegroundColor White
    Write-Host "     Temps min: ${minTime}ms" -ForegroundColor White
    Write-Host "     Temps max: ${maxTime}ms" -ForegroundColor White
    
    if ($avgTime -lt 1000) {
        Write-Host "  ✅ Performance excellente (< 1s)" -ForegroundColor Green
        $RESULTS.Passed++
    }
    elseif ($avgTime -lt 3000) {
        Write-Host "  ⚠️  Performance acceptable (< 3s)" -ForegroundColor Yellow
        $RESULTS.Warnings++
    }
    else {
        Write-Host "  ❌ Performance insuffisante (> 3s)" -ForegroundColor Red
        $RESULTS.Failed++
    }
    
}
catch {
    Write-Host "  ❌ Test de performance échoué" -ForegroundColor Red
    $RESULTS.Failed++
}

#endregion

#region Test 4 : Configuration Azure

Write-Host ""
Write-Host "[4/7] ☁️  Tests de configuration Azure" -ForegroundColor Yellow
Write-Host ""

try {
    # Vérifier App Service
    Write-Host "  → Vérification App Service..." -ForegroundColor White
    $app = az webapp show --name $CONFIG.AppName --resource-group $CONFIG.ResourceGroup --output json 2>&1 | ConvertFrom-Json
    
    if ($app -and $app.state -eq "Running") {
        Write-Host "  ✅ App Service Running" -ForegroundColor Green
        $RESULTS.Passed++
    }
    else {
        Write-Host "  ❌ App Service non Running" -ForegroundColor Red
        $RESULTS.Failed++
    }
    
    # Vérifier Always On
    $config = az webapp config show --name $CONFIG.AppName --resource-group $CONFIG.ResourceGroup --output json 2>&1 | ConvertFrom-Json
    
    if ($config.alwaysOn) {
        Write-Host "  ✅ Always On activé" -ForegroundColor Green
        $RESULTS.Passed++
    }
    else {
        Write-Host "  ⚠️  Always On désactivé" -ForegroundColor Yellow
        $RESULTS.Warnings++
    }
    
    # Vérifier HTTP 2.0
    if ($config.http20Enabled) {
        Write-Host "  ✅ HTTP 2.0 activé" -ForegroundColor Green
        $RESULTS.Passed++
    }
    else {
        Write-Host "  ⚠️  HTTP 2.0 désactivé" -ForegroundColor Yellow
        $RESULTS.Warnings++
    }
    
}
catch {
    Write-Host "  ❌ Erreur vérification Azure: $($_.Exception.Message)" -ForegroundColor Red
    $RESULTS.Failed++
}

#endregion

#region Test 5 : Monitoring

Write-Host ""
Write-Host "[5/7] 📊 Tests du monitoring" -ForegroundColor Yellow
Write-Host ""

try {
    # Vérifier Application Insights
    Write-Host "  → Vérification Application Insights..." -ForegroundColor White
    $appSettings = az webapp config appsettings list --name $CONFIG.AppName --resource-group $CONFIG.ResourceGroup --output json 2>&1 | ConvertFrom-Json
    
    $hasAppInsights = $appSettings | Where-Object { $_.name -eq "APPINSIGHTS_INSTRUMENTATIONKEY" }
    
    if ($hasAppInsights) {
        Write-Host "  ✅ Application Insights configuré" -ForegroundColor Green
        $RESULTS.Passed++
    }
    else {
        Write-Host "  ❌ Application Insights non configuré" -ForegroundColor Red
        $RESULTS.Failed++
    }
    
    # Vérifier Log Analytics
    Write-Host "  → Vérification Log Analytics..." -ForegroundColor White
    $workspaces = az monitor log-analytics workspace list --resource-group $CONFIG.ResourceGroup --output json 2>&1 | ConvertFrom-Json
    
    if ($workspaces -and $workspaces.Count -gt 0) {
        Write-Host "  ✅ Log Analytics configuré" -ForegroundColor Green
        $RESULTS.Passed++
    }
    else {
        Write-Host "  ⚠️  Log Analytics non trouvé" -ForegroundColor Yellow
        $RESULTS.Warnings++
    }
    
    # Vérifier les alertes
    Write-Host "  → Vérification des alertes..." -ForegroundColor White
    $alerts = az monitor metrics alert list --resource-group $CONFIG.ResourceGroup --output json 2>&1 | ConvertFrom-Json
    
    $apiAlerts = $alerts | Where-Object { $_.name -like "seeg-api-*" }
    
    if ($apiAlerts -and $apiAlerts.Count -ge 3) {
        Write-Host "  ✅ Alertes configurées ($($apiAlerts.Count))" -ForegroundColor Green
        $RESULTS.Passed++
    }
    else {
        Write-Host "  ⚠️  Peu d'alertes configurées ($($apiAlerts.Count))" -ForegroundColor Yellow
        $RESULTS.Warnings++
    }
    
}
catch {
    Write-Host "  ⚠️  Erreur vérification monitoring: $($_.Exception.Message)" -ForegroundColor Yellow
    $RESULTS.Warnings++
}

#endregion

#region Test 6 : CI/CD

Write-Host ""
Write-Host "[6/7] 🔄 Tests du CI/CD" -ForegroundColor Yellow
Write-Host ""

try {
    # Vérifier Continuous Deployment
    Write-Host "  → Vérification Continuous Deployment..." -ForegroundColor White
    $cdUrl = az webapp deployment container show-cd-url --name $CONFIG.AppName --resource-group $CONFIG.ResourceGroup --query "CI_CD_URL" --output tsv 2>&1
    
    if ($cdUrl -and $cdUrl -ne "") {
        Write-Host "  ✅ Continuous Deployment activé" -ForegroundColor Green
        $RESULTS.Passed++
    }
    else {
        Write-Host "  ⚠️  Continuous Deployment non activé" -ForegroundColor Yellow
        $RESULTS.Warnings++
    }
    
    # Vérifier Webhook ACR
    Write-Host "  → Vérification Webhook ACR..." -ForegroundColor White
    $webhooks = az acr webhook list --registry seegbackend --output json 2>&1 | ConvertFrom-Json
    
    $apiWebhook = $webhooks | Where-Object { $_.name -like "*$($CONFIG.AppName)*" -or $_.name -like "*seeg-api*" }
    
    if ($apiWebhook) {
        Write-Host "  ✅ Webhook ACR configuré" -ForegroundColor Green
        $RESULTS.Passed++
    }
    else {
        Write-Host "  ⚠️  Webhook ACR non trouvé" -ForegroundColor Yellow
        $RESULTS.Warnings++
    }
    
}
catch {
    Write-Host "  ⚠️  Erreur vérification CI/CD: $($_.Exception.Message)" -ForegroundColor Yellow
    $RESULTS.Warnings++
}

#endregion

#region Test 7 : Sécurité

Write-Host ""
Write-Host "[7/7] 🔒 Tests de sécurité" -ForegroundColor Yellow
Write-Host ""

try {
    # Vérifier HTTPS
    Write-Host "  → Vérification HTTPS..." -ForegroundColor White
    $response = Invoke-WebRequest -Uri $CONFIG.BaseUrl -UseBasicParsing -ErrorAction Stop
    
    if ($CONFIG.BaseUrl.StartsWith("https://")) {
        Write-Host "  ✅ HTTPS activé" -ForegroundColor Green
        $RESULTS.Passed++
    }
    else {
        Write-Host "  ❌ HTTPS non activé" -ForegroundColor Red
        $RESULTS.Failed++
    }
    
    # Vérifier TLS
    Write-Host "  → Vérification TLS 1.2..." -ForegroundColor White
    $config = az webapp config show --name $CONFIG.AppName --resource-group $CONFIG.ResourceGroup --output json 2>&1 | ConvertFrom-Json
    
    if ($config.minTlsVersion -eq "1.2") {
        Write-Host "  ✅ TLS 1.2 minimum configuré" -ForegroundColor Green
        $RESULTS.Passed++
    }
    else {
        Write-Host "  ⚠️  TLS version: $($config.minTlsVersion)" -ForegroundColor Yellow
        $RESULTS.Warnings++
    }
    
    # Vérifier headers de sécurité
    Write-Host "  → Vérification headers de sécurité..." -ForegroundColor White
    
    if ($response.Headers.ContainsKey("X-Frame-Options") -or 
        $response.Headers.ContainsKey("X-Content-Type-Options")) {
        Write-Host "  ✅ Headers de sécurité présents" -ForegroundColor Green
        $RESULTS.Passed++
    }
    else {
        Write-Host "  ⚠️  Headers de sécurité manquants" -ForegroundColor Yellow
        $RESULTS.Warnings++
    }
    
}
catch {
    Write-Host "  ⚠️  Erreur vérification sécurité: $($_.Exception.Message)" -ForegroundColor Yellow
    $RESULTS.Warnings++
}

#endregion

#region Rapport final

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor White
Write-Host "║                    RAPPORT DES TESTS                               ║" -ForegroundColor White
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor White
Write-Host ""

Write-Host "📊 RÉSULTATS" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""
Write-Host "  ✅ Tests réussis : $($RESULTS.Passed)" -ForegroundColor Green
Write-Host "  ⚠️  Avertissements : $($RESULTS.Warnings)" -ForegroundColor Yellow
Write-Host "  ❌ Tests échoués : $($RESULTS.Failed)" -ForegroundColor Red
Write-Host ""

$totalTests = $RESULTS.Passed + $RESULTS.Warnings + $RESULTS.Failed
$successRate = if ($totalTests -gt 0) { [math]::Round(($RESULTS.Passed / $totalTests) * 100, 2) } else { 0 }

Write-Host "  Taux de réussite : $successRate%" -ForegroundColor White
Write-Host ""

if ($RESULTS.Failed -eq 0 -and $RESULTS.Warnings -eq 0) {
    Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║              ✅ TOUS LES TESTS SONT PASSÉS ! ✅                ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    exit 0
}
elseif ($RESULTS.Failed -eq 0) {
    Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║     ⚠️  TESTS PASSÉS AVEC AVERTISSEMENTS ⚠️                   ║" -ForegroundColor Yellow
    Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Vérifiez les avertissements ci-dessus pour optimiser le déploiement." -ForegroundColor Yellow
    exit 0
}
else {
    Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "║              ❌ CERTAINS TESTS ONT ÉCHOUÉ ❌                   ║" -ForegroundColor Red
    Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Red
    Write-Host ""
    Write-Host "Corrigez les erreurs ci-dessus avant de passer en production." -ForegroundColor Red
    exit 1
}

#endregion

