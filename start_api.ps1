# Script pour démarrer l'API SEEG avec l'environnement virtuel
Set-Location "C:\Users\Sevan Kedesh IKISSA\Desktop\Projects\Programme\SEEG\SEEG-API"
.\env\Scripts\Activate.ps1
$env:ENVIRONMENT = "development"
$env:DEBUG = "true"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

