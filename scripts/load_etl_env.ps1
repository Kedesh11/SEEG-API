# Script pour charger les variables d'environnement ETL
# Usage: .\load_etl_env.ps1

Write-Host "`nChargement de la configuration ETL depuis .env.etl..." -ForegroundColor Cyan

if (-not (Test-Path .env.etl)) {
    Write-Host "Fichier .env.etl introuvable !" -ForegroundColor Red
    Write-Host "Creez le fichier .env.etl avec les variables requises." -ForegroundColor Yellow
    exit 1
}

# Lire le fichier .env.etl
Get-Content .env.etl | ForEach-Object {
    $line = $_.Trim()
    
    # Ignorer les lignes vides et les commentaires
    if ($line -and -not $line.StartsWith("#")) {
        # Extraire la cle et la valeur
        if ($line -match "^([^=]+)=(.*)") {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            # Ne pas afficher la connection string complète (trop longue)
            if ($key -eq "AZURE_STORAGE_CONNECTION_STRING") {
                if ($value -ne "DefaultEndpointsProtocol=https;AccountName=seegairaweu001;AccountKey=YOUR_KEY_HERE;EndpointSuffix=core.windows.net") {
                    Set-Item -Path "env:$key" -Value $value
                    Write-Host "✅ $key : Défini (masqué)" -ForegroundColor Green
                }
                else {
                    Write-Host "⚠️  $key : PLACEHOLDER détecté - Remplacez YOUR_KEY_HERE par la vraie clé" -ForegroundColor Yellow
                }
            }
            else {
                Set-Item -Path "env:$key" -Value $value
                Write-Host "✅ $key : $value" -ForegroundColor Green
            }
        }
    }
}

Write-Host "`n✅ Configuration ETL chargée avec succès !`n" -ForegroundColor Green
Write-Host "💡 Vous pouvez maintenant lancer le test:" -ForegroundColor Cyan
Write-Host "   python test_etl_webhook.py`n" -ForegroundColor White

