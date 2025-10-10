# ============================================================================
# Script de Configuration de l'Environnement Local
# ============================================================================
# Ce script crée automatiquement votre fichier .env.local pour le développement
# ============================================================================

param(
    [Parameter(Mandatory = $false)]
    [string]$DbUser = "postgres",
    
    [Parameter(Mandatory = $false)]
    [string]$DbPassword = "postgres",
    
    [Parameter(Mandatory = $false)]
    [string]$DbHost = "localhost",
    
    [Parameter(Mandatory = $false)]
    [int]$DbPort = 5432,
    
    [Parameter(Mandatory = $false)]
    [string]$DbName = "recruteur"
)

Write-Host ""
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host "  CONFIGURATION DE L'ENVIRONNEMENT LOCAL" -ForegroundColor Cyan
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host ""

# Vérifier si le template existe
if (-not (Test-Path "env.local.template")) {
    Write-Host "[ERREUR] Le fichier env.local.template est introuvable !" -ForegroundColor Red
    exit 1
}

# Vérifier si .env.local existe déjà
if (Test-Path ".env.local") {
    Write-Host "[ATTENTION] Le fichier .env.local existe déjà !" -ForegroundColor Yellow
    $response = Read-Host "Voulez-vous le remplacer ? (o/N)"
    if ($response -ne "o" -and $response -ne "O") {
        Write-Host "[INFO] Configuration annulée" -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "Configuration de la base de données :" -ForegroundColor Yellow
Write-Host "  Hôte     : $DbHost" -ForegroundColor Gray
Write-Host "  Port     : $DbPort" -ForegroundColor Gray
Write-Host "  Database : $DbName" -ForegroundColor Gray
Write-Host "  User     : $DbUser" -ForegroundColor Gray
Write-Host ""

# Lire le template
$content = Get-Content "env.local.template" -Raw

# Remplacer les valeurs de la base de données
$content = $content -replace "postgresql\+asyncpg://postgres:postgres@localhost:5432/recruteur", "postgresql+asyncpg://$DbUser`:$DbPassword@$DbHost`:$DbPort/$DbName"
$content = $content -replace "postgresql://postgres:postgres@localhost:5432/recruteur", "postgresql://$DbUser`:$DbPassword@$DbHost`:$DbPort/$DbName"

# Écrire le fichier .env.local
$content | Out-File -FilePath ".env.local" -Encoding UTF8

Write-Host "[OK] Fichier .env.local créé avec succès !" -ForegroundColor Green
Write-Host ""
Write-Host "Prochaines étapes :" -ForegroundColor Yellow
Write-Host "  1. Vérifiez que PostgreSQL est démarré" -ForegroundColor White
Write-Host "  2. Créez la base de données si nécessaire :" -ForegroundColor White
Write-Host "     psql -U $DbUser -c 'CREATE DATABASE $DbName;'" -ForegroundColor Gray
Write-Host "  3. Lancez l'application :" -ForegroundColor White
Write-Host "     uvicorn app.main:app --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "Pour tester la connexion à la base de données :" -ForegroundColor Yellow
Write-Host "  psql -U $DbUser -h $DbHost -p $DbPort -d $DbName" -ForegroundColor Gray
Write-Host ""
Write-Host "=============================================================" -ForegroundColor Green
Write-Host "  Configuration terminée !" -ForegroundColor Green
Write-Host "=============================================================" -ForegroundColor Green
Write-Host ""

