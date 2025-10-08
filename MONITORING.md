# Guide de Monitoring SEEG-API

## Vue d'ensemble

Le système de monitoring de SEEG-API fournit une observabilité complète avec :
- **Métriques** : Prometheus + Grafana
- **Logs** : Structlog avec JSON
- **Tracing** : OpenTelemetry + Jaeger
- **Health Checks** : Endpoints de santé

## Démarrage rapide

### 1. Lancer l'infrastructure complète

```bash
# Démarrer tous les services
docker-compose up -d

# Vérifier les services
docker-compose ps

# Voir les logs
docker-compose logs -f seeg-api
```

### 2. Accès aux interfaces

- **API** : http://localhost:8000
- **Documentation API** : http://localhost:8000/docs
- **Jaeger UI** : http://localhost:16686
- **Prometheus** : http://localhost:9090
- **Grafana** : http://localhost:3000 (admin/admin)
- **Health Check** : http://localhost:8000/monitoring/health
- **Métriques** : http://localhost:8000/monitoring/metrics

## Configuration

### Variables d'environnement

```env
# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Tracing
ENABLE_TRACING=true
JAEGER_ENDPOINT=localhost:6831
OTLP_ENDPOINT=http://localhost:4317
TRACING_SAMPLE_RATE=1.0

# Metrics
METRICS_ENABLED=true
PROMETHEUS_PORT=9090

# Redis
REDIS_URL=redis://localhost:6379/0
```

### Configuration des alertes

Créez `monitoring/alerts.yml` :

```yaml
groups:
  - name: seeg-api
    rules:
      - alert: HighErrorRate
        expr: rate(seeg_api_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Taux d'erreur élevé"
          
      - alert: SlowRequests
        expr: histogram_quantile(0.95, rate(seeg_api_http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Requêtes lentes détectées"
```

## Métriques disponibles

### HTTP
- `seeg_api_http_requests_total` : Nombre total de requêtes
- `seeg_api_http_request_duration_seconds` : Durée des requêtes

### Business
- `seeg_api_applications_created_total` : Candidatures créées
- `seeg_api_documents_uploaded_total` : Documents uploadés
- `seeg_api_auth_attempts_total` : Tentatives d'authentification

### Système
- `seeg_api_system_cpu_usage_percent` : Utilisation CPU
- `seeg_api_system_memory_usage_bytes` : Utilisation mémoire

### Cache
- `seeg_api_cache_hits_total` : Cache hits
- `seeg_api_cache_misses_total` : Cache misses

## Dashboards Grafana

### Import des dashboards

1. Connectez-vous à Grafana (admin/admin)
2. Allez dans "Import Dashboard"
3. Importez les dashboards depuis `monitoring/grafana/dashboards/`

### Dashboards disponibles

- **Overview** : Vue d'ensemble de l'application
- **Performance** : Métriques de performance
- **Business** : Métriques métier
- **Infrastructure** : Santé de l'infrastructure

## Logs structurés

### Format des logs

```json
{
  "timestamp": "2025-12-09T10:00:00.000Z",
  "level": "INFO",
  "logger_name": "api",
  "message": "Request completed",
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "user-123",
  "method": "GET",
  "path": "/api/v1/users",
  "status_code": 200,
  "duration_seconds": 0.125
}
```

### Requêtes de logs

```bash
# Voir les logs d'erreur
docker-compose logs seeg-api | jq 'select(.level == "ERROR")'

# Filtrer par request_id
docker-compose logs seeg-api | jq 'select(.request_id == "123...")'

# Statistiques par endpoint
docker-compose logs seeg-api | jq -r '.path' | sort | uniq -c
```

## Tracing distribué

### Recherche de traces

1. Ouvrez Jaeger UI : http://localhost:16686
2. Sélectionnez le service "seeg-api"
3. Recherchez par :
   - Tags : `http.method`, `http.status_code`
   - Durée : Min/Max duration
   - Opération : Nom de l'endpoint

### Analyse des traces

- **Latence** : Identifiez les goulots d'étranglement
- **Dépendances** : Visualisez les appels entre services
- **Erreurs** : Trouvez rapidement la cause des erreurs

## Alerting

### Configuration Slack

```yaml
# alertmanager.yml
route:
  receiver: 'slack-notifications'

receivers:
  - name: 'slack-notifications'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts'
```

## Troubleshooting

### Problèmes courants

1. **Métriques non disponibles**
   - Vérifiez que l'utilisateur a les droits admin
   - Vérifiez la configuration Prometheus

2. **Traces manquantes**
   - Vérifiez que `ENABLE_TRACING=true`
   - Vérifiez la connexion à Jaeger

3. **Logs non structurés**
   - Vérifiez `LOG_FORMAT=json`
   - Vérifiez le fichier `logging.yaml`

### Debug

```bash
# Vérifier la santé
curl http://localhost:8000/monitoring/health

# Vérifier les métriques
curl -H "Authorization: Bearer <token>" http://localhost:8000/monitoring/metrics

# Tester le tracing
curl -H "X-B3-TraceId: 123456789abcdef" http://localhost:8000/api/v1/users
```

## Performance

### Optimisation

1. **Sampling** : Réduire `TRACING_SAMPLE_RATE` en production
2. **Retention** : Configurer la rétention Prometheus/Jaeger
3. **Aggregation** : Utiliser des métriques agrégées

### Benchmarking

```bash
# Test de charge avec Apache Bench
ab -n 1000 -c 10 http://localhost:8000/api/v1/jobs

# Test avec k6
k6 run monitoring/load-tests/api-test.js
```

## Sécurité

### Protection des endpoints

- `/monitoring/metrics` : Requiert authentification admin
- `/monitoring/stats` : Requiert authentification admin
- Jaeger/Prometheus : À sécuriser en production

### Bonnes pratiques

1. Ne pas logger d'informations sensibles
2. Anonymiser les données dans les traces
3. Limiter l'accès aux dashboards
4. Rotation des logs

## Maintenance

### Backup

```bash
# Backup Prometheus
docker exec seeg-prometheus tar -czf - /prometheus > prometheus-backup.tar.gz

# Backup Grafana
docker exec seeg-grafana tar -czf - /var/lib/grafana > grafana-backup.tar.gz
```

### Mise à jour

```bash
# Mettre à jour les images
docker-compose pull

# Redémarrer avec les nouvelles images
docker-compose up -d
```

## Support

Pour toute question ou problème :
1. Consultez les logs : `docker-compose logs`
2. Vérifiez les métriques : `/monitoring/metrics`
3. Analysez les traces dans Jaeger
4. Contactez l'équipe DevOps
