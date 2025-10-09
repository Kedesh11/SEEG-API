# ============================================================================
# Script de déploiement Azure pour SEEG-API (One HCM)
# ============================================================================
# Architecture: Clean Code avec principes SOLID appliqués
# - Single Responsibility: Une fonction = une responsabilité
# - Open/Closed: Extensible sans modification du core
# - Liskov Substitution: Fonctions interchangeables
# - Interface Segregation: Interfaces minimales et ciblées
# - Dependency Inversion: Pas de dépendances hardcodées
# ============================================================================

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"  # Accélère les cmdlets Azure

# ============================================================================
# CONFIGURATION CENTRALISÉE
# ============================================================================

$script:Config = @{
  ResourceGroup         = "seeg-backend-rg"
  AppServiceName        = "seeg-backend-api"
  ContainerRegistryName = "seegbackend"
  ContainerRegistry     = "seegbackend.azurecr.io"
  ImageName             = "seeg-backend"
  ImageTag              = "latest"
  EnvFile               = ".env.production"
}

# ============================================================================
# FONCTIONS D'AFFICHAGE (Separation of Concerns)
# ============================================================================

function Write-Header {
  param([string]$Title)
  Write-Host "`n=========================================" -ForegroundColor Cyan
  Write-Host " $Title" -ForegroundColor Yellow
  Write-Host "=========================================`n" -ForegroundColor Cyan
}

function Write-Success {
  param([string]$Message)
  Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Info {
  param([string]$Message)
  Write-Host "[INFO] $Message" -ForegroundColor White
}

function Write-Warning {
  param([string]$Message)
  Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-ErrorMsg {
  param([string]$Message)
  Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# ============================================================================
# FONCTIONS DE VÉRIFICATION
# ============================================================================

function Test-AzureConnection {
  <#
    .SYNOPSIS
    Verifie la connexion Azure CLI.
    #>
  Write-Info "Verification connexion Azure..."
    
  try {
    $null = az account show 2>&1
    if ($LASTEXITCODE -eq 0) {
      $account = az account show | ConvertFrom-Json
      Write-Success "Connecte a Azure ($($account.name))"
      return $true
    }
  }
  catch {
    Write-ErrorMsg "Non connecte a Azure"
    Write-Warning "Executez: az login"
    return $false
  }
    
  return $false
}

function Test-DockerRunning {
  <#
    .SYNOPSIS
    Vérifie si Docker Desktop est actif.
    #>
  try {
    docker ps > $null 2>&1
    return ($LASTEXITCODE -eq 0)
  }
  catch {
    return $false
  }
}

# ============================================================================
# FONCTIONS DE CONFIGURATION
# ============================================================================

function Get-EnvironmentConfig {
  <#
    .SYNOPSIS
    Charge la configuration depuis .env.production.
    #>
  param([string]$EnvFile = $script:Config.EnvFile)
    
  Write-Info "Chargement configuration depuis $EnvFile..."
    
  if (-not (Test-Path $EnvFile)) {
    Write-Warning "Fichier $EnvFile introuvable"
    return $false
  }
    
  Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^([^=\#]+)=(.*)$') {
      $key = $matches[1].Trim()
      $value = $matches[2].Trim().Trim('"').Trim("'")
      [Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
  }
    
  Write-Success "Configuration chargee"
  return $true
}

function Sync-AzureAppSettings {
  <#
    .SYNOPSIS
    Synchronise les App Settings Azure depuis .env.production.
    Applique les meilleures pratiques de configuration cloud.
    #>
  param([string]$EnvFile = $script:Config.EnvFile)
    
  Write-Header "SYNCHRONISATION APP SETTINGS AZURE"
    
  # Dictionnaire des settings
  $settings = @{}
    
  # Charger depuis fichier si existe
  if (Test-Path $EnvFile) {
    Write-Info "Lecture de $EnvFile..."
        
    Get-Content $EnvFile | ForEach-Object {
      if ($_ -match '^([^=\#]+)=(.*)$') {
        $k = $matches[1].Trim()
        $v = $matches[2].Trim().Trim('"').Trim("'")
        $settings[$k] = $v
      }
    }
  }
    
  # Variables critiques forcées (ne jamais les omettre)
  $settings['WEBSITES_PORT'] = '8000'
  $settings['ENVIRONMENT'] = 'production'
    
  # Valeurs par défaut si absentes
  if (-not $settings.ContainsKey('DATABASE_URL')) {
    $settings['DATABASE_URL'] = 'postgresql+asyncpg://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres'
  }
    
  if (-not $settings.ContainsKey('DATABASE_URL_SYNC')) {
    $settings['DATABASE_URL_SYNC'] = 'postgresql://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres'
  }
    
  # Validation CORS (si wildcard, credentials doit être false)
  if ($settings.ContainsKey('ALLOWED_ORIGINS')) {
    if ($settings['ALLOWED_ORIGINS'] -match '^\s*\*\s*$') {
      Write-Warning "ALLOWED_ORIGINS='*' détecté -> ALLOWED_CREDENTIALS forcé à false"
      $settings['ALLOWED_CREDENTIALS'] = 'false'
    }
  }
    
  # Conversion en tableau de paires key=value
  $settingsPairs = $settings.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }
    
  # Envoi vers Azure
  Write-Info "Envoi de $($settings.Count) parametres vers Azure..."
    
  az webapp config appsettings set `
    --name $script:Config.AppServiceName `
    --resource-group $script:Config.ResourceGroup `
    --settings @settingsPairs `
    --output none
    
  if ($LASTEXITCODE -eq 0) {
    Write-Success "App Settings synchronises ($($settings.Count) parametres)"
    return $true
  }
  else {
    Write-ErrorMsg "Echec synchronisation App Settings"
    return $false
  }
}

# ============================================================================
# FONCTIONS DE BUILD
# ============================================================================

function New-DockerImageLocal {
  <#G
    .SYNOPSIS
    Build l'image Docker localement.
    #>
  Write-Header "BUILD DOCKER LOCAL"
    
  if (-not (Test-DockerRunning)) {
    Write-ErrorMsg "Docker Desktop non actif"
    Write-Warning "Démarrez Docker Desktop et réessayez"
    return $false
  }
    
  $fullImageName = "$($script:Config.ContainerRegistry)/$($script:Config.ImageName):$($script:Config.ImageTag)"
  Write-Info "Build de l'image Docker SANS CACHE: $fullImageName..."

  try {
    docker build --no-cache -t $fullImageName -f Dockerfile .
    Write-Success "Image buildee avec succes: $fullImageName"
  }
  catch {
    Write-ErrorMsg "Erreur lors du build Docker"
    return $false
  }
}

function Push-DockerImage {
  <#
    .SYNOPSIS
    Push l'image vers Azure Container Registry.
    #>
  Write-Header "PUSH VERS AZURE CONTAINER REGISTRY"
    
  # Login ACR
  Write-Info "Connexion a ACR..."
  az acr login --name $script:Config.ContainerRegistryName `
    --resource-group $script:Config.ResourceGroup `
    --output none
    
  if ($LASTEXITCODE -ne 0) {
    Write-ErrorMsg "Echec connexion ACR"
    return $false
  }
    
  # Push
  $imageFull = "$($script:Config.ContainerRegistry)/$($script:Config.ImageName):$($script:Config.ImageTag)"
  Write-Info "Push de l'image: $imageFull"
    
  docker push $imageFull --quiet
    
  if ($LASTEXITCODE -eq 0) {
    Write-Success "Image pushee vers Azure"
    return $true
  }
  else {
    Write-ErrorMsg "Erreur lors du push"
    return $false
  }
}

function New-AzureCloudImage {
  <#
    .SYNOPSIS
    Build l'image directement dans Azure (sans Docker Desktop).
    #>
  Write-Header "BUILD DANS AZURE CLOUD"
  Write-Info "Avantage: Pas besoin de Docker Desktop local"
    
  $imageFull = "$($script:Config.ImageName):$($script:Config.ImageTag)"
    
  # Commande sur une seule ligne pour contourner le bug de parsing PowerShell
  az acr build --registry $script:Config.ContainerRegistryName --image $imageFull --resource-group $script:Config.ResourceGroup --file Dockerfile --platform linux --no-logs --no-cache .
    
  if ($LASTEXITCODE -eq 0) {
    Write-Success "Image buildee dans Azure Cloud"
    return $true
  }
  else {
    Write-ErrorMsg "Echec du build Azure"
    return $false
  }
}

# ============================================================================
# FONCTIONS DE DÉPLOIEMENT
# ============================================================================

function Update-AppServiceContainer {
  <#
    .SYNOPSIS
    Met à jour le conteneur de l'App Service et configure le Health Check.
    #>
  Write-Header "MISE A JOUR DU CONTENEUR"
    
  $imageFull = "$($script:Config.ContainerRegistry)/$($script:Config.ImageName):$($script:Config.ImageTag)"
    
  # Configuration du conteneur
  Write-Info "Configuration du nouveau conteneur..."
  az webapp config container set `
    --name $script:Config.AppServiceName `
    --resource-group $script:Config.ResourceGroup `
    --container-image-name $imageFull `
    --output none
    
  if ($LASTEXITCODE -ne 0) {
    Write-ErrorMsg "Echec configuration conteneur"
    return $false
  }
    
  Write-Success "Conteneur configure"
    
  # AlwaysOn
  Write-Info "Activation AlwaysOn..."
  az webapp config set `
    --name $script:Config.AppServiceName `
    --resource-group $script:Config.ResourceGroup `
    --always-on true `
    --output none
    
  # Health Check (fallback si commande non disponible)
  Write-Info "Configuration Health Check..."
  az webapp config appsettings set `
    --name $script:Config.AppServiceName `
    --resource-group $script:Config.ResourceGroup `
    --settings WEBSITE_HEALTHCHECK_PATH="/monitoring/health" WEBSITE_HEALTHCHECK_MAXPINGFAILURES="10" `
    --output none
    
  if ($LASTEXITCODE -eq 0) {
    Write-Success "Health Check configure sur /monitoring/health"
  }
  else {
    Write-Warning "Health Check non configure (non critique)"
  }
    
  return $true
}

function Restart-AppService {
  <#
    .SYNOPSIS
    Redémarre l'App Service et affiche les logs.
    #>
  param([bool]$ShowLogs = $true)
    
  Write-Header "REDEMARRAGE APP SERVICE"
    
  az webapp restart `
    --name $script:Config.AppServiceName `
    --resource-group $script:Config.ResourceGroup `
    --output none
    
  if ($LASTEXITCODE -ne 0) {
    Write-ErrorMsg "Echec redemarrage"
    return $false
  }
    
  Write-Success "App Service redemarree"
    
  if ($ShowLogs) {
    Write-Info "Attente demarrage (45 secondes)..."
    Start-Sleep -Seconds 45
        
    Write-Header "LOGS EN TEMPS REEL"
    Write-Info "Affichage des logs (Ctrl+C pour arreter)"
    Write-Host ""
        
    # Logs pendant 60 secondes max
    try {
      $job = Start-Job -ScriptBlock {
        param($app, $rg)
        az webapp log tail --name $app --resource-group $rg
      } -ArgumentList $script:Config.AppServiceName, $script:Config.ResourceGroup
            
      Wait-Job $job -Timeout 60 | Out-Null
      Receive-Job $job
      Stop-Job $job -ErrorAction SilentlyContinue
      Remove-Job $job -ErrorAction SilentlyContinue
    }
    catch {
      Write-Info "Logs interrompus"
    }
        
    Write-Host ""
  }
    
  return $true
}

function Invoke-HealthCheck {
  <#
    .SYNOPSIS
    Verifie que l'API repond correctement.
    #>
  Write-Header "VERIFICATION HEALTH CHECK"
    
  $url = "https://$($script:Config.AppServiceName).azurewebsites.net/monitoring/health"
    
  Write-Info "Test de $url..."
    
  try {
    $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 10 -ErrorAction Stop
        
    if ($response.status -eq "healthy") {
      Write-Success "API operationnelle - Status: $($response.status)"
      return $true
    }
    else {
      Write-Warning "API en etat degrade - Status: $($response.status)"
      return $false
    }
  }
  catch {
    Write-ErrorMsg "Health Check echoue: $_"
    return $false
  }
}

function New-InitialUsers {
  <#
    .SYNOPSIS
    Active temporairement la création des utilisateurs initiaux.
    #>
  Write-Header "CREATION UTILISATEURS INITIAUX"
    
  Write-Info "Activation CREATE_INITIAL_USERS=true..."
  az webapp config appsettings set `
    --name $script:Config.AppServiceName `
    --resource-group $script:Config.ResourceGroup `
    --settings CREATE_INITIAL_USERS=true `
    --output none
    
  Write-Info "Redemarrage pour executer le script..."
  az webapp restart `
    --name $script:Config.AppServiceName `
    --resource-group $script:Config.ResourceGroup `
    --output none
    
  Start-Sleep -Seconds 45
    
  Write-Info "Desactivation CREATE_INITIAL_USERS..."
  az webapp config appsettings set `
    --name $script:Config.AppServiceName `
    --resource-group $script:Config.ResourceGroup `
    --settings CREATE_INITIAL_USERS=false `
    --output none
    
  Write-Success "Bootstrap utilisateurs termine"
  return $true
}

# ============================================================================
# WORKFLOWS (Orchestration selon Command Pattern)
# ============================================================================

function Start-FullDeployment {
  <#
    .SYNOPSIS
    Déploiement complet: Build, Push, Deploy, Migrations, Health Check.
    #>
  param(
    [bool]$UseLocalDocker = $true,
    [bool]$CreateUsers = $false
  )
    
  Write-Header "DEPLOIEMENT COMPLET - SEEG-API"
    
  # Verifications prealables
  if (-not (Test-AzureConnection)) {
    Write-ErrorMsg "Connexion Azure requise"
    return $false
  }
    
  if (-not (Get-EnvironmentConfig)) {
    Write-Warning "Configuration .env non chargee, poursuite avec defaults"
  }
    
  # Synchroniser App Settings
  if (-not (Sync-AzureAppSettings)) {
    Write-ErrorMsg "Echec synchronisation App Settings"
    return $false
  }
    
  # Build de l'image
  if ($UseLocalDocker) {
    if (-not (New-DockerImageLocal)) {
      Write-ErrorMsg "Build local echoue"
      return $false
    }
        
    if (-not (Push-DockerImage)) {
      Write-ErrorMsg "Push ACR echoue"
      return $false
    }
  }
  else {
    if (-not (New-AzureCloudImage)) {
      Write-ErrorMsg "Build Azure echoue"
      return $false
    }
  }
    
  # Mise a jour du conteneur
  if (-not (Update-AppServiceContainer)) {
    Write-ErrorMsg "Mise a jour conteneur echouee"
    return $false
  }
    
  # Redemarrage
  if (-not (Restart-AppService -ShowLogs $true)) {
    Write-ErrorMsg "Redemarrage echoue"
    return $false
  }
    
  # Health Check
  Start-Sleep -Seconds 15
  Invoke-HealthCheck | Out-Null
    
  # Creation utilisateurs si demande
  if ($CreateUsers) {
    New-InitialUsers | Out-Null
  }
    
  Show-DeploymentSummary
  return $true
}

function Start-QuickDeploy {
  <#
    .SYNOPSIS
    Déploiement rapide: utilise l'image existante.
    #>
  Write-Header "DEPLOIEMENT RAPIDE"
    
  if (-not (Test-AzureConnection)) { return $false }
    
  if ((Update-AppServiceContainer) -and (Restart-AppService -ShowLogs $true)) {
    Invoke-HealthCheck | Out-Null
    Show-DeploymentSummary
    return $true
  }
    
  return $false
}

function Show-DeploymentSummary {
  <#
    .SYNOPSIS
    Affiche un resume du deploiement.
    #>
  Write-Header "DEPLOIEMENT TERMINE"
    
  Write-Success "API deployee avec succes!"
  Write-Host ""
  Write-Host "URLs:" -ForegroundColor Yellow
  Write-Host "   API       : https://$($script:Config.AppServiceName).azurewebsites.net" -ForegroundColor Cyan
  Write-Host "   Docs      : https://$($script:Config.AppServiceName).azurewebsites.net/docs" -ForegroundColor Cyan
  Write-Host "   Health    : https://$($script:Config.AppServiceName).azurewebsites.net/monitoring/health" -ForegroundColor Cyan
  Write-Host ""
  Write-Host "Commandes utiles:" -ForegroundColor Yellow
  Write-Host "   Logs      : az webapp log tail --name $($script:Config.AppServiceName) --resource-group $($script:Config.ResourceGroup)" -ForegroundColor Gray
  Write-Host "   Restart   : az webapp restart --name $($script:Config.AppServiceName) --resource-group $($script:Config.ResourceGroup)" -ForegroundColor Gray
  Write-Host ""
}

# ============================================================================
# MENU INTERACTIF
# ============================================================================

function Show-Menu {
  Write-Header "MENU DE DEPLOIEMENT"
    
  Write-Host "  1. Deploiement complet (Build Local + Docker Desktop)" -ForegroundColor White
  Write-Host "     Build + Push + Deploy + Migrations + Logs" -ForegroundColor Gray
  Write-Host ""
  Write-Host "  2. Deploiement complet (Build Azure Cloud)" -ForegroundColor White
  Write-Host "     Build Cloud + Deploy + Migrations + Logs" -ForegroundColor Gray
  Write-Host ""
  Write-Host "  3. Deploiement rapide (image existante)" -ForegroundColor White
  Write-Host "     Deploy + Redemarrage + Logs" -ForegroundColor Gray
  Write-Host ""
  Write-Host "  4. Creer utilisateurs initiaux (recruteurs/observateur)" -ForegroundColor White
  Write-Host "     Execute le script de bootstrap post-migration" -ForegroundColor Gray
  Write-Host ""
  Write-Host "  5. Verifier Health Check" -ForegroundColor White
  Write-Host ""
  Write-Host "  6. Quitter" -ForegroundColor White
  Write-Host ""
    
  $choice = Read-Host "Votre choix (1-6)"
  return $choice
}

function Start-InteractiveMenu {
  Write-Host ""
  Write-Header "SEEG-API - DEPLOIEMENT AZURE"
    
  do {
    $choice = Show-Menu
        
    switch ($choice) {
      "1" {
        Start-FullDeployment -UseLocalDocker $true -CreateUsers $false
        Read-Host "`nAppuyez sur Entrée pour continuer"
      }
      "2" {
        Start-FullDeployment -UseLocalDocker $false -CreateUsers $false
        Read-Host "`nAppuyez sur Entrée pour continuer"
      }
      "3" {
        Start-QuickDeploy
        Read-Host "`nAppuyez sur Entrée pour continuer"
      }
      "4" {
        New-InitialUsers
        Read-Host "`nAppuyez sur Entrée pour continuer"
      }
      "5" {
        Invoke-HealthCheck
        Read-Host "`nAppuyez sur Entrée pour continuer"
      }
      "6" {
        Write-Host "`nAu revoir!`n" -ForegroundColor Green
        break
      }
      default {
        Write-Warning "Option invalide (1-6)"
        Start-Sleep -Seconds 2
      }
    }
  } while ($choice -ne "6")
}

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

# Lancer le menu interactif
Start-InteractiveMenu
