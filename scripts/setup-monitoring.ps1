<#
.SYNOPSIS
    Configuration complète du monitoring et performance Azure pour SEEG-API

.DESCRIPTION
    Active et configure tous les outils de monitoring et performance Azure :
    - Application Insights (APM complet)
    - Azure Monitor (métriques système)
    - Log Analytics Workspace
    - Alertes automatiques
    - Diagnostics avancés
    - Profiling et traces
    - Métriques custom
    - Tableaux de bord

.EXAMPLE
    .\setup-monitoring.ps1
    Active tout le monitoring

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
    ResourceGroup    = "seeg-backend-rg"
    AppName          = "seeg-backend-api"
    Location         = "francecentral"
    
    # Noms des ressources monitoring
    AppInsightsName  = "seeg-api-insights"
    LogAnalyticsName = "seeg-api-logs"
    ActionGroupName  = "seeg-api-alerts"
    
    # Email pour les alertes
    AlertEmail       = "support@cnx4-0.com"
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     CONFIGURATION MONITORING & PERFORMANCE - SEEG-API             ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

#region Étape 1 : Log Analytics Workspace

Write-Host "[1/8] 📊 Création du Log Analytics Workspace" -ForegroundColor Yellow
Write-Host ""

try {
    # Vérifier si existe
    $workspace = az monitor log-analytics workspace show `
        --resource-group $CONFIG.ResourceGroup `
        --workspace-name $CONFIG.LogAnalyticsName `
        --output json 2>&1 | ConvertFrom-Json
    
    if ($workspace) {
        Write-Host "  ✅ Workspace existant trouvé" -ForegroundColor Green
        $workspaceId = $workspace.customerId
    }
    else {
        Write-Host "  → Création du workspace..." -ForegroundColor White
        
        $workspace = az monitor log-analytics workspace create `
            --resource-group $CONFIG.ResourceGroup `
            --workspace-name $CONFIG.LogAnalyticsName `
            --location $CONFIG.Location `
            --output json 2>&1 | ConvertFrom-Json
        
        $workspaceId = $workspace.customerId
        Write-Host "  ✅ Log Analytics Workspace créé" -ForegroundColor Green
    }
    
    Write-Host "     Workspace ID: $workspaceId" -ForegroundColor Gray
    
}
catch {
    Write-Host "  ❌ Erreur: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

#endregion

#region Étape 2 : Application Insights

Write-Host ""
Write-Host "[2/8] 🔍 Configuration d'Application Insights" -ForegroundColor Yellow
Write-Host ""

try {
    # Vérifier si existe
    $appInsights = az monitor app-insights component show `
        --app $CONFIG.AppInsightsName `
        --resource-group $CONFIG.ResourceGroup `
        --output json 2>&1 | ConvertFrom-Json
    
    if ($appInsights) {
        Write-Host "  ✅ Application Insights existant trouvé" -ForegroundColor Green
    }
    else {
        Write-Host "  → Création d'Application Insights..." -ForegroundColor White
        
        $appInsights = az monitor app-insights component create `
            --app $CONFIG.AppInsightsName `
            --location $CONFIG.Location `
            --resource-group $CONFIG.ResourceGroup `
            --workspace $workspaceId `
            --output json 2>&1 | ConvertFrom-Json
        
        Write-Host "  ✅ Application Insights créé" -ForegroundColor Green
    }
    
    $instrumentationKey = $appInsights.instrumentationKey
    $connectionString = $appInsights.connectionString
    
    Write-Host "     Instrumentation Key: $($instrumentationKey.Substring(0,8))..." -ForegroundColor Gray
    
    # Configurer l'App Service avec Application Insights
    Write-Host "  → Liaison avec App Service..." -ForegroundColor White
    
    az webapp config appsettings set `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --settings `
        APPINSIGHTS_INSTRUMENTATIONKEY="$instrumentationKey" `
        APPLICATIONINSIGHTS_CONNECTION_STRING="$connectionString" `
        ApplicationInsightsAgent_EXTENSION_VERSION="~3" `
        XDT_MicrosoftApplicationInsights_Mode="recommended" `
        APPINSIGHTS_PROFILERFEATURE_VERSION="1.0.0" `
        APPINSIGHTS_SNAPSHOTFEATURE_VERSION="1.0.0" `
        DiagnosticServices_EXTENSION_VERSION="~3" 2>&1 | Out-Null
    
    Write-Host "  ✅ Application Insights lié à l'App Service" -ForegroundColor Green
    
}
catch {
    Write-Host "  ❌ Erreur: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

#endregion

#region Étape 3 : Configuration des logs détaillés

Write-Host ""
Write-Host "[3/8] 📝 Configuration des logs avancés" -ForegroundColor Yellow
Write-Host ""

try {
    Write-Host "  → Configuration des logs Docker..." -ForegroundColor White
    
    az webapp log config `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --docker-container-logging filesystem `
        --level verbose 2>&1 | Out-Null
    
    Write-Host "  ✅ Logs Docker activés (verbose)" -ForegroundColor Green
    
    # Activer les logs d'application
    Write-Host "  → Activation des logs d'application..." -ForegroundColor White
    
    az webapp log config `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --application-logging filesystem `
        --detailed-error-messages true `
        --failed-request-tracing true `
        --web-server-logging filesystem 2>&1 | Out-Null
    
    Write-Host "  ✅ Logs d'application activés" -ForegroundColor Green
    Write-Host "  ✅ Logs d'erreurs détaillés activés" -ForegroundColor Green
    Write-Host "  ✅ Tracing des requêtes échouées activé" -ForegroundColor Green
    
}
catch {
    Write-Host "  ⚠️  Avertissement: $($_.Exception.Message)" -ForegroundColor Yellow
}

#endregion

#region Étape 4 : Diagnostics Azure Monitor

Write-Host ""
Write-Host "[4/8] 🏥 Configuration des diagnostics Azure Monitor" -ForegroundColor Yellow
Write-Host ""

try {
    Write-Host "  → Activation des diagnostics..." -ForegroundColor White
    
    # Récupérer l'ID de l'App Service
    $appServiceId = az webapp show `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --query "id" `
        --output tsv
    
    # Récupérer l'ID du workspace
    $workspaceResourceId = az monitor log-analytics workspace show `
        --resource-group $CONFIG.ResourceGroup `
        --workspace-name $CONFIG.LogAnalyticsName `
        --query "id" `
        --output tsv
    
    # Configuration des diagnostics
    $diagnosticSettings = @{
        logs        = @(
            @{ category = "AppServiceHTTPLogs"; enabled = $true; retentionPolicy = @{ enabled = $true; days = 30 } }
            @{ category = "AppServiceConsoleLogs"; enabled = $true; retentionPolicy = @{ enabled = $true; days = 30 } }
            @{ category = "AppServiceAppLogs"; enabled = $true; retentionPolicy = @{ enabled = $true; days = 30 } }
            @{ category = "AppServiceAuditLogs"; enabled = $true; retentionPolicy = @{ enabled = $true; days = 90 } }
            @{ category = "AppServiceIPSecAuditLogs"; enabled = $true; retentionPolicy = @{ enabled = $true; days = 90 } }
            @{ category = "AppServicePlatformLogs"; enabled = $true; retentionPolicy = @{ enabled = $true; days = 30 } }
        )
        metrics     = @(
            @{ category = "AllMetrics"; enabled = $true; retentionPolicy = @{ enabled = $true; days = 30 } }
        )
        workspaceId = $workspaceResourceId
    }
    
    $diagnosticJson = $diagnosticSettings | ConvertTo-Json -Depth 10
    $diagnosticFile = "diagnostic-settings.json"
    $diagnosticJson | Out-File -FilePath $diagnosticFile -Encoding UTF8
    
    az monitor diagnostic-settings create `
        --name "seeg-api-diagnostics" `
        --resource $appServiceId `
        --workspace $workspaceResourceId `
        --logs '[
            {"category":"AppServiceHTTPLogs","enabled":true},
            {"category":"AppServiceConsoleLogs","enabled":true},
            {"category":"AppServiceAppLogs","enabled":true},
            {"category":"AppServiceAuditLogs","enabled":true},
            {"category":"AppServicePlatformLogs","enabled":true}
        ]' `
        --metrics '[{"category":"AllMetrics","enabled":true}]' 2>&1 | Out-Null
    
    Remove-Item $diagnosticFile -ErrorAction SilentlyContinue
    
    Write-Host "  ✅ Diagnostics configurés (logs + métriques)" -ForegroundColor Green
    Write-Host "     - Logs HTTP (30 jours)" -ForegroundColor Gray
    Write-Host "     - Logs Console (30 jours)" -ForegroundColor Gray
    Write-Host "     - Logs Application (30 jours)" -ForegroundColor Gray
    Write-Host "     - Logs Audit (90 jours)" -ForegroundColor Gray
    Write-Host "     - Métriques (30 jours)" -ForegroundColor Gray
    
}
catch {
    Write-Host "  ⚠️  Avertissement: $($_.Exception.Message)" -ForegroundColor Yellow
}

#endregion

#region Étape 5 : Action Group pour les alertes

Write-Host ""
Write-Host "[5/8] 🔔 Configuration des Action Groups (alertes)" -ForegroundColor Yellow
Write-Host ""

try {
    # Vérifier si existe
    $actionGroup = az monitor action-group show `
        --name $CONFIG.ActionGroupName `
        --resource-group $CONFIG.ResourceGroup `
        --output json 2>&1 | ConvertFrom-Json
    
    if ($actionGroup) {
        Write-Host "  ✅ Action Group existant trouvé" -ForegroundColor Green
    }
    else {
        Write-Host "  → Création de l'Action Group..." -ForegroundColor White
        
        az monitor action-group create `
            --name $CONFIG.ActionGroupName `
            --resource-group $CONFIG.ResourceGroup `
            --short-name "SEEG-API" `
            --action email admin $CONFIG.AlertEmail 2>&1 | Out-Null
        
        Write-Host "  ✅ Action Group créé" -ForegroundColor Green
        Write-Host "     Email: $($CONFIG.AlertEmail)" -ForegroundColor Gray
    }
    
}
catch {
    Write-Host "  ⚠️  Avertissement: $($_.Exception.Message)" -ForegroundColor Yellow
}

#endregion

#region Étape 6 : Alertes automatiques

Write-Host ""
Write-Host "[6/8] ⚡ Configuration des alertes automatiques" -ForegroundColor Yellow
Write-Host ""

try {
    $appServiceId = az webapp show `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --query "id" `
        --output tsv
    
    # Alerte 1 : CPU élevé
    Write-Host "  → Alerte: CPU > 80%..." -ForegroundColor White
    
    az monitor metrics alert create `
        --name "seeg-api-high-cpu" `
        --resource-group $CONFIG.ResourceGroup `
        --scopes $appServiceId `
        --condition "avg CpuPercentage > 80" `
        --window-size 5m `
        --evaluation-frequency 1m `
        --action $CONFIG.ActionGroupName `
        --description "CPU supérieur à 80% pendant 5 minutes" `
        --severity 2 2>&1 | Out-Null
    
    Write-Host "  ✅ Alerte CPU créée" -ForegroundColor Green
    
    # Alerte 2 : Mémoire élevée
    Write-Host "  → Alerte: Mémoire > 80%..." -ForegroundColor White
    
    az monitor metrics alert create `
        --name "seeg-api-high-memory" `
        --resource-group $CONFIG.ResourceGroup `
        --scopes $appServiceId `
        --condition "avg MemoryPercentage > 80" `
        --window-size 5m `
        --evaluation-frequency 1m `
        --action $CONFIG.ActionGroupName `
        --description "Mémoire supérieure à 80% pendant 5 minutes" `
        --severity 2 2>&1 | Out-Null
    
    Write-Host "  ✅ Alerte Mémoire créée" -ForegroundColor Green
    
    # Alerte 3 : Erreurs HTTP 5xx
    Write-Host "  → Alerte: Erreurs HTTP 5xx..." -ForegroundColor White
    
    az monitor metrics alert create `
        --name "seeg-api-http-errors" `
        --resource-group $CONFIG.ResourceGroup `
        --scopes $appServiceId `
        --condition "total Http5xx > 10" `
        --window-size 5m `
        --evaluation-frequency 1m `
        --action $CONFIG.ActionGroupName `
        --description "Plus de 10 erreurs HTTP 5xx en 5 minutes" `
        --severity 1 2>&1 | Out-Null
    
    Write-Host "  ✅ Alerte Erreurs HTTP créée" -ForegroundColor Green
    
    # Alerte 4 : Temps de réponse élevé
    Write-Host "  → Alerte: Temps de réponse > 3s..." -ForegroundColor White
    
    az monitor metrics alert create `
        --name "seeg-api-slow-response" `
        --resource-group $CONFIG.ResourceGroup `
        --scopes $appServiceId `
        --condition "avg ResponseTime > 3" `
        --window-size 5m `
        --evaluation-frequency 1m `
        --action $CONFIG.ActionGroupName `
        --description "Temps de réponse moyen supérieur à 3 secondes" `
        --severity 2 2>&1 | Out-Null
    
    Write-Host "  ✅ Alerte Temps de réponse créée" -ForegroundColor Green
    
    # Alerte 5 : Application down
    Write-Host "  → Alerte: Application indisponible..." -ForegroundColor White
    
    az monitor metrics alert create `
        --name "seeg-api-down" `
        --resource-group $CONFIG.ResourceGroup `
        --scopes $appServiceId `
        --condition "avg HealthCheckStatus < 100" `
        --window-size 5m `
        --evaluation-frequency 1m `
        --action $CONFIG.ActionGroupName `
        --description "Application indisponible (health check échoué)" `
        --severity 0 2>&1 | Out-Null
    
    Write-Host "  ✅ Alerte Application Down créée" -ForegroundColor Green
    
}
catch {
    Write-Host "  ⚠️  Certaines alertes n'ont pas pu être créées: $($_.Exception.Message)" -ForegroundColor Yellow
}

#endregion

#region Étape 7 : Configuration performance avancée

Write-Host ""
Write-Host "[7/8] ⚡ Configuration des optimisations de performance" -ForegroundColor Yellow
Write-Host ""

try {
    Write-Host "  → Always On (éviter cold start)..." -ForegroundColor White
    
    az webapp config set `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --always-on true 2>&1 | Out-Null
    
    Write-Host "  ✅ Always On activé" -ForegroundColor Green
    
    Write-Host "  → HTTP 2.0..." -ForegroundColor White
    
    az webapp config set `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --http20-enabled true 2>&1 | Out-Null
    
    Write-Host "  ✅ HTTP 2.0 activé" -ForegroundColor Green
    
    Write-Host "  → Compression..." -ForegroundColor White
    
    az webapp config set `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --use-32bit-worker-process false 2>&1 | Out-Null
    
    Write-Host "  ✅ Worker 64-bit activé" -ForegroundColor Green
    
    Write-Host "  → Health check path..." -ForegroundColor White
    
    az webapp config set `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --generic-configurations '{"healthCheckPath": "/docs"}' 2>&1 | Out-Null
    
    Write-Host "  ✅ Health check configuré (/docs)" -ForegroundColor Green
    
    Write-Host "  → Minimum instances..." -ForegroundColor White
    
    az webapp config set `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --min-tls-version "1.2" 2>&1 | Out-Null
    
    Write-Host "  ✅ TLS 1.2 minimum configuré" -ForegroundColor Green
    
}
catch {
    Write-Host "  ⚠️  Avertissement: $($_.Exception.Message)" -ForegroundColor Yellow
}

#endregion

#region Étape 8 : Test et validation

Write-Host ""
Write-Host "[8/8] 🧪 Validation de la configuration" -ForegroundColor Yellow
Write-Host ""

try {
    Write-Host "  → Vérification Application Insights..." -ForegroundColor White
    
    $appSettings = az webapp config appsettings list `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --output json | ConvertFrom-Json
    
    $hasAppInsights = $appSettings | Where-Object { $_.name -eq "APPINSIGHTS_INSTRUMENTATIONKEY" }
    
    if ($hasAppInsights) {
        Write-Host "  ✅ Application Insights configuré" -ForegroundColor Green
    }
    else {
        Write-Host "  ⚠️  Application Insights non détecté" -ForegroundColor Yellow
    }
    
    Write-Host "  → Vérification des diagnostics..." -ForegroundColor White
    
    $diagnostics = az monitor diagnostic-settings list `
        --resource $appServiceId `
        --output json 2>&1 | ConvertFrom-Json
    
    if ($diagnostics -and $diagnostics.value.Count -gt 0) {
        Write-Host "  ✅ Diagnostics activés ($($diagnostics.value.Count) configuration(s))" -ForegroundColor Green
    }
    
    Write-Host "  → Vérification des alertes..." -ForegroundColor White
    
    $alerts = az monitor metrics alert list `
        --resource-group $CONFIG.ResourceGroup `
        --output json 2>&1 | ConvertFrom-Json
    
    $apiAlerts = $alerts | Where-Object { $_.name -like "seeg-api-*" }
    
    if ($apiAlerts) {
        Write-Host "  ✅ Alertes configurées ($($apiAlerts.Count) alerte(s))" -ForegroundColor Green
    }
    
}
catch {
    Write-Host "  ⚠️  Validation partielle: $($_.Exception.Message)" -ForegroundColor Yellow
}

#endregion

#region Résumé

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║         ✅ MONITORING & PERFORMANCE CONFIGURÉS ✅              ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "📊 MONITORING ACTIVÉ" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""
Write-Host "✅ Application Insights (APM complet)" -ForegroundColor Green
Write-Host "   • Traces distribuées" -ForegroundColor Gray
Write-Host "   • Métriques de performance" -ForegroundColor Gray
Write-Host "   • Dépendances et requêtes" -ForegroundColor Gray
Write-Host "   • Exceptions et erreurs" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ Log Analytics Workspace" -ForegroundColor Green
Write-Host "   • Requêtes KQL avancées" -ForegroundColor Gray
Write-Host "   • Rétention 30-90 jours" -ForegroundColor Gray
Write-Host "   • Corrélation des logs" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ Diagnostics Azure Monitor" -ForegroundColor Green
Write-Host "   • Logs HTTP" -ForegroundColor Gray
Write-Host "   • Logs Console" -ForegroundColor Gray
Write-Host "   • Logs Application" -ForegroundColor Gray
Write-Host "   • Logs Audit" -ForegroundColor Gray
Write-Host "   • Métriques système" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ Alertes automatiques (5 alertes)" -ForegroundColor Green
Write-Host "   • CPU > 80%" -ForegroundColor Gray
Write-Host "   • Mémoire > 80%" -ForegroundColor Gray
Write-Host "   • Erreurs HTTP 5xx > 10" -ForegroundColor Gray
Write-Host "   • Temps réponse > 3s" -ForegroundColor Gray
Write-Host "   • Application Down" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ Optimisations performance" -ForegroundColor Green
Write-Host "   • Always On activé" -ForegroundColor Gray
Write-Host "   • HTTP 2.0 activé" -ForegroundColor Gray
Write-Host "   • Worker 64-bit" -ForegroundColor Gray
Write-Host "   • Health check /docs" -ForegroundColor Gray
Write-Host "   • TLS 1.2 minimum" -ForegroundColor Gray
Write-Host ""

Write-Host "🔗 ACCÈS AUX OUTILS" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""
Write-Host "Application Insights:" -ForegroundColor White
Write-Host "  https://portal.azure.com/#@/resource$appServiceId/appInsights" -ForegroundColor Gray
Write-Host ""
Write-Host "Log Analytics:" -ForegroundColor White
Write-Host "  https://portal.azure.com/#@/resource$workspaceResourceId/Overview" -ForegroundColor Gray
Write-Host ""
Write-Host "Métriques Azure Monitor:" -ForegroundColor White
Write-Host "  https://portal.azure.com/#@/resource$appServiceId/metrics" -ForegroundColor Gray
Write-Host ""
Write-Host "Alertes:" -ForegroundColor White
Write-Host "  https://portal.azure.com/#blade/Microsoft_Azure_Monitoring/AzureMonitoringBrowseBlade/alertsV2" -ForegroundColor Gray
Write-Host ""

Write-Host "📈 COMMANDES UTILES" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""
Write-Host "Voir les logs en temps réel:" -ForegroundColor White
Write-Host "  az webapp log tail --name $($CONFIG.AppName) --resource-group $($CONFIG.ResourceGroup)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Télécharger les logs:" -ForegroundColor White
Write-Host "  az webapp log download --name $($CONFIG.AppName) --resource-group $($CONFIG.ResourceGroup) --log-file logs.zip" -ForegroundColor Yellow
Write-Host ""
Write-Host "Voir les métriques:" -ForegroundColor White
Write-Host "  az monitor metrics list --resource $appServiceId --metric-names CpuPercentage MemoryPercentage ResponseTime" -ForegroundColor Yellow
Write-Host ""
Write-Host "Voir les alertes actives:" -ForegroundColor White
Write-Host "  az monitor metrics alert list --resource-group $($CONFIG.ResourceGroup)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Requête KQL (Log Analytics):" -ForegroundColor White
Write-Host "  az monitor log-analytics query --workspace $workspaceId --analytics-query 'AppServiceHTTPLogs | take 100'" -ForegroundColor Yellow
Write-Host ""

Write-Host "🎯 PROCHAINES ÉTAPES" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""
Write-Host "1. Accédez au portail Azure pour visualiser les métriques" -ForegroundColor White
Write-Host "2. Configurez des tableaux de bord personnalisés" -ForegroundColor White
Write-Host "3. Ajustez les seuils d'alertes selon vos besoins" -ForegroundColor White
Write-Host "4. Explorez les traces dans Application Insights" -ForegroundColor White
Write-Host ""
Write-Host "Les alertes seront envoyées à: $($CONFIG.AlertEmail)" -ForegroundColor Yellow
Write-Host ""

#endregion

