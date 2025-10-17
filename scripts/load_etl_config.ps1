# ============================================================================
# Script pour charger la configuration ETL
# Usage: . .\load_etl_config.ps1
# ============================================================================

Write-Host "🔧 Chargement de la configuration ETL..." -ForegroundColor Cyan

# Lire et charger les variables depuis .env.etl
Get-Content .env.etl | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        
        if ($name -and $value) {
            [Environment]::SetEnvironmentVariable($name, $value, 'Process')
            Write-Host "  ✅ $name défini" -ForegroundColor Green
        }
    }
}

Write-Host "`n✅ Configuration ETL chargée avec succès!" -ForegroundColor Green
Write-Host "`n💡 Variables définies:" -ForegroundColor Yellow
Write-Host "   - AZURE_STORAGE_CONNECTION_STRING" -ForegroundColor Gray
Write-Host "   - WEBHOOK_SECRET" -ForegroundColor Gray
Write-Host "`nVous pouvez maintenant:" -ForegroundColor Yellow
Write-Host "   - Lancer l'API: uvicorn app.main:app --reload" -ForegroundColor Gray
Write-Host "   - Tester l'ETL: python test_etl_webhook.py`n" -ForegroundColor Gray

