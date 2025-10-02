# 📊 Azure Application Insights - Guide Complet

**Date**: 2 Octobre 2025  
**Statut**: ✅ Configuré et Prêt

---

## 📋 Vue d'ensemble

Azure Application Insights fournit un monitoring APM (Application Performance Monitoring) complet pour SEEG-API, incluant :

- 📈 **Métriques de performance** en temps réel
- 🔍 **Tracking des requêtes** HTTP
- ⚠️ **Alertes** sur les erreurs et lenteurs
- 📊 **Dashboards** personnalisés
- 🐛 **Debugging** distribué
- 📉 **Analyse des tendances**

---

## 🚀 Configuration

### 1. Créer une Ressource Application Insights

#### Via Azure Portal

1. Connectez-vous au [Portail Azure](https://portal.azure.com)
2. Créez une nouvelle ressource **Application Insights**
3. Configurez :
   - **Nom** : `seeg-api-insights`
   - **Groupe de ressources** : Utilisez votre RG existant
   - **Région** : Même que votre App Service
   - **Mode** : Workspace-based

4. Après création, récupérez la **Connection String** :
   - Allez dans **Overview** de la ressource
   - Copiez `Connection String` (format: `InstrumentationKey=xxx;...`)

#### Via Azure CLI

```bash
# Créer la ressource
az monitor app-insights component create \
  --app seeg-api-insights \
  --location francecentral \
  --resource-group seeg-rg \
  --workspace seeg-logs-workspace

# Récupérer la connection string
az monitor app-insights component show \
  --app seeg-api-insights \
  --resource-group seeg-rg \
  --query connectionString -o tsv
```

### 2. Configurer l'Application

#### Développement Local

Créez/modifiez `.env` :

```bash
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=xxx;IngestionEndpoint=https://xxx;LiveEndpoint=https://xxx
```

#### Production (Azure App Service)

Configurez la variable d'environnement :

```bash
az webapp config appsettings set \
  --name seeg-api-prod \
  --resource-group seeg-rg \
  --settings APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=xxx..."
```

Ou via le portail :
1. App Service > **Configuration**
2. **Application settings** > **New application setting**
3. Nom: `APPLICATIONINSIGHTS_CONNECTION_STRING`
4. Valeur: Votre connection string
5. **Save** et **Restart**

### 3. Installer les Dépendances

```bash
pip install -r requirements.txt
```

Les dépendances suivantes seront installées :
- `opencensus-ext-azure==1.1.13`
- `opencensus-ext-fastapi==0.1.1`
- `opencensus-ext-logging==0.1.1`
- `opencensus-ext-requests==0.8.0`

---

## 📊 Fonctionnalités

### 1. Tracking Automatique des Requêtes

Toutes les requêtes HTTP sont automatiquement trackées avec :

```python
{
  "name": "GET /api/v1/users",
  "url": "https://api.seeg.com/api/v1/users",
  "duration_ms": 125.5,
  "status_code": 200,
  "success": true,
  "properties": {
    "method": "GET",
    "path": "/api/v1/users",
    "user_agent": "Mozilla/5.0...",
    "client_host": "192.168.1.1",
    "user_id": "uuid-xxx"  // Si authentifié
  }
}
```

**Exclusions** : `/health`, `/docs`, `/redoc`, `/openapi.json`

### 2. Tracking Manuel d'Événements

```python
from app.core.monitoring import app_insights

# Tracker un événement personnalisé
app_insights.track_event(
    name="user_signup_completed",
    properties={
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role
    }
)
```

### 3. Tracking d'Exceptions

```python
try:
    # Code risqué
    result = await dangerous_operation()
except Exception as e:
    # Tracker l'exception
    app_insights.track_exception(
        exception=e,
        properties={
            "operation": "dangerous_operation",
            "user_id": user_id
        }
    )
    raise
```

### 4. Métriques Personnalisées

```python
# Tracker une métrique
app_insights.track_metric(
    name="active_users",
    value=150,
    properties={
        "environment": "production"
    }
)

# Exemple : temps de traitement
import time
start = time.time()
# ... traitement ...
duration = time.time() - start

app_insights.track_metric(
    name="processing_time",
    value=duration * 1000,  # en ms
    properties={
        "operation_type": "pdf_processing"
    }
)
```

### 5. Alertes sur Requêtes Lentes

Les requêtes > 1 seconde sont automatiquement loguées :

```json
{
  "level": "warning",
  "message": "Requête lente détectée",
  "path": "/api/v1/applications",
  "method": "POST",
  "duration_ms": 1250.5,
  "status_code": 201
}
```

---

## 📈 Dashboards Azure

### Dashboard Recommandé

1. **Performances**
   - Temps de réponse moyen
   - Requêtes/seconde
   - Taux d'échec

2. **Disponibilité**
   - Uptime %
   - Tests de disponibilité
   - Santé des dépendances

3. **Erreurs**
   - Top 10 exceptions
   - Taux d'erreur par endpoint
   - Alertes actives

4. **Utilisation**
   - Utilisateurs actifs
   - Endpoints les plus utilisés
   - Géographie des utilisateurs

### Créer un Dashboard

#### Via Portal

1. **Application Insights** > **Overview**
2. Cliquez sur **Dashboard** > **New dashboard**
3. Ajoutez des tuiles :
   - `Requests` : Graphique des requêtes
   - `Failed requests` : Taux d'échec
   - `Server response time` : Temps de réponse
   - `Availability` : Tests de disponibilité

#### Requêtes KQL Utiles

```kusto
// Top 10 endpoints les plus lents
requests
| summarize avg(duration) by name
| order by avg_duration desc
| take 10

// Taux d'erreur par heure
requests
| where timestamp > ago(24h)
| summarize 
    total = count(),
    errors = countif(success == false)
    by bin(timestamp, 1h)
| extend error_rate = errors * 100.0 / total
| render timechart

// Requêtes lentes (> 1s)
requests
| where duration > 1000
| project timestamp, name, duration, resultCode, url
| order by duration desc

// Utilisateurs actifs par heure
customEvents
| where name == "user_activity"
| summarize dcount(tostring(customDimensions.user_id)) by bin(timestamp, 1h)
| render timechart
```

---

## 🔔 Configuration des Alertes

### 1. Alertes sur les Erreurs

```bash
az monitor metrics alert create \
  --name seeg-api-error-rate-high \
  --resource-group seeg-rg \
  --scopes /subscriptions/{sub-id}/resourceGroups/seeg-rg/providers/microsoft.insights/components/seeg-api-insights \
  --condition "avg requests/failed > 5" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action-group seeg-alerts-group \
  --description "Taux d'erreur élevé (>5 requêtes échouées)"
```

### 2. Alertes sur les Performances

```bash
az monitor metrics alert create \
  --name seeg-api-slow-response \
  --resource-group seeg-rg \
  --scopes /subscriptions/{sub-id}/resourceGroups/seeg-rg/providers/microsoft.insights/components/seeg-api-insights \
  --condition "avg requests/duration > 2000" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action-group seeg-alerts-group \
  --description "Temps de réponse élevé (>2s)"
```

### 3. Alertes via Portal

1. **Application Insights** > **Alerts**
2. **New alert rule**
3. Configurez :
   - **Condition** : Métrique à surveiller
   - **Actions** : Email, SMS, Webhook
   - **Seuils** : Valeurs critiques

**Alertes recommandées** :
- Taux d'erreur > 5%
- Temps de réponse > 2s
- Availability < 99%
- Exceptions non gérées

---

## 🔍 Monitoring en Production

### Métriques Clés à Surveiller

| Métrique | Seuil Acceptable | Critique |
|----------|------------------|----------|
| Temps de réponse moyen | < 500ms | > 2s |
| Taux d'erreur | < 1% | > 5% |
| Availability | > 99.9% | < 99% |
| Requêtes/seconde | Baseline | +300% |
| Exceptions/heure | < 10 | > 50 |

### Tests de Disponibilité

Configurez des tests ping toutes les 5 minutes :

```bash
az monitor app-insights component-billing update \
  --app seeg-api-insights \
  --resource-group seeg-rg \
  --basic-plan
```

Endpoints à tester :
- `GET https://api.seeg.com/health` (5 min)
- `GET https://api.seeg.com/api/v1/jobs` (15 min)

---

## 💡 Best Practices

### 1. Sampling

En production, utilisez un sampling rate de 10% pour réduire les coûts :

```python
# app/core/monitoring/app_insights.py (déjà configuré)
sample_rate = 1.0 if settings.ENVIRONMENT == "development" else 0.1
```

### 2. Properties Sensibles

**NE PAS tracker** :
- Mots de passe
- Tokens JWT
- Données personnelles sensibles (RGPD)
- Clés API

### 3. Performance

- Utilisez le tracking asynchrone
- Évitez de tracker dans des boucles
- Batch les événements si possible

### 4. Coûts

- Monitoring gratuit : 5 GB/mois
- Au-delà : ~2€/GB
- Utilisez le sampling en production
- Configurez la rétention des données (30-90 jours)

---

## 🧪 Tester l'Intégration

### 1. Vérifier la Configuration

```bash
# Démarrer l'API
uvicorn app.main:app --reload

# Vérifier le statut
curl http://localhost:8000/info | jq .monitoring
```

**Réponse attendue** :
```json
{
  "monitoring": {
    "application_insights": "enabled",
    "instrumentation": true
  }
}
```

### 2. Générer du Trafic Test

```bash
# Requêtes normales
for i in {1..10}; do
  curl http://localhost:8000/api/v1/jobs
done

# Requêtes avec erreur
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "invalid", "password": "wrong"}'
```

### 3. Vérifier dans Azure

1. Attendez 2-5 minutes (délai d'ingestion)
2. **Application Insights** > **Live Metrics**
3. Vous devriez voir :
   - Requêtes en temps réel
   - Temps de réponse
   - Erreurs (si générées)

---

## 📚 Ressources

- [Documentation Azure Application Insights](https://docs.microsoft.com/azure/azure-monitor/app/app-insights-overview)
- [OpenCensus Python](https://github.com/census-instrumentation/opencensus-python)
- [KQL Query Language](https://docs.microsoft.com/azure/data-explorer/kusto/query/)
- [Best Practices APM](https://docs.microsoft.com/azure/azure-monitor/app/best-practices)

---

## 🆘 Troubleshooting

### Problème : Aucune donnée dans Application Insights

**Vérifications** :
1. Connection string correcte ?
2. Variable d'environnement chargée ?
3. Délai d'ingestion (2-5 min) ?
4. Firewall/Proxy bloque-t-il Azure ?

**Solution** :
```bash
# Tester la connectivité
curl https://{YOUR-REGION}.applicationinsights.azure.com/

# Vérifier les logs
tail -f logs/app.log | grep "Application Insights"
```

### Problème : Coûts élevés

**Solutions** :
- Augmenter le sampling rate (actuellement 10%)
- Réduire la rétention (90 → 30 jours)
- Filtrer les endpoints non-critiques
- Exclure les health checks

### Problème : Latence ajoutée

**Impact** : ~5-10ms par requête

**Solutions** :
- Tracking asynchrone (déjà implémenté)
- Désactiver en dev si nécessaire
- Utiliser le sampling

---

**🎉 Application Insights est maintenant configuré et prêt pour le monitoring production !**

