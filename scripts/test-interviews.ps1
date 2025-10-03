# Script de test pour l'API Calendrier d'Entretiens
# Exécute les tests avant migration

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  TESTS API CALENDRIER D'ENTRETIENS" -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Cyan

# Vérifier que nous sommes dans le bon répertoire
if (-not (Test-Path "app")) {
    Write-Host "Erreur: Doit etre execute depuis la racine du projet" -ForegroundColor Red
    exit 1
}

# Vérifier l'environnement virtuel
$PYTHON_EXE = "venv\Scripts\python.exe"
if (-not (Test-Path $PYTHON_EXE)) {
    $PYTHON_EXE = "env\Scripts\python.exe"
}

if (-not (Test-Path $PYTHON_EXE)) {
    Write-Host "Erreur: Environnement virtuel non trouve" -ForegroundColor Red
    Write-Host "Cherche dans: venv\ ou env\" -ForegroundColor Yellow
    exit 1
}

Write-Host "[1/5] Environnement virtuel trouve" -ForegroundColor Green
Write-Host "      Python: $PYTHON_EXE`n" -ForegroundColor Gray

# Installer les dépendances de test si nécessaire
Write-Host "[2/5] Verification des dependances de test..." -ForegroundColor Yellow
& $PYTHON_EXE -m pip list | Select-String "pytest" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Installation de pytest..." -ForegroundColor Gray
    & $PYTHON_EXE -m pip install pytest pytest-asyncio httpx -q
}
Write-Host "      Dependances OK`n" -ForegroundColor Green

# Tests unitaires du service
Write-Host "[3/5] Execution des tests unitaires..." -ForegroundColor Yellow
Write-Host "      Fichier: tests/unit/test_interview_service.py" -ForegroundColor Gray
& $PYTHON_EXE -m pytest tests/unit/test_interview_service.py -v --tb=short

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n========================================" -ForegroundColor Red
    Write-Host "  TESTS UNITAIRES ECHOUES" -ForegroundColor Red
    Write-Host "========================================`n" -ForegroundColor Red
    exit 1
}

Write-Host "`n      Tests unitaires: OK`n" -ForegroundColor Green

# Tests d'intégration des endpoints
Write-Host "[4/5] Execution des tests d'integration..." -ForegroundColor Yellow
Write-Host "      Fichier: tests/interviews/test_interviews_endpoints.py" -ForegroundColor Gray
& $PYTHON_EXE -m pytest tests/interviews/test_interviews_endpoints.py -v --tb=short

if ($LASTEXITCODE -ne 0) {
    Write-Host "`n========================================" -ForegroundColor Red
    Write-Host "  TESTS D'INTEGRATION ECHOUES" -ForegroundColor Red
    Write-Host "========================================`n" -ForegroundColor Red
    exit 1
}

Write-Host "`n      Tests d'integration: OK`n" -ForegroundColor Green

# Rapport de couverture
Write-Host "[5/5] Generation du rapport de couverture..." -ForegroundColor Yellow
& $PYTHON_EXE -m pytest tests/interviews/ tests/unit/test_interview_service.py `
    --cov=app.services.interview `
    --cov=app.api.v1.endpoints.interviews `
    --cov=app.schemas.interview `
    --cov-report=term-missing `
    --cov-report=html:htmlcov `
    -q

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n      Rapport HTML genere: htmlcov/index.html" -ForegroundColor Gray
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  TOUS LES TESTS REUSSIS" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "RESULTATS:" -ForegroundColor Yellow
Write-Host "  Tests unitaires: PASS" -ForegroundColor Green
Write-Host "  Tests integration: PASS" -ForegroundColor Green
Write-Host "  Couverture generee: htmlcov/index.html" -ForegroundColor White

Write-Host "`nPROCHAINE ETAPE:" -ForegroundColor Yellow
Write-Host "  Executer les migrations:" -ForegroundColor White
Write-Host "    .\scripts\run-migrations.ps1" -ForegroundColor Cyan

Write-Host "`n========================================`n" -ForegroundColor Cyan

