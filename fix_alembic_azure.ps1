# Script pour corriger la table alembic_version dans Azure PostgreSQL
# Remplace d150a8fca35c par 20251010_add_updated_at

param(
    [string]$ResourceGroup = "seeg-rg",
    [string]$ServerName = "seeg-postgres-server",
    [string]$DatabaseName = "postgres",
    [string]$Username = "Sevan"
)

Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " CORRECTION TABLE ALEMBIC_VERSION (AZURE)" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

# Récupérer l'IP publique
try {
    $myIp = (Invoke-WebRequest -Uri "https://api.ipify.org" -UseBasicParsing).Content
    Write-Host "[INFO] Votre IP publique: $myIp" -ForegroundColor Cyan
}
catch {
    Write-Host "[ERREUR] Impossible de récupérer l'IP publique" -ForegroundColor Red
    exit 1
}

# Ajouter une règle de firewall temporaire
$ruleName = "fix-alembic-$($myIp -replace '\.','-')"
Write-Host "[INFO] Ajout règle firewall temporaire..." -ForegroundColor Cyan

az postgres flexible-server firewall-rule create `
    --resource-group $ResourceGroup `
    --name $ServerName `
    --rule-name $ruleName `
    --start-ip-address $myIp `
    --end-ip-address $myIp `
    --output none 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Règle firewall ajoutée" -ForegroundColor Green
}

# Construire la chaîne de connexion
$Server = "$ServerName.postgres.database.azure.com"
$Password = Read-Host "Mot de passe pour l'utilisateur '$Username'" -AsSecureString
$PasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password))

Write-Host ""
Write-Host "[INFO] Exécution du SQL..." -ForegroundColor Cyan
Write-Host ""

# Exécuter les commandes SQL
$SqlCommands = @"
-- Voir la version actuelle
SELECT 'Version actuelle:' as info, version_num FROM alembic_version;

-- Mettre à jour
UPDATE alembic_version SET version_num = '20251010_add_updated_at' WHERE version_num = 'd150a8fca35c';

-- Si vide, insérer
INSERT INTO alembic_version (version_num) 
SELECT '20251010_add_updated_at' 
WHERE NOT EXISTS (SELECT 1 FROM alembic_version);

-- Vérifier
SELECT 'Version après correction:' as info, version_num FROM alembic_version;
"@

# Utiliser psql si disponible
try {
    $env:PGPASSWORD = $PasswordPlain
    $SqlCommands | psql -h $Server -U $Username -d $DatabaseName -p 5432
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    
    Write-Host ""
    Write-Host "[OK] Correction appliquée avec succès!" -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host "[ERREUR] psql n'est pas disponible" -ForegroundColor Red
    Write-Host ""
    Write-Host "Méthode alternative:" -ForegroundColor Yellow
    Write-Host "1. Installez psql ou utilisez Azure Cloud Shell" -ForegroundColor Yellow
    Write-Host "2. Exécutez manuellement le SQL suivant:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host $SqlCommands -ForegroundColor White
}

# Supprimer la règle firewall
Write-Host ""
Write-Host "[INFO] Suppression de la règle firewall temporaire..." -ForegroundColor Cyan
az postgres flexible-server firewall-rule delete `
    --resource-group $ResourceGroup `
    --name $ServerName `
    --rule-name $ruleName `
    --yes `
    --output none 2>$null

Write-Host "[OK] Nettoyage terminé" -ForegroundColor Green
Write-Host ""
Write-Host "Vous pouvez maintenant relancer: scripts/run-migrations.ps1" -ForegroundColor Cyan

