# Script d'execution des migrations Alembic pour SEEG-API
$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  EXECUTION DES MIGRATIONS - SEEG-API" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

# Variables
$RESOURCE_GROUP = "one-hcm-seeg-rg"
$APP_SERVICE_NAME = "one-hcm-seeg-backend"

# Vérifier la connexion Azure
Write-Host "Vérification de la connexion Azure..." -ForegroundColor Yellow
try {
    az account show 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Non connecté"
    }
    Write-Host "✓ Connecté à Azure`n" -ForegroundColor Green
}
catch {
    Write-Host "Erreur : Vous devez être connecté à Azure CLI" -ForegroundColor Red
    Write-Host "Exécutez : az login" -ForegroundColor Yellow
    exit 1
}

# Demander confirmation
Write-Host "Cette opération va exécuter les migrations Alembic sur la base de données de production." -ForegroundColor Yellow
Write-Host "Voulez-vous continuer? (y/n)" -ForegroundColor Yellow
$confirm = Read-Host
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "Migration annulée" -ForegroundColor Yellow
    exit 0
}

Write-Host "`nExécution des migrations Alembic..." -ForegroundColor Cyan

# Option 1 : Exécution locale (recommandé si DATABASE_URL est configuré localement)
try {
    # Vérifier si alembic est disponible
    $alembicPath = Get-Command alembic -ErrorAction SilentlyContinue
    
    if ($alembicPath) {
        Write-Host "Exécution des migrations en local..." -ForegroundColor Cyan
        alembic upgrade head
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n✓ Migrations exécutées avec succès !" -ForegroundColor Green
            exit 0
        }
        else {
            throw "Erreur lors de l'exécution des migrations"
        }
    }
    else {
        Write-Host "Alembic n'est pas installé localement." -ForegroundColor Yellow
        Write-Host "Tentative d'exécution via Azure Web App SSH..." -ForegroundColor Yellow
        
        # Option 2 : Exécution via SSH Azure (si disponible)
        Write-Host "`nConnexion SSH à l'App Service..." -ForegroundColor Cyan
        az webapp ssh --name $APP_SERVICE_NAME --resource-group $RESOURCE_GROUP --command "cd /app && alembic upgrade head"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n✓ Migrations exécutées avec succès via SSH !" -ForegroundColor Green
        }
        else {
            Write-Host "`nErreur lors de l'exécution via SSH" -ForegroundColor Red
            Write-Host "Vous pouvez exécuter manuellement :" -ForegroundColor Yellow
            Write-Host "  1. Activer l'environnement virtuel : .\env\Scripts\Activate.ps1" -ForegroundColor Cyan
            Write-Host "  2. Configurer DATABASE_URL dans .env" -ForegroundColor Cyan
            Write-Host "  3. Exécuter : alembic upgrade head" -ForegroundColor Cyan
            exit 1
        }
    }
}
catch {
    Write-Host "`nErreur : $_" -ForegroundColor Red
    Write-Host "`nVeuillez vérifier :" -ForegroundColor Yellow
    Write-Host "  - La configuration DATABASE_URL dans .env" -ForegroundColor Cyan
    Write-Host "  - La connectivité à la base de données" -ForegroundColor Cyan
    Write-Host "  - Les fichiers de migration dans app/db/migrations/versions/" -ForegroundColor Cyan
    exit 1
}

