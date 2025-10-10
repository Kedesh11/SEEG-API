# 🚀 Commandes de référence rapide - SEEG-API

> Guide de référence rapide pour le déploiement et la surveillance

---

## 📦 Déploiement

### Déploiement initial complet

```powershell
# Déploiement avec tous les packages, CI/CD et monitoring
.\scripts\deploy-api-v2.ps1

# Avec logs de debug
.\scripts\deploy-api-v2.ps1 -LogLevel DEBUG

# Build dans le cloud (recommandé)
.\scripts\deploy-api-v2.ps1 -BuildMode cloud

# Simulation sans exécution
.\scripts\deploy-api-v2.ps1 -DryRun
```

### Déploiements suivants (CI/CD automatique)

```powershell
# Build + Push (Azure redéploie automatiquement)
docker build -t seegbackend.azurecr.io/seeg-backend-api:latest .
docker push seegbackend.azurecr.io/seeg-backend-api:latest
```

### Tests post-déploiement

```powershell
# Tests automatisés complets
.\scripts\test-deployment.ps1
```

---

## 📊 Monitoring

### Logs en temps réel

```powershell
# Logs streaming
az webapp log tail --name seeg-backend-api --resource-group seeg-backend-rg

# Télécharger les logs
az webapp log download --name seeg-backend-api --resource-group seeg-backend-rg --log-file logs.zip
```

### Métriques

```powershell
# CPU et RAM
az monitor metrics list `
    --resource /subscriptions/.../seeg-backend-api `
    --metric-names CpuPercentage MemoryPercentage `
    --start-time (Get-Date).AddHours(-1)

# Temps de réponse
az monitor metrics list `
    --resource /subscriptions/.../seeg-backend-api `
    --metric-names ResponseTime Http5xx Http4xx `
    --start-time (Get-Date).AddHours(-1)
```

### Application Insights

```powershell
# Ouvrir dans le portail
$appId = az webapp show --name seeg-backend-api --resource-group seeg-backend-rg --query "id" -o tsv
Start-Process "https://portal.azure.com/#@/resource$appId/appInsights"
```

### Alertes

```powershell
# Lister toutes les alertes
az monitor metrics alert list --resource-group seeg-backend-rg --output table

# Voir les alertes déclenchées
az monitor metrics alert show --name seeg-api-high-cpu --output table

# Désactiver une alerte temporairement
az monitor metrics alert update --name seeg-api-high-cpu --enabled false
```

---

## 🔄 CI/CD

### Vérifier les webhooks

```powershell
# Liste des webhooks
az acr webhook list --registry seegbackend --output table

# Événements récents
az acr webhook list-events `
    --name seeg-backend-apiWebhook `
    --registry seegbackend `
    --output table

# Tester le webhook
az acr webhook ping --name seeg-backend-apiWebhook --registry seegbackend
```

### État du déploiement

```powershell
# Statut App Service
az webapp show `
    --name seeg-backend-api `
    --resource-group seeg-backend-rg `
    --query "{State:state,Image:siteConfig.linuxFxVersion}" `
    --output table

# Historique des déploiements
az webapp deployment list `
    --name seeg-backend-api `
    --resource-group seeg-backend-rg `
    --output table
```

---

## 🐳 Docker

### Images locales

```powershell
# Lister les images
docker images seegbackend.azurecr.io/seeg-backend-api

# Build local
docker build -t seegbackend.azurecr.io/seeg-backend-api:latest .

# Login ACR
az acr login --name seegbackend

# Push
docker push seegbackend.azurecr.io/seeg-backend-api:latest
```

### Images dans ACR

```powershell
# Lister les repositories
az acr repository list --name seegbackend --output table

# Lister les tags
az acr repository show-tags `
    --name seegbackend `
    --repository seeg-backend-api `
    --orderby time_desc `
    --output table

# Supprimer un tag
az acr repository delete `
    --name seegbackend `
    --image seeg-backend-api:old-tag `
    --yes
```

---

## 🔧 Maintenance

### Redémarrer l'application

```powershell
# Restart normal
az webapp restart --name seeg-backend-api --resource-group seeg-backend-rg

# Stop puis Start (force pull nouvelle image)
az webapp stop --name seeg-backend-api --resource-group seeg-backend-rg
Start-Sleep -Seconds 10
az webapp start --name seeg-backend-api --resource-group seeg-backend-rg
```

### Variables d'environnement

```powershell
# Lister toutes les variables
az webapp config appsettings list `
    --name seeg-backend-api `
    --resource-group seeg-backend-rg `
    --output table

# Ajouter/Modifier une variable
az webapp config appsettings set `
    --name seeg-backend-api `
    --resource-group seeg-backend-rg `
    --settings NEW_VAR=value

# Supprimer une variable
az webapp config appsettings delete `
    --name seeg-backend-api `
    --resource-group seeg-backend-rg `
    --setting-names VAR_TO_DELETE
```

### Scaling

```powershell
# Scale up (plan plus puissant)
az appservice plan update `
    --name seeg-backend-plan `
    --resource-group seeg-backend-rg `
    --sku P1V2

# Scale out (plus d'instances)
az appservice plan update `
    --name seeg-backend-plan `
    --resource-group seeg-backend-rg `
    --number-of-workers 3
```

---

## 🧪 Tests

### Tests manuels

```powershell
# Health check
Invoke-WebRequest -Uri "https://seeg-backend-api.azurewebsites.net/docs"

# Test endpoint spécifique
Invoke-WebRequest -Uri "https://seeg-backend-api.azurewebsites.net/api/v1/auth/login" -Method POST
```

### Tests automatisés

```powershell
# Suite de tests complète
.\scripts\test-deployment.ps1

# Tests Python (pytest)
pytest tests/ -v
```

---

## 🆘 Dépannage

### Voir les logs d'erreur

```powershell
# Logs des dernières minutes
az webapp log tail --name seeg-backend-api --resource-group seeg-backend-rg

# Télécharger tous les logs
az webapp log download --name seeg-backend-api --resource-group seeg-backend-rg --log-file all-logs.zip
```

### Vérifier l'état

```powershell
# État détaillé
az webapp show `
    --name seeg-backend-api `
    --resource-group seeg-backend-rg `
    --output json

# Vérifier le conteneur
az webapp config container show `
    --name seeg-backend-api `
    --resource-group seeg-backend-rg
```

### Rollback

```powershell
# Revenir à l'image précédente
az webapp config container set `
    --name seeg-backend-api `
    --resource-group seeg-backend-rg `
    --docker-custom-image-name seegbackend.azurecr.io/seeg-backend-api:deploy-YYYYMMDD-HHMMSS

# Redémarrer
az webapp restart --name seeg-backend-api --resource-group seeg-backend-rg
```

---

## 📊 Requêtes KQL utiles (Application Insights)

### Erreurs des dernières 24h

```kql
exceptions
| where timestamp > ago(24h)
| summarize count() by type, outerMessage
| order by count_ desc
```

### Top 10 requêtes lentes

```kql
requests
| where timestamp > ago(1h)
| top 10 by duration desc
| project timestamp, name, duration, resultCode
```

### Taux d'erreur par endpoint

```kql
requests
| where timestamp > ago(1h)
| summarize total=count(), errors=countif(success == false) by name
| extend error_rate = (errors * 100.0) / total
| order by error_rate desc
```

### Performance PostgreSQL

```kql
dependencies
| where type == "SQL"
| where timestamp > ago(1h)
| summarize avg(duration), count() by name
| order by avg_duration desc
```

---

## 🎯 Liens rapides

| Ressource | Commande |
|-----------|----------|
| **Portail Azure** | `Start-Process "https://portal.azure.com"` |
| **App Service** | `Start-Process "https://portal.azure.com/#@/resource/.../seeg-backend-api"` |
| **Application Insights** | `Start-Process "https://portal.azure.com/#@/resource/.../seeg-api-insights"` |
| **Container Registry** | `Start-Process "https://portal.azure.com/#@/resource/.../seegbackend"` |
| **API Swagger** | `Start-Process "https://seeg-backend-api.azurewebsites.net/docs"` |

---

**Dernière mise à jour** : 10 octobre 2025  
**Version** : 2.0.0

