# Guide de Déploiement Docker SEEG-API

## Vue d'ensemble

Ce guide explique comment déployer SEEG-API avec Docker, incluant tous les services de monitoring et d'infrastructure.

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Nginx     │────▶│  SEEG-API   │────▶│ PostgreSQL  │
│  (Reverse   │     │   (FastAPI) │     │  (Database) │
│   Proxy)    │     └──────┬──────┘     └─────────────┘
└─────────────┘            │
                           │
                    ┌──────▼──────┐
                    │    Redis    │
                    │   (Cache)   │
                    └─────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐     ┌──────▼──────┐   ┌─────▼─────┐
    │ Jaeger  │     │ Prometheus  │   │  Grafana  │
    │(Tracing)│     │  (Metrics)  │   │(Dashboard)│
    └─────────┘     └─────────────┘   └───────────┘
```

## Prérequis

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 10GB espace disque

## Installation rapide

### 1. Cloner le projet

```bash
git clone https://github.com/seeg/seeg-api.git
cd seeg-api
```

### 2. Configuration

```bash
# Copier le fichier d'environnement
cp env.example .env

# Éditer les variables importantes
nano .env
```

Variables critiques à modifier :
- `SECRET_KEY` : Générer une clé sécurisée (32+ caractères)
- `DATABASE_URL` : Ajuster si nécessaire
- `SMTP_*` : Configuration email

### 3. Démarrage

```bash
# Build et démarrage de tous les services
docker-compose up -d --build

# Vérifier que tout est lancé
docker-compose ps

# Voir les logs
docker-compose logs -f
```

### 4. Initialisation

```bash
# Les migrations sont exécutées automatiquement au démarrage
# Pour créer le premier administrateur :
curl -X POST http://localhost:8000/api/v1/auth/create-first-admin \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@seeg.ga",
    "password": "AdminPassword123!",
    "first_name": "Admin",
    "last_name": "SEEG"
  }'
```

## Services et accès

| Service | URL | Credentials |
|---------|-----|-------------|
| API | http://localhost:8000 | - |
| API Docs | http://localhost:8000/docs | - |
| Grafana | http://localhost:3000 | admin/admin |
| Prometheus | http://localhost:9090 | - |
| Jaeger | http://localhost:16686 | - |

## Configuration avancée

### SSL/TLS

1. Placer les certificats dans `./ssl/` :
   - `cert.pem` : Certificat
   - `key.pem` : Clé privée

2. Décommenter les lignes SSL dans `nginx.conf`

3. Redémarrer Nginx :
   ```bash
   docker-compose restart nginx
   ```

### Scaling

Pour augmenter le nombre d'instances API :

```bash
# Scaler à 3 instances
docker-compose up -d --scale seeg-api=3
```

### Personnalisation des ressources

Créer `docker-compose.override.yml` :

```yaml
version: '3.8'

services:
  seeg-api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
  
  postgres:
    deploy:
      resources:
        limits:
          memory: 1G
```

## Monitoring

### Dashboards Grafana

1. Accéder à Grafana : http://localhost:3000
2. Login : admin/admin
3. Importer les dashboards depuis `monitoring/grafana/dashboards/`

### Alertes

Configurer les webhooks dans `monitoring/alerts.yml` :

```yaml
receivers:
  - name: 'email'
    email_configs:
      - to: 'ops@seeg.ga'
        from: 'alerts@seeg.ga'
  
  - name: 'slack'
    slack_configs:
      - api_url: 'YOUR_WEBHOOK_URL'
        channel: '#alerts'
```

### Métriques personnalisées

Ajouter dans `monitoring/prometheus.yml` :

```yaml
- job_name: 'custom-metrics'
  static_configs:
    - targets: ['your-service:port']
```

## Maintenance

### Backup

#### Base de données

```bash
# Backup
docker exec seeg-postgres pg_dump -U seeg seeg_db > backup_$(date +%Y%m%d).sql

# Restore
docker exec -i seeg-postgres psql -U seeg seeg_db < backup_20251209.sql
```

#### Volumes Docker

```bash
# Backup tous les volumes
docker run --rm -v seeg-api_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

### Logs

```bash
# Voir les logs d'un service
docker-compose logs -f seeg-api

# Exporter les logs
docker-compose logs > logs_$(date +%Y%m%d).txt

# Rotation automatique (dans docker-compose.yml)
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "5"
```

### Mise à jour

```bash
# Arrêter les services
docker-compose down

# Pull les dernières images
docker-compose pull

# Rebuild si nécessaire
docker-compose build --no-cache

# Redémarrer
docker-compose up -d
```

## Troubleshooting

### Problèmes courants

#### 1. "Cannot connect to database"

```bash
# Vérifier que PostgreSQL est prêt
docker-compose logs postgres

# Tester la connexion
docker exec -it seeg-postgres psql -U seeg -d seeg_db
```

#### 2. "Redis connection refused"

```bash
# Vérifier Redis
docker-compose logs redis

# Tester Redis
docker exec -it seeg-redis redis-cli ping
```

#### 3. "Port already in use"

```bash
# Changer les ports dans docker-compose.yml
ports:
  - "8001:8000"  # API sur port 8001
```

### Debug

```bash
# Entrer dans un conteneur
docker exec -it seeg-api bash

# Vérifier les variables d'environnement
docker exec seeg-api env | grep -E "(DATABASE|REDIS|SECRET)"

# Tester l'API depuis l'intérieur
docker exec seeg-api curl localhost:8000/monitoring/health
```

### Performance

```bash
# Statistiques des conteneurs
docker stats

# Analyser l'utilisation disque
docker system df

# Nettoyer les ressources inutilisées
docker system prune -a
```

## Production

### Checklist de production

- [ ] Changer tous les mots de passe par défaut
- [ ] Configurer SSL/TLS
- [ ] Désactiver les interfaces de debug (Grafana, Prometheus)
- [ ] Configurer les backups automatiques
- [ ] Mettre en place le monitoring externe
- [ ] Configurer les limites de ressources
- [ ] Activer les logs centralisés
- [ ] Configurer un reverse proxy externe
- [ ] Mettre en place la haute disponibilité

### Configuration production

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  seeg-api:
    restart: always
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - LOG_LEVEL=WARNING
      - TRACING_SAMPLE_RATE=0.1
    
  postgres:
    restart: always
    volumes:
      - ./postgres.conf:/etc/postgresql/postgresql.conf
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

### Déploiement

```bash
# Utiliser la config de production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Sécurité

### Bonnes pratiques

1. **Réseau isolé** : Les services communiquent via le réseau Docker interne
2. **Utilisateur non-root** : L'API s'exécute avec un utilisateur dédié
3. **Secrets** : Utiliser Docker Secrets en production
4. **Firewall** : Exposer uniquement les ports nécessaires

### Docker Secrets

```yaml
secrets:
  db_password:
    external: true
  jwt_secret:
    external: true

services:
  seeg-api:
    secrets:
      - db_password
      - jwt_secret
```

## Support

Pour toute assistance :
1. Consulter les logs : `docker-compose logs`
2. Vérifier la documentation : `/docs`
3. Ouvrir une issue sur GitHub
4. Contacter l'équipe : support@seeg.ga
