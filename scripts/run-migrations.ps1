# ============================================================================
# Script d'Execution des Migrations de Base de Donnees
# ============================================================================
# Ce script execute les migrations Alembic sur la base de donnees Azure
# Il peut etre execute independamment du deploiement de l'API
# ============================================================================

param(
    [Parameter(Mandatory = $false)]
    [string]$ResourceGroup = "seeg-rg",
    
    [Parameter(Mandatory = $false)]
    [string]$AppName = "seeg-backend-api",
    
    [Parameter(Mandatory = $false)]
    [string]$PostgresServer = "seeg-postgres-server",
    
    [Parameter(Mandatory = $false)]
    [ValidateSet("upgrade", "downgrade", "current", "history")]
    [string]$Action = "upgrade",
    
    [Parameter(Mandatory = $false)]
    [string]$Target = "head"
)

# Configuration
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=" -NoNewline -ForegroundColor Cyan
    Write-Host ("=" * 78) -ForegroundColor Cyan
    Write-Host " $Title" -ForegroundColor Cyan
    Write-Host "=" -NoNewline -ForegroundColor Cyan
    Write-Host ("=" * 78) -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "[ETAPE] " -NoNewline -ForegroundColor Green
    Write-Host $Message
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] " -NoNewline -ForegroundColor Cyan
    Write-Host $Message
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] " -NoNewline -ForegroundColor Green
    Write-Host $Message
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "[ERREUR] " -NoNewline -ForegroundColor Red
    Write-Host $Message
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "[ATTENTION] " -NoNewline -ForegroundColor Yellow
    Write-Host $Message
}

# ============================================================================
# VERIFICATION DES PRE-REQUIS
# ============================================================================

function Test-Prerequisites {
    Write-Step "Verification des pre-requis..."
    
    # Verifier Azure CLI
    try {
        $azVersion = az version --output json | ConvertFrom-Json
        Write-Info "Azure CLI version: $($azVersion.'azure-cli')"
    }
    catch {
        Write-Error-Custom "Azure CLI n'est pas installe ou n'est pas dans le PATH"
        exit 1
    }
    
    # Verifier la connexion Azure
    $account = az account show 2>$null | ConvertFrom-Json
    if (-not $account) {
        Write-Error-Custom "Vous n'etes pas connecte a Azure. Executez: az login"
        exit 1
    }
    Write-Info "Connecte a Azure: $($account.user.name)"
    
    # Verifier Python
    try {
        $pythonVersion = python --version
        Write-Info "Python: $pythonVersion"
    }
    catch {
        Write-Error-Custom "Python n'est pas installe ou n'est pas dans le PATH"
        exit 1
    }
    
    # Verifier Alembic
    try {
        alembic --version | Out-Null
        Write-Info "Alembic est disponible"
    }
    catch {
        Write-Error-Custom "Alembic n'est pas installe. Executez: pip install alembic"
        exit 1
    }
    
    # Verifier que le repertoire est bien la racine du projet
    if (-not (Test-Path "app/main.py")) {
        Write-Error-Custom "Ce script doit etre execute depuis la racine du projet"
        exit 1
    }
    
    if (-not (Test-Path "alembic.ini")) {
        Write-Error-Custom "Le fichier alembic.ini est introuvable"
        exit 1
    }
    
    Write-Success "Tous les pre-requis sont satisfaits"
}

# ============================================================================
# RECUPERATION DE LA CHAINE DE CONNEXION
# ============================================================================

function Get-DatabaseConnectionString {
    Write-Step "Recuperation de la chaine de connexion..."
    
    # Recuperer la configuration de la base de donnees depuis l'App Service
    $appSettings = az webapp config appsettings list `
        --name $AppName `
        --resource-group $ResourceGroup `
        --output json | ConvertFrom-Json
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Impossible de recuperer les parametres de l'App Service"
        exit 1
    }
    
    # Chercher DATABASE_URL
    $databaseUrl = ($appSettings | Where-Object { $_.name -eq "DATABASE_URL" }).value
    
    if (-not $databaseUrl) {
        Write-Error-Custom "La variable DATABASE_URL n'est pas configuree dans l'App Service"
        exit 1
    }
    
    Write-Success "Chaine de connexion recuperee"
    return $databaseUrl
}

# ============================================================================
# AUTORISATION FIREWALL
# ============================================================================

function Add-FirewallRule {
    Write-Step "Verification de l'acces au serveur PostgreSQL..."
    
    # Recuperer l'IP publique
    try {
        $myIp = (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing).Content
        Write-Info "Votre IP publique: $myIp"
    }
    catch {
        Write-Warning-Custom "Impossible de recuperer l'IP publique"
        return
    }
    
    # Verifier si une regle existe deja pour cette IP
    $ruleName = "migration-script-$($myIp -replace '\.','-')"
    
    # Lister toutes les regles et verifier si la notre existe
    try {
        $existingRules = az postgres flexible-server firewall-rule list `
            --resource-group $ResourceGroup `
            --name $PostgresServer `
            --output json 2>$null | ConvertFrom-Json
        
        $ruleExists = $existingRules | Where-Object { $_.name -eq $ruleName }
        
        if ($ruleExists) {
            Write-Info "Regle de firewall deja existante"
            return $ruleName
        }
    }
    catch {
        # Si on ne peut pas lister les regles, on continue pour essayer de creer
        Write-Info "Impossible de verifier les regles existantes, tentative de creation..."
    }
    
    # Creer une regle temporaire
    Write-Step "Ajout de votre IP au firewall PostgreSQL..."
    
    az postgres flexible-server firewall-rule create `
        --resource-group $ResourceGroup `
        --name $PostgresServer `
        --rule-name $ruleName `
        --start-ip-address $myIp `
        --end-ip-address $myIp `
        --output none
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Regle de firewall ajoutee: $ruleName"
        return $ruleName
    }
    else {
        Write-Warning-Custom "Impossible d'ajouter la regle de firewall"
        return $null
    }
}

# ============================================================================
# EXECUTION DES MIGRATIONS
# ============================================================================

function Invoke-Migration {
    param(
        [string]$DatabaseUrl,
        [string]$Action,
        [string]$Target
    )
    
    Write-Section "EXECUTION DES MIGRATIONS"
    
    Write-Info "Action: $Action"
    Write-Info "Target: $Target"
    
    # Configurer la variable d'environnement
    $env:DATABASE_URL = $DatabaseUrl
    
    try {
        switch ($Action) {
            "upgrade" {
                Write-Step "Application des migrations ($Target)..."
                alembic upgrade $Target
            }
            "downgrade" {
                Write-Step "Retour en arriere des migrations ($Target)..."
                alembic downgrade $Target
            }
            "current" {
                Write-Step "Affichage de la version actuelle..."
                alembic current
            }
            "history" {
                Write-Step "Affichage de l'historique des migrations..."
                alembic history --verbose
            }
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Operation '$Action' executee avec succes"
            return $true
        }
        else {
            Write-Error-Custom "Echec de l'operation '$Action'"
            return $false
        }
    }
    catch {
        Write-Error-Custom "Erreur lors de l'execution: $($_.Exception.Message)"
        return $false
    }
    finally {
        # Nettoyer la variable d'environnement
        Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    }
}

# ============================================================================
# VERIFICATION DE L'ETAT DES MIGRATIONS
# ============================================================================

function Test-MigrationStatus {
    param([string]$DatabaseUrl)
    
    Write-Section "VERIFICATION DE L'ETAT DES MIGRATIONS"
    
    $env:DATABASE_URL = $DatabaseUrl
    
    try {
        Write-Step "Version actuelle de la base de donnees..."
        alembic current -v
        
        Write-Host ""
        Write-Step "Migrations en attente..."
        alembic upgrade head --sql > $null 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Aucune migration en attente"
        }
        else {
            Write-Warning-Custom "Des migrations sont en attente"
        }
    }
    catch {
        Write-Warning-Custom "Impossible de verifier l'etat: $($_.Exception.Message)"
    }
    finally {
        Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
    }
}

# ============================================================================
# NETTOYAGE
# ============================================================================

function Remove-FirewallRule {
    param([string]$RuleName)
    
    if (-not $RuleName) {
        return
    }
    
    Write-Step "Suppression de la regle de firewall temporaire..."
    
    az postgres flexible-server firewall-rule delete `
        --resource-group $ResourceGroup `
        --name $PostgresServer `
        --rule-name $RuleName `
        --yes `
        --output none `
        2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Regle de firewall supprimee"
    }
}

# ============================================================================
# SCRIPT PRINCIPAL
# ============================================================================

function Main {
    Write-Section "EXECUTION DES MIGRATIONS DE BASE DE DONNEES"
    
    Write-Info "Resource Group: $ResourceGroup"
    Write-Info "App Service: $AppName"
    Write-Info "PostgreSQL Server: $PostgresServer"
    
    # 1. Verification des pre-requis
    Test-Prerequisites
    
    # 2. Recuperation de la chaine de connexion
    $databaseUrl = Get-DatabaseConnectionString
    
    # 3. Autorisation firewall
    $firewallRule = Add-FirewallRule
    
    # 4. Verification de l'etat actuel (seulement pour upgrade)
    if ($Action -eq "upgrade") {
        Test-MigrationStatus -DatabaseUrl $databaseUrl
    }
    
    # 5. Execution de l'action demandee
    $success = Invoke-Migration -DatabaseUrl $databaseUrl -Action $Action -Target $Target
    
    # 6. Nettoyage
    if ($firewallRule) {
        $cleanup = Read-Host "Voulez-vous supprimer la regle de firewall temporaire? (O/n)"
        if ($cleanup -ne "n" -and $cleanup -ne "N") {
            Remove-FirewallRule -RuleName $firewallRule
        }
        else {
            Write-Info "Regle de firewall conservee: $firewallRule"
        }
    }
    
    # Resume final
    Write-Section "RESUME"
    
    if ($success) {
        Write-Success "MIGRATIONS EXECUTEES AVEC SUCCES"
        
        if ($Action -eq "upgrade") {
            Write-Host ""
            Write-Info "Les migrations ont ete appliquees a la base de donnees"
            Write-Info "L'API peut maintenant utiliser le nouveau schema"
            Write-Host ""
            Write-Warning-Custom "N'oubliez pas de redemarrer l'API si elle est en cours d'execution:"
            Write-Host "  az webapp restart --name $AppName --resource-group $ResourceGroup"
        }
    }
    else {
        Write-Error-Custom "ECHEC DES MIGRATIONS"
        Write-Info "Verifiez les logs ci-dessus pour plus de details"
        exit 1
    }
}

# Executer le script principal
try {
    Main
}
catch {
    Write-Error-Custom "Erreur fatale: $($_.Exception.Message)"
    exit 1
}
