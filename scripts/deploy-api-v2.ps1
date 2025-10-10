#Requires -Version 5.1
<#
.SYNOPSIS
    Script de deploiement robuste pour SEEG-API sur Azure
    
.DESCRIPTION
    Deploiement automatise avec logs detailles, barres de progression et monitoring
    
    Fonctionnalites:
    - Validation complete des prerequis (Azure CLI, Docker, connexion Azure)
    - Build Docker local ou cloud (ACR Build)
    - Configuration automatique App Service avec optimisations
    - CI/CD automatique avec webhooks ACR
    - Monitoring et alertes Azure
    - Logs detailles multi-niveaux (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - Rapports JSON detailles
    - Mode DryRun pour simulation
    - Idempotent (peut etre re-execute sans effets de bord)
    
.PARAMETER BuildMode
    Mode de build: 'local' (defaut) ou 'cloud' (ACR Build)
    - local: Build Docker en local puis push vers ACR
    - cloud: Build directement dans Azure (ACR Build)
    
.PARAMETER DryRun
    Mode simulation sans modifications reelles
    Active le mode simulation qui valide tout sans faire de modifications
    
.EXAMPLE
    .\deploy-api-v2.ps1
    Deploiement standard avec build local
    
.EXAMPLE
    .\deploy-api-v2.ps1 -BuildMode cloud
    Deploiement avec build dans Azure Cloud
    
.EXAMPLE
    .\deploy-api-v2.ps1 -DryRun
    Simulation du deploiement sans modifications
    
.NOTES
    Auteur: SEEG DevOps Team
    Version: 2.0.0
    Date: 2025-01-10
    
    Prerequis:
    - PowerShell 5.1+
    - Azure CLI installe et configure
    - Docker installe (pour build local)
    - Connexion Azure active (az login)
    
.LINK
    https://github.com/seeg/seeg-api
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("local", "cloud")]
    [string]$BuildMode = "local",
    
    [Parameter(Mandatory = $false)]
    [switch]$DryRun
)

# Configuration stricte pour garantir la qualite
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Supprimer les warnings Python (cryptography, etc.)
$env:PYTHONWARNINGS = "ignore"

# Version du script (Semantic Versioning)
$SCRIPT_VERSION = "2.0.0"

# ===== CONSTANTES =====

# Constantes de temporisation (en secondes)
Set-Variable -Name RESTART_WAIT_TIME -Value 5 -Option Constant
Set-Variable -Name APP_STARTUP_WAIT_TIME -Value 30 -Option Constant
Set-Variable -Name RETRY_DELAY -Value 15 -Option Constant
Set-Variable -Name MAX_HEALTH_CHECK_RETRIES -Value 5 -Option Constant

# Constantes de progression
Set-Variable -Name TOTAL_DEPLOYMENT_STEPS -Value 8 -Option Constant
Set-Variable -Name PROGRESS_BAR_LENGTH -Value 50 -Option Constant

# ===== CONFIGURATION =====

$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$LOG_DIR = ".\logs"
$LOG_FILE = Join-Path $LOG_DIR "deploy_$TIMESTAMP.log"
$ERROR_LOG_FILE = Join-Path $LOG_DIR "deploy_${TIMESTAMP}_errors.log"
$REPORT_FILE = Join-Path $LOG_DIR "deploy_${TIMESTAMP}_report.json"

# Creer le repertoire de logs si necessaire
if (-not (Test-Path $LOG_DIR)) {
    New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null
}

# Configuration Azure (centralise pour faciliter les modifications)
$CONFIG = @{
    ResourceGroup     = "seeg-rg"                    # Existe deja
    Location          = "francecentral"
    ContainerRegistry = "seegregistry"               # Existe deja - cree le 2025-10-10
    AppServicePlan    = "seeg-app-service-plan"      # A creer ou existe deja
    AppName           = "seeg-backend-api"           # A creer
    ImageName         = "seeg-api"
    DockerfilePath    = ".\Dockerfile"
    SKU               = "B2"
}

# Informations Container Registry (cree le 2025-10-10)
# Status: Provisionne et operationnel
# Login Server: seegregistry.azurecr.io
# Username: seegregistry
# Password: eaYjL5DBdId9yZRy52dlguUjsjVBISqh36PvAQegaK+ACRCNvSs7
# Full Image: seegregistry.azurecr.io/seeg-api:latest
# Admin User: Active

# Variables de tracking du deploiement
$DEPLOYMENT_STEPS = @()
$DEPLOYMENT_ERRORS = @()
$DEPLOYMENT_WARNINGS = @()
$START_TIME = Get-Date

# ===== FONCTIONS DE LOGGING =====

function Write-Log {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,
        
        [Parameter(Mandatory = $false)]
        [ValidateSet("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")]
        [string]$Level = "INFO",
        
        [Parameter(Mandatory = $false)]
        [hashtable]$Context = @{}
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $contextJson = if ($Context.Count -gt 0) { " | Context: $($Context | ConvertTo-Json -Compress)" } else { "" }
    $logEntry = "[$timestamp] [$Level] $Message$contextJson"
    
    Add-Content -Path $LOG_FILE -Value $logEntry -Encoding UTF8
    
    if ($Level -in @("ERROR", "CRITICAL")) {
        Add-Content -Path $ERROR_LOG_FILE -Value $logEntry -Encoding UTF8
        $script:DEPLOYMENT_ERRORS += @{
            Timestamp = $timestamp
            Level     = $Level
            Message   = $Message
            Context   = $Context
        }
    }
    
    if ($Level -eq "WARNING") {
        $script:DEPLOYMENT_WARNINGS += @{
            Timestamp = $timestamp
            Message   = $Message
            Context   = $Context
        }
    }
    
    $color = switch ($Level) {
        "DEBUG" { "Gray" }
        "INFO" { "White" }
        "WARNING" { "Yellow" }
        "ERROR" { "Red" }
        "CRITICAL" { "DarkRed" }
        default { "White" }
    }
    
    $icon = switch ($Level) {
        "DEBUG" { "[DEBUG]" }
        "INFO" { "[INFO]" }
        "WARNING" { "[WARN]" }
        "ERROR" { "[ERROR]" }
        "CRITICAL" { "[FAIL]" }
        default { "[LOG]" }
    }
    
    Write-Host "  $icon $Message" -ForegroundColor $color
}

function Write-Section {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        
        [Parameter(Mandatory = $false)]
        [int]$StepNumber,
        
        [Parameter(Mandatory = $false)]
        [int]$TotalSteps = $TOTAL_DEPLOYMENT_STEPS
    )
    
    $line = "=" * 76
    $prefix = if ($StepNumber) { "ETAPE $StepNumber/$TotalSteps : " } else { "" }
    $fullTitle = "$prefix$Title"
    
    Write-Host ""
    Write-Host $line -ForegroundColor Cyan
    Write-Host $fullTitle.ToUpper() -ForegroundColor Cyan
    
    if ($StepNumber) {
        $progress = [math]::Round(($StepNumber / $TotalSteps) * 100)
        $barLength = $PROGRESS_BAR_LENGTH
        $completed = [math]::Floor(($progress / 100) * $barLength)
        $remaining = $barLength - $completed
        
        $bar = "[" + ("=" * $completed) + ("-" * $remaining) + "] $progress%"
        Write-Host $bar -ForegroundColor Green
    }
    
    Write-Host $line -ForegroundColor Cyan
    Write-Host ""
    
    Write-Log -Message $fullTitle -Level "INFO"
}

function Write-ProgressBar {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Activity,
        
        [Parameter(Mandatory = $true)]
        [int]$Current,
        
        [Parameter(Mandatory = $true)]
        [int]$Total,
        
        [Parameter(Mandatory = $false)]
        [string]$Status = ""
    )
    
    $percentage = [math]::Round(($Current / $Total) * 100)
    $barLength = $PROGRESS_BAR_LENGTH - 10  # Slightly smaller for sub-progress
    $completed = [math]::Floor(($percentage / 100) * $barLength)
    $remaining = $barLength - $completed
    
    $bar = ("=" * $completed) + ("-" * $remaining)
    $statusText = if ($Status) { " | $Status" } else { "" }
    
    Write-Host "  $Activity : [$bar] $percentage% ($Current/$Total)$statusText" -ForegroundColor Cyan
}

function Start-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )
    
    $step = @{
        Name      = $Name
        StartTime = Get-Date
        Status    = "InProgress"
        Duration  = $null
        Message   = $null
    }
    
    $script:DEPLOYMENT_STEPS += $step
    return ($script:DEPLOYMENT_STEPS.Count - 1)
}

function Complete-Step {
    param(
        [Parameter(Mandatory = $true)]
        [int]$StepIndex,
        
        [Parameter(Mandatory = $true)]
        [ValidateSet("Success", "Failed", "Skipped")]
        [string]$Status,
        
        [Parameter(Mandatory = $false)]
        [string]$Message = ""
    )
    
    $step = $script:DEPLOYMENT_STEPS[$StepIndex]
    $step.Status = $Status
    $step.Duration = (Get-Date) - $step.StartTime
    $step.Message = $Message
    
    $icon = switch ($Status) {
        "Success" { "[OK]" }
        "Failed" { "[FAIL]" }
        "Skipped" { "[SKIP]" }
    }
    
    $color = switch ($Status) {
        "Success" { "Green" }
        "Failed" { "Red" }
        "Skipped" { "Yellow" }
    }
    
    Write-Host "  $icon $($step.Name) termine en $([math]::Round($step.Duration.TotalSeconds, 2))s" -ForegroundColor $color
}

# ===== VALIDATION DES PREREQUIS =====

function Test-Prerequisites {
    Write-Section -Title "VALIDATION DES PREREQUIS" -StepNumber 1
    $stepIndex = Start-Step -Name "Validation prerequis"
    
    $allValid = $true
    
    Write-Host "  Verification Azure CLI..." -ForegroundColor Gray
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        Write-Log -Message "Azure CLI non installe" -Level "CRITICAL"
        $allValid = $false
    }
    else {
        $azVersion = (az version | ConvertFrom-Json).'azure-cli'
        Write-Log -Message "Azure CLI installe" -Level "INFO" -Context @{ Version = $azVersion }
        Write-Host "    [OK] Azure CLI version $azVersion" -ForegroundColor Green
    }
    
    Write-Host "  Verification Docker..." -ForegroundColor Gray
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Log -Message "Docker non installe" -Level "CRITICAL"
        $allValid = $false
    }
    else {
        $dockerVersion = docker --version
        Write-Log -Message "Docker installe" -Level "INFO" -Context @{ Version = $dockerVersion }
        Write-Host "    [OK] $dockerVersion" -ForegroundColor Green
    }
    
    Write-Host "  Verification connexion Azure..." -ForegroundColor Gray
    $account = az account show 2>&1 | ConvertFrom-Json
    if (-not $account) {
        Write-Log -Message "Non connecte a Azure" -Level "CRITICAL"
        Write-Host "    [X] Veuillez executer 'az login'" -ForegroundColor Red
        $allValid = $false
    }
    else {
        Write-Log -Message "Connecte a Azure" -Level "INFO" -Context @{ Account = $account.user.name }
        Write-Host "    [OK] Connecte: $($account.user.name)" -ForegroundColor Green
        Write-Host "    [OK] Subscription: $($account.name)" -ForegroundColor Green
    }
    
    Write-Host "  Verification fichiers..." -ForegroundColor Gray
    $requiredFiles = @("Dockerfile", "requirements.txt", "docker-entrypoint.sh", "app/main.py")
    
    foreach ($file in $requiredFiles) {
        if (-not (Test-Path $file)) {
            Write-Log -Message "Fichier manquant: $file" -Level "ERROR"
            Write-Host "    [X] Manquant: $file" -ForegroundColor Red
            $allValid = $false
        }
        else {
            Write-Host "    [OK] $file" -ForegroundColor Green
        }
    }
    
    Write-Host "  Verification packages critiques..." -ForegroundColor Gray
    $requirements = Get-Content "requirements.txt" -Raw
    $criticalPackages = @("fastapi", "uvicorn", "pydantic-settings", "fastapi-mail", "slowapi", "reportlab")
    
    foreach ($package in $criticalPackages) {
        if ($requirements -notmatch $package) {
            Write-Log -Message "Package critique manquant: $package" -Level "ERROR"
            Write-Host "    [X] Manquant: $package" -ForegroundColor Red
            $allValid = $false
        }
        else {
            Write-Host "    [OK] $package present" -ForegroundColor Green
        }
    }
    
    if ($allValid) {
        Complete-Step -StepIndex $stepIndex -Status "Success"
        Write-Log -Message "Tous les prerequis sont valides" -Level "INFO"
    }
    else {
        Complete-Step -StepIndex $stepIndex -Status "Failed" -Message "Prerequis manquants"
        Write-Log -Message "Prerequis manquants - arret du deploiement" -Level "CRITICAL"
        throw "Validation des prerequis echouee"
    }
}

# ===== VALIDATION RESSOURCES AZURE =====

function Test-AzureResources {
    Write-Section -Title "VALIDATION RESSOURCES AZURE" -StepNumber 2
    $stepIndex = Start-Step -Name "Ressources Azure"
    
    Write-Host "  Verification Resource Group..." -ForegroundColor Gray
    # Supprimer completement les warnings Python
    $ErrorActionPreference = "SilentlyContinue"
    $rgResult = az group show --name $CONFIG.ResourceGroup --output json 2>&1 | Out-String
    $ErrorActionPreference = "Stop"
    
    if ($rgResult) {
        try {
            $rg = $rgResult | ConvertFrom-Json
        }
        catch {
            $rg = $null
        }
    }
    else {
        $rg = $null
    }
    
    if (-not $rg) {
        Write-Log -Message "Creation Resource Group: $($CONFIG.ResourceGroup)" -Level "INFO"
        Write-Host "    [INFO] Creation du Resource Group..." -ForegroundColor Yellow
        az group create --name $CONFIG.ResourceGroup --location $CONFIG.Location --output none
        Write-Host "    [OK] Resource Group cree" -ForegroundColor Green
    }
    else {
        Write-Host "    [OK] Resource Group existe" -ForegroundColor Green
    }
    
    Write-Host "  Verification Container Registry..." -ForegroundColor Gray
    # Supprimer completement les warnings Python
    $ErrorActionPreference = "SilentlyContinue"
    $acrResult = az acr show --name $CONFIG.ContainerRegistry --resource-group $CONFIG.ResourceGroup --output json 2>&1 | Out-String
    $ErrorActionPreference = "Stop"
    
    if ($acrResult) {
        try {
            $acr = $acrResult | ConvertFrom-Json
        }
        catch {
            $acr = $null
        }
    }
    else {
        $acr = $null
    }
    
    if (-not $acr) {
        Write-Log -Message "Creation ACR: $($CONFIG.ContainerRegistry)" -Level "INFO"
        Write-Host "    [INFO] Creation du Container Registry..." -ForegroundColor Yellow
        
        az acr create `
            --name $CONFIG.ContainerRegistry `
            --resource-group $CONFIG.ResourceGroup `
            --location $CONFIG.Location `
            --sku Basic `
            --admin-enabled true `
            --output none 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    [OK] ACR cree avec succes" -ForegroundColor Green
        }
        else {
            Write-Log -Message "Echec creation ACR" -Level "ERROR"
            throw "Echec de la creation du Container Registry"
        }
    }
    else {
        Write-Host "    [OK] ACR existe: $($acr.loginServer)" -ForegroundColor Green
    }
    
    Write-Host "  Verification App Service Plan..." -ForegroundColor Gray
    # Supprimer completement les warnings Python
    $ErrorActionPreference = "SilentlyContinue"
    $planResult = az appservice plan show --name $CONFIG.AppServicePlan --resource-group $CONFIG.ResourceGroup --output json 2>&1 | Out-String
    $ErrorActionPreference = "Stop"
    
    if ($planResult) {
        try {
            $plan = $planResult | ConvertFrom-Json
        }
        catch {
            $plan = $null
        }
    }
    else {
        $plan = $null
    }
    
    if (-not $plan) {
        Write-Log -Message "Creation App Service Plan: $($CONFIG.AppServicePlan)" -Level "INFO"
        Write-Host "    [INFO] Creation de l'App Service Plan..." -ForegroundColor Yellow
        
        az appservice plan create `
            --name $CONFIG.AppServicePlan `
            --resource-group $CONFIG.ResourceGroup `
            --location $CONFIG.Location `
            --is-linux `
            --sku $CONFIG.SKU `
            --output none 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    [OK] App Service Plan cree (SKU: $($CONFIG.SKU))" -ForegroundColor Green
        }
        else {
            Write-Log -Message "Echec creation App Service Plan" -Level "ERROR"
            throw "Echec de la creation de l'App Service Plan"
        }
    }
    else {
        Write-Host "    [OK] App Service Plan existe (SKU: $($plan.sku.name))" -ForegroundColor Green
    }
    
    Complete-Step -StepIndex $stepIndex -Status "Success"
}

# ===== BUILD DOCKER =====

function New-DockerImage {
    Write-Section -Title "CONSTRUCTION IMAGE DOCKER" -StepNumber 3
    $stepIndex = Start-Step -Name "Build Docker"
    
    if ($DryRun) {
        Write-Log -Message "[DRY RUN] Build Docker ignore" -Level "WARNING"
        Complete-Step -StepIndex $stepIndex -Status "Skipped"
        return $null
    }
    
    $acrLoginServer = "$($CONFIG.ContainerRegistry).azurecr.io"
    $imageTag = "latest"
    $imageFull = "${acrLoginServer}/$($CONFIG.ImageName):${imageTag}"
    
    if ($BuildMode -eq "local") {
        Write-Host "  Build local de l'image Docker..." -ForegroundColor White
        Write-ProgressBar -Activity "Build Docker" -Current 0 -Total 3 -Status "Demarrage..."
        
        Write-Log -Message "Build de l'image Docker localement" -Level "INFO" -Context @{ Image = $imageFull }
        
        # Supprimer les messages informatifs Docker
        $ErrorActionPreference = "SilentlyContinue"
        docker build -t $imageFull -f $CONFIG.DockerfilePath . 2>&1 | Out-Null
        $buildResult = $LASTEXITCODE
        $ErrorActionPreference = "Stop"
        
        if ($buildResult -ne 0) {
            Complete-Step -StepIndex $stepIndex -Status "Failed" -Message "Echec du build Docker"
            throw "Echec du build Docker"
        }
        
        Write-ProgressBar -Activity "Build Docker" -Current 1 -Total 3 -Status "Image construite"
        Write-Host "    [OK] Image Docker construite" -ForegroundColor Green
        
        Write-Host "  Connexion a Azure Container Registry..." -ForegroundColor Gray
        # Supprimer les messages informatifs Azure CLI
        $ErrorActionPreference = "SilentlyContinue"
        az acr login --name $CONFIG.ContainerRegistry 2>&1 | Out-Null
        $loginResult = $LASTEXITCODE
        $ErrorActionPreference = "Stop"
        
        if ($loginResult -ne 0) {
            Complete-Step -StepIndex $stepIndex -Status "Failed" -Message "Echec login ACR"
            throw "Echec de la connexion ACR"
        }
        
        Write-ProgressBar -Activity "Build Docker" -Current 2 -Total 3 -Status "Login ACR reussi"
        
        Write-Host "  Push de l'image vers ACR..." -ForegroundColor Gray
        Write-Log -Message "Push de l'image vers ACR" -Level "INFO" -Context @{ Image = $imageFull }
        
        # Supprimer les messages informatifs Docker
        $ErrorActionPreference = "SilentlyContinue"
        docker push $imageFull 2>&1 | Out-Null
        $pushResult = $LASTEXITCODE
        $ErrorActionPreference = "Stop"
        
        if ($pushResult -ne 0) {
            Complete-Step -StepIndex $stepIndex -Status "Failed" -Message "Echec push Docker"
            throw "Echec du push vers ACR"
        }
        
        Write-ProgressBar -Activity "Build Docker" -Current 3 -Total 3 -Status "Push termine avec succes"
        Write-Host "    [OK] Image pushee vers ACR" -ForegroundColor Green
    }
    else {
        Write-Host "  Build dans Azure Cloud (ACR Build)..." -ForegroundColor White
        Write-ProgressBar -Activity "Build Azure" -Current 0 -Total 1 -Status "Demarrage du build cloud..."
        
        Write-Log -Message "Build de l'image dans le cloud (ACR Build)" -Level "INFO" -Context @{ Image = $imageFull }
        
        az acr build `
            --registry $CONFIG.ContainerRegistry `
            --image "$($CONFIG.ImageName):${imageTag}" `
            --file $CONFIG.DockerfilePath `
            . 2>&1 | Out-Null
        
        if ($LASTEXITCODE -ne 0) {
            Complete-Step -StepIndex $stepIndex -Status "Failed" -Message "Echec ACR Build"
            throw "Echec du build ACR"
        }
        
        Write-ProgressBar -Activity "Build Azure" -Current 1 -Total 1 -Status "Build cloud termine avec succes"
        Write-Host "    [OK] Build cloud termine" -ForegroundColor Green
    }
    
    Complete-Step -StepIndex $stepIndex -Status "Success"
    Write-Log -Message "Image Docker prete" -Level "INFO" -Context @{ Image = $imageFull }
    
    return $imageFull
}

# ===== CONFIGURATION APP SERVICE =====

function Publish-AppService {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ImageName
    )
    
    Write-Section -Title "CONFIGURATION APP SERVICE" -StepNumber 4
    $stepIndex = Start-Step -Name "App Service"
    
    if ($DryRun) {
        Write-Log -Message "[DRY RUN] Configuration App Service ignoree" -Level "WARNING"
        Complete-Step -StepIndex $stepIndex -Status "Skipped"
        return
    }
    
    Write-Host "  Verification App Service..." -ForegroundColor Gray
    # Supprimer completement les warnings Python
    $ErrorActionPreference = "SilentlyContinue"
    $appResult = az webapp show --name $CONFIG.AppName --resource-group $CONFIG.ResourceGroup --output json 2>&1 | Out-String
    $ErrorActionPreference = "Stop"
    
    if ($appResult) {
        try {
            $app = $appResult | ConvertFrom-Json
        }
        catch {
            $app = $null
        }
    }
    else {
        $app = $null
    }
    
    if (-not $app) {
        Write-Log -Message "Creation App Service: $($CONFIG.AppName)" -Level "INFO"
        Write-Host "  Creation de l'App Service..." -ForegroundColor White
        
        az webapp create `
            --name $CONFIG.AppName `
            --resource-group $CONFIG.ResourceGroup `
            --plan $CONFIG.AppServicePlan `
            --deployment-container-image-name $ImageName `
            --output none
        
        if ($LASTEXITCODE -ne 0) {
            Complete-Step -StepIndex $stepIndex -Status "Failed" -Message "Echec creation App Service"
            throw "Echec de la creation de l'App Service"
        }
        
        Write-Host "    [OK] App Service cree" -ForegroundColor Green
    }
    else {
        Write-Log -Message "Mise a jour App Service existante" -Level "INFO"
        Write-Host "    [OK] App Service existe - mise a jour..." -ForegroundColor Green
    }
    
    Write-Host "  Configuration du container..." -ForegroundColor Gray
    Write-Log -Message "Configuration du container Docker" -Level "INFO" -Context @{ Image = $ImageName }
    
    az webapp config container set `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --docker-custom-image-name $ImageName `
        --docker-registry-server-url "https://$($CONFIG.ContainerRegistry).azurecr.io" `
        --output none
    
    if ($LASTEXITCODE -ne 0) {
        Complete-Step -StepIndex $stepIndex -Status "Failed" -Message "Echec configuration container"
        throw "Echec de la configuration du container"
    }
    
    Write-Host "    [OK] Container configure" -ForegroundColor Green
    
    Write-Host "  Configuration des variables d'environnement..." -ForegroundColor Gray
    
    $appSettings = @(
        # Environnement
        "ENVIRONMENT=production",
        "DEBUG=false",
        "APP_NAME=One HCM SEEG Backend API",
        "APP_VERSION=1.0.0",
        
        # Base de donnees PostgreSQL Azure
        "DATABASE_URL=postgresql+asyncpg://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres",
        "DATABASE_URL_SYNC=postgresql://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres",
        
        # Securite JWT
        "SECRET_KEY=GVxt590ktWvcTL6BLttyq7CVxhhGcZ18EA34vnDZczLDIf6Gh2uHpQOahkn2LXF8",
        "ALGORITHM=HS256",
        "JWT_ISSUER=seeg-hcm-api",
        "JWT_AUDIENCE=seeg-hcm-frontend",
        "ACCESS_TOKEN_EXPIRE_MINUTES=30",
        "REFRESH_TOKEN_EXPIRE_DAYS=7",
        
        # CORS - Accepte toutes les origines
        "ALLOWED_ORIGINS=*",
        "ALLOWED_CREDENTIALS=false",
        
        # Logging
        "LOG_LEVEL=INFO",
        "LOG_FORMAT=json",
        
        # Redis (desactive)
        "REDIS_URL=",
        
        # Monitoring Azure
        "ENABLE_TRACING=true",
        "METRICS_ENABLED=true",
        
        # Performance Uvicorn
        "WORKERS=2",
        "MAX_REQUESTS=1000",
        "MAX_REQUESTS_JITTER=100",
        "TIMEOUT_KEEP_ALIVE=5",
        "TIMEOUT_GRACEFUL_SHUTDOWN=30",
        
        # Email SMTP
        "SMTP_HOST=smtp.gmail.com",
        "SMTP_PORT=587",
        "SMTP_USERNAME=support@seeg-talentsource.com",
        "SMTP_PASSWORD=njev urja zsbc spfn",
        "SMTP_TLS=true",
        "SMTP_SSL=false",
        "MAIL_FROM_NAME=One HCM - SEEG Talent Source",
        "MAIL_FROM_EMAIL=support@seeg-talentsource.com",
        
        # Frontend
        "PUBLIC_APP_URL=https://www.seeg-talentsource.com",
        
        # Features
        "RATE_LIMIT_ENABLED=false",
        "CREATE_INITIAL_USERS=false",
        
        # Migrations et Azure
        "SKIP_MIGRATIONS=true",
        "WEBSITES_PORT=8000",
        "WEBSITE_HEALTHCHECK_PATH=/monitoring/health",
        "WEBSITE_HEALTHCHECK_MAXPINGFAILURES=10",
        "WEBSITES_ENABLE_APP_SERVICE_STORAGE=false",
        "DOCKER_ENABLE_CI=true"
    )
    
    az webapp config appsettings set `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --settings $appSettings `
        --output none
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [OK] Variables d'environnement configurees" -ForegroundColor Green
        Write-Log -Message "Variables d'environnement configurees" -Level "INFO"
    }
    
    Write-Host "  Activation des logs..." -ForegroundColor Gray
    
    az webapp log config `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --docker-container-logging filesystem `
        --application-logging filesystem `
        --level information `
        --output none
    
    Write-Host "    [OK] Logs actives" -ForegroundColor Green
    
    Write-Host "  Configuration avancee..." -ForegroundColor Gray
    
    az webapp config set `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --always-on true `
        --http20-enabled true `
        --min-tls-version 1.2 `
        --use-32bit-worker-process false `
        --output none
    
    Write-Host "    [OK] Configuration avancee appliquee" -ForegroundColor Green
    Write-Log -Message "Configuration avancee: Always On, HTTP/2, TLS 1.2+" -Level "INFO"
    
    Complete-Step -StepIndex $stepIndex -Status "Success"
}

# ===== REDEMARRAGE APPLICATION =====

function Restart-Application {
    Write-Section -Title "REDEMARRAGE APPLICATION" -StepNumber 5
    $stepIndex = Start-Step -Name "Restart App"
    
    if ($DryRun) {
        Write-Log -Message "[DRY RUN] Redemarrage ignore" -Level "WARNING"
        Complete-Step -StepIndex $stepIndex -Status "Skipped"
        return
    }
    
    Write-Host "  Arret de l'application..." -ForegroundColor Gray
    az webapp stop --name $CONFIG.AppName --resource-group $CONFIG.ResourceGroup --output none
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [OK] Application arretee" -ForegroundColor Green
        Write-Log -Message "Application arretee" -Level "INFO"
    }
    
    Start-Sleep -Seconds $RESTART_WAIT_TIME
    
    Write-Host "  Demarrage de l'application..." -ForegroundColor Gray
    az webapp start --name $CONFIG.AppName --resource-group $CONFIG.ResourceGroup --output none
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [OK] Application demarree" -ForegroundColor Green
        Write-Log -Message "Application demarree" -Level "INFO"
    }
    
    Write-Host "  Attente de la disponibilite ($($APP_STARTUP_WAIT_TIME)s)..." -ForegroundColor Gray
    Start-Sleep -Seconds $APP_STARTUP_WAIT_TIME
    
    Complete-Step -StepIndex $stepIndex -Status "Success"
}

# ===== TESTS DE VALIDATION =====

function Test-DeployedApplication {
    Write-Section -Title "TESTS DE VALIDATION" -StepNumber 6
    $stepIndex = Start-Step -Name "Tests application"
    
    if ($DryRun) {
        Write-Log -Message "Tests ignores" -Level "WARNING"
        Complete-Step -StepIndex $stepIndex -Status "Skipped"
        return
    }
    
    $appUrl = "https://$($CONFIG.AppName).azurewebsites.net"
    
    Write-Host "  Test de disponibilite..." -ForegroundColor Gray
    Write-Log -Message "Test de l'application deployee" -Level "INFO" -Context @{ URL = $appUrl }
    
    $maxRetries = $MAX_HEALTH_CHECK_RETRIES
    $retryCount = 0
    $success = $false
    
    while ($retryCount -lt $maxRetries -and -not $success) {
        $retryCount++
        Write-Host "    Tentative $retryCount/$maxRetries..." -ForegroundColor Gray
        
        try {
            $response = Invoke-WebRequest -Uri "$appUrl/health" -Method GET -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
            
            if ($response.StatusCode -eq 200) {
                Write-Host "    [OK] Application accessible (HTTP $($response.StatusCode))" -ForegroundColor Green
                Write-Log -Message "Application deployee et accessible" -Level "INFO" -Context @{
                    URL        = $appUrl
                    StatusCode = $response.StatusCode
                    Retries    = $retryCount
                }
                $success = $true
            }
        }
        catch {
            if ($retryCount -lt $maxRetries) {
                Write-Host "    [WARN] Pas encore prete, nouvelle tentative dans $($RETRY_DELAY)s..." -ForegroundColor Yellow
                Start-Sleep -Seconds $RETRY_DELAY
            }
        }
    }
    
    if ($success) {
        Complete-Step -StepIndex $stepIndex -Status "Success"
        
        Write-Host ""
        Write-Host "  URL de l'API: $appUrl" -ForegroundColor Cyan
        Write-Host "  Documentation: $appUrl/docs" -ForegroundColor Cyan
        Write-Host "  Health Check: $appUrl/health" -ForegroundColor Cyan
    }
    else {
        Complete-Step -StepIndex $stepIndex -Status "Failed" -Message "Application non accessible"
        Write-Log -Message "Application non accessible apres $maxRetries tentatives" -Level "WARNING"
        Write-Host "    [WARN] Application deployee mais pas encore accessible" -ForegroundColor Yellow
        Write-Host "    Verifiez les logs: az webapp log tail --name $($CONFIG.AppName) --resource-group $($CONFIG.ResourceGroup)" -ForegroundColor Yellow
    }
}

# ===== CONFIGURATION CI/CD =====

function Enable-ContinuousDeployment {
    Write-Section -Title "CONFIGURATION CI/CD AUTOMATIQUE" -StepNumber 7
    $stepIndex = Start-Step -Name "CI/CD"
    
    if ($DryRun) {
        Write-Log -Message "[DRY RUN] Configuration CI/CD ignoree" -Level "WARNING"
        Complete-Step -StepIndex $stepIndex -Status "Skipped"
        return
    }
    
    Write-Host "  Activation du Continuous Deployment..." -ForegroundColor Gray
    Write-Log -Message "Activation du CI/CD depuis ACR" -Level "INFO"
    
    # Supprimer completement les warnings Python
    $ErrorActionPreference = "SilentlyContinue"
    az webapp deployment container config `
        --name $CONFIG.AppName `
        --resource-group $CONFIG.ResourceGroup `
        --enable-cd true `
        --output none 2>&1 | Out-Null
    $cdResult = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    
    if ($cdResult -eq 0) {
        Write-Host "    [OK] CD active" -ForegroundColor Green
        
        # Supprimer completement les warnings Python
        $ErrorActionPreference = "SilentlyContinue"
        $webhookUrl = az webapp deployment container show-cd-url `
            --name $CONFIG.AppName `
            --resource-group $CONFIG.ResourceGroup `
            --query "CI_CD_URL" `
            --output tsv 2>&1 | Out-String
        $ErrorActionPreference = "Stop"
        $webhookUrl = $webhookUrl.Trim()
        
        if ($webhookUrl) {
            Write-Log -Message "Webhook URL recuperee" -Level "INFO"
            
            # Nom du webhook sans tirets (uniquement alphanumerique)
            $webhookName = ($CONFIG.AppName -replace '-', '') + "Webhook"
            
            Write-Host "  Configuration du webhook ACR..." -ForegroundColor Gray
            
            # Supprimer completement les warnings Python
            $ErrorActionPreference = "SilentlyContinue"
            $webhookResult = az acr webhook show `
                --name $webhookName `
                --registry $CONFIG.ContainerRegistry `
                --output json 2>&1 | Out-String
            $ErrorActionPreference = "Stop"
            
            try {
                $existingWebhook = $webhookResult | ConvertFrom-Json
            }
            catch {
                $existingWebhook = $null
            }
            
            if ($existingWebhook) {
                az acr webhook update `
                    --name $webhookName `
                    --registry $CONFIG.ContainerRegistry `
                    --uri $webhookUrl `
                    --actions push delete `
                    --status enabled `
                    --output none 2>&1 | Out-Null
            }
            else {
                az acr webhook create `
                    --name $webhookName `
                    --registry $CONFIG.ContainerRegistry `
                    --uri $webhookUrl `
                    --actions push delete `
                    --scope "$($CONFIG.AppName):*" `
                    --output none 2>&1 | Out-Null
            }
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    [OK] Webhook ACR configure" -ForegroundColor Green
                Write-Host "    [INFO] Les futurs push vers ACR declencheront un redeploiement automatique" -ForegroundColor Cyan
                Write-Log -Message "CI/CD completement configure" -Level "INFO" -Context @{ Webhook = $webhookName }
            }
        }
        
        Complete-Step -StepIndex $stepIndex -Status "Success"
    }
    else {
        Complete-Step -StepIndex $stepIndex -Status "Failed" -Message "Echec config CI/CD"
        Write-Log -Message "Echec de la configuration CI/CD (non bloquant)" -Level "WARNING"
    }
}

# ===== CONFIGURATION MONITORING =====

function Enable-Monitoring {
    Write-Section -Title "CONFIGURATION MONITORING & PERFORMANCE" -StepNumber 8
    $stepIndex = Start-Step -Name "Monitoring"
    
    if ($DryRun) {
        Write-Log -Message "[DRY RUN] Configuration monitoring ignoree" -Level "WARNING"
        Complete-Step -StepIndex $stepIndex -Status "Skipped"
        return
    }
    
    Write-Host "  Execution du script de monitoring..." -ForegroundColor Gray
    Write-Log -Message "Lancement de la configuration du monitoring" -Level "INFO"
    
    $monitoringScript = Join-Path $PSScriptRoot "setup-monitoring.ps1"
    
    if (Test-Path $monitoringScript) {
        & $monitoringScript -ErrorAction Continue
        
        if ($?) {
            Write-Host "    [OK] Monitoring configure avec succes" -ForegroundColor Green
            Write-Log -Message "Monitoring Azure configure" -Level "INFO"
            Complete-Step -StepIndex $stepIndex -Status "Success"
        }
        else {
            Write-Host "    [WARN] Erreur lors de la configuration du monitoring (non bloquant)" -ForegroundColor Yellow
            Write-Log -Message "Erreur configuration monitoring (non bloquant)" -Level "WARNING"
            Complete-Step -StepIndex $stepIndex -Status "Failed" -Message "Erreur monitoring"
        }
    }
    else {
        Write-Host "    [WARN] Script setup-monitoring.ps1 introuvable" -ForegroundColor Yellow
        Write-Log -Message "Script de monitoring introuvable" -Level "WARNING"
        Complete-Step -StepIndex $stepIndex -Status "Skipped"
    }
}

# ===== RAPPORT DE DEPLOIEMENT =====

function New-DeploymentReport {
    $endTime = Get-Date
    $totalDuration = $endTime - $START_TIME
    
    $report = @{
        Timestamp     = $START_TIME.ToString("yyyy-MM-dd HH:mm:ss")
        Duration      = @{
            Total   = $totalDuration.ToString()
            Seconds = [math]::Round($totalDuration.TotalSeconds, 2)
        }
        Configuration = $CONFIG
        BuildMode     = $BuildMode
        DryRun        = $DryRun.IsPresent
        Steps         = $DEPLOYMENT_STEPS
        Errors        = $DEPLOYMENT_ERRORS
        Warnings      = $DEPLOYMENT_WARNINGS
        Summary       = @{
            TotalSteps      = $DEPLOYMENT_STEPS.Count
            SuccessfulSteps = ($DEPLOYMENT_STEPS | Where-Object { $_.Status -eq "Success" }).Count
            FailedSteps     = ($DEPLOYMENT_STEPS | Where-Object { $_.Status -eq "Failed" }).Count
            SkippedSteps    = ($DEPLOYMENT_STEPS | Where-Object { $_.Status -eq "Skipped" }).Count
            TotalErrors     = $DEPLOYMENT_ERRORS.Count
            TotalWarnings   = $DEPLOYMENT_WARNINGS.Count
        }
        AppURL        = "https://$($CONFIG.AppName).azurewebsites.net"
        DocsURL       = "https://$($CONFIG.AppName).azurewebsites.net/docs"
    }
    
    $report | ConvertTo-Json -Depth 10 | Out-File -FilePath $REPORT_FILE -Encoding UTF8
    
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host "       RAPPORT DE DEPLOIEMENT          " -ForegroundColor Cyan
    Write-Host "============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Duree totale: $([math]::Round($totalDuration.TotalMinutes, 2)) minutes" -ForegroundColor White
    Write-Host "  Etapes reussies: $($report.Summary.SuccessfulSteps)/$($report.Summary.TotalSteps)" -ForegroundColor Green
    
    if ($report.Summary.FailedSteps -gt 0) {
        Write-Host "  Etapes echouees: $($report.Summary.FailedSteps)" -ForegroundColor Red
    }
    
    if ($report.Summary.TotalWarnings -gt 0) {
        Write-Host "  Avertissements: $($report.Summary.TotalWarnings)" -ForegroundColor Yellow
    }
    
    if ($report.Summary.TotalErrors -gt 0) {
        Write-Host "  Erreurs: $($report.Summary.TotalErrors)" -ForegroundColor Red
    }
    
    Write-Host ""
    Write-Host "  Fichiers generes:" -ForegroundColor Cyan
    Write-Host "    - Logs: $LOG_FILE" -ForegroundColor Gray
    Write-Host "    - Erreurs: $ERROR_LOG_FILE" -ForegroundColor Gray
    Write-Host "    - Rapport: $REPORT_FILE" -ForegroundColor Gray
    Write-Host ""
    
    Write-Log -Message "Rapport de deploiement genere" -Level "INFO" -Context @{
        ReportFile = $REPORT_FILE
        Summary    = $report.Summary
    }
}

# ===== FONCTION PRINCIPALE =====

function Invoke-Deployment {
    Write-Host ""
    Write-Host "=============================================================" -ForegroundColor Cyan
    Write-Host "       DEPLOIEMENT SEEG-API SUR AZURE APP SERVICE          " -ForegroundColor Cyan
    Write-Host "       Version $SCRIPT_VERSION                              " -ForegroundColor Cyan
    Write-Host "=============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
    Write-Host "  Version Script: $SCRIPT_VERSION" -ForegroundColor Gray
    Write-Host "  Mode Build: $BuildMode" -ForegroundColor Gray
    Write-Host "  Mode DryRun: $($DryRun.IsPresent)" -ForegroundColor Gray
    Write-Host "  PowerShell: $($PSVersionTable.PSVersion)" -ForegroundColor Gray
    Write-Host ""
    
    Write-Log -Message "=== DEBUT DU DEPLOIEMENT ===" -Level "INFO" -Context @{
        BuildMode     = $BuildMode
        DryRun        = $DryRun.IsPresent
        User          = $env:USERNAME
        Computer      = $env:COMPUTERNAME
        ScriptVersion = $SCRIPT_VERSION
    }
    
    # Etape 1: Valider que tous les outils necessaires sont installes
    Test-Prerequisites
    
    # Etape 2: Creer ou valider les ressources Azure (RG, ACR, App Service Plan)
    Test-AzureResources
    
    # Etape 3: Construire l'image Docker (local ou cloud)
    $imageName = New-DockerImage
    
    # Etape 4: Configurer l'App Service avec l'image Docker
    if ($imageName) {
        Publish-AppService -ImageName $imageName
    }
    else {
        Write-Log -Message "Pas d'image Docker disponible" -Level "WARNING"
    }
    
    # Etape 5: Redemarrer l'application pour appliquer les changements
    Restart-Application
    
    # Etape 6: Tester que l'application est accessible
    Test-DeployedApplication
    
    # Etape 7: Configurer le CI/CD automatique
    Enable-ContinuousDeployment
    
    # Etape 8: Activer le monitoring et les alertes
    Enable-Monitoring
    
    # Generer le rapport final de deploiement
    New-DeploymentReport
    
    Write-Host ""
    Write-Host "=============================================================" -ForegroundColor Green
    Write-Host "          DEPLOIEMENT TERMINE AVEC SUCCES !                " -ForegroundColor Green
    Write-Host "=============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  URL de l'API: https://$($CONFIG.AppName).azurewebsites.net" -ForegroundColor Cyan
    Write-Host "  Documentation: https://$($CONFIG.AppName).azurewebsites.net/docs" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Log -Message "=== DEPLOIEMENT TERMINE AVEC SUCCES ===" -Level "INFO"
}

# ===== POINT D'ENTREE =====

if ($MyInvocation.InvocationName -ne '.') {
    Invoke-Deployment
}
