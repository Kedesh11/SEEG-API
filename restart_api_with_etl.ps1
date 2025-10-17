# Script pour redémarrer l'API avec les variables ETL
Write-Host "`n=== Redémarrage de l'API avec configuration ETL ===" -ForegroundColor Cyan

# Étape 1 : Charger les variables ETL
Write-Host "`n1. Chargement des variables ETL..." -ForegroundColor Yellow
if (Test-Path .env.etl) {
    Get-Content .env.etl | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#")) {
            if ($line -match "^([^=]+)=(.*)") {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                Set-Item -Path "env:$key" -Value $value
                if ($key -eq "AZURE_STORAGE_CONNECTION_STRING") {
                    Write-Host "   [OK] $key : Defini (masque)" -ForegroundColor Green
                }
                else {
                    Write-Host "   [OK] $key : $value" -ForegroundColor Green
                }
            }
        }
    }
}
else {
    Write-Host "   [ERREUR] Fichier .env.etl introuvable !" -ForegroundColor Red
    exit 1
}

# Étape 2 : Arrêter l'API en cours
Write-Host "`n2. Arret de l'API en cours..." -ForegroundColor Yellow
$uvicornProcess = Get-Process -Name "python" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*app.main:app*"
}

if ($uvicornProcess) {
    Stop-Process -Id $uvicornProcess.Id -Force
    Write-Host "   [OK] API arretee (PID: $($uvicornProcess.Id))" -ForegroundColor Green
    Start-Sleep -Seconds 2
}
else {
    Write-Host "   [INFO] Aucune API en cours d'execution" -ForegroundColor Gray
}

# Étape 3 : Démarrer l'API en arrière-plan
Write-Host "`n3. Demarrage de l'API avec les variables ETL..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; uvicorn app.main:app --reload --port 8000"
Write-Host "   [OK] API demarree en arriere-plan" -ForegroundColor Green

# Étape 4 : Attendre que l'API soit prête
Write-Host "`n4. Attente du demarrage de l'API..." -ForegroundColor Yellow
Start-Sleep -Seconds 8
Write-Host "   [OK] API prete" -ForegroundColor Green

Write-Host "`n=== Configuration terminee ===" -ForegroundColor Green
Write-Host "`nVous pouvez maintenant lancer le test:" -ForegroundColor Cyan
Write-Host "   python test_etl_webhook.py`n" -ForegroundColor White

