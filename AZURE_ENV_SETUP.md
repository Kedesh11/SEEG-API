# Configuration Azure pour SEEG API

## 🚀 Variables d'environnement Azure App Service

Ces variables doivent être configurées dans Azure Portal → App Service → Configuration → Application Settings

### 🔐 Variables CRITIQUES (à configurer dans Azure Portal)

```bash
# Base de données Azure PostgreSQL
DATABASE_URL=postgresql+asyncpg://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres
DATABASE_URL_SYNC=postgresql://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres

# Sécurité - IMPORTANT: Générer une vraie clé
SECRET_KEY=[Générer avec: openssl rand -hex 32]

# Email SMTP - Mot de passe réel
SMTP_PASSWORD=[Mot de passe application Gmail]

# Azure Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=[Obtenir depuis Azure Portal]

# Redis Azure Cache (si configuré)
REDIS_URL=redis://:PASSWORD@your-redis.redis.cache.windows.net:6380/0?ssl=True
```

### 📝 Variables standard (peuvent être dans .env.production)

```bash
# Environnement
ENVIRONMENT=production
DEBUG=false

# Application
APP_NAME=One HCM SEEG Backend
APP_VERSION=1.0.0
WORKERS=4
WEBSITES_PORT=8000

# CORS - Domaines de production
ALLOWED_ORIGINS=https://www.seeg-talentsource.com,https://seeg-hcm.vercel.app,https://seeg-backend-api.azurewebsites.net
ALLOWED_CREDENTIALS=true

# JWT Configuration
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
JWT_ISSUER=seeg-api
JWT_AUDIENCE=seeg-clients

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_TLS=true
SMTP_SSL=false
SMTP_USERNAME=noreply@seeg-talentsource.com
MAIL_FROM_EMAIL=support@seeg-talentsource.com
MAIL_FROM_NAME=One HCM - SEEG Talent Source

# URLs
PUBLIC_APP_URL=https://www.seeg-talentsource.com

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
ENABLE_TRACING=true
METRICS_ENABLED=true
CONSOLE_EXPORT=false

# Rate Limiting
RATE_LIMIT_DEFAULT=100 per minute
RATE_LIMIT_AUTH=5 per minute
RATE_LIMIT_SIGNUP=3 per hour
RATE_LIMIT_UPLOAD=10 per hour

# Azure Functions (Webhooks)
WEBHOOK_SECRET=[Générer une clé secrète]
AZ_FUNC_ON_APP_SUBMITTED_URL=https://your-function.azurewebsites.net/api/OnApplicationSubmitted
AZ_FUNC_ON_APP_SUBMITTED_KEY=[Function Key]
```

## 🔧 Configuration dans Azure Portal

### 1. Via Azure Portal UI

1. Allez dans : **App Services** → **seeg-backend-api**
2. Menu gauche : **Settings** → **Configuration**
3. Cliquez sur **+ New application setting**
4. Ajoutez chaque variable une par une

### 2. Via Azure CLI

```powershell
# Connexion à Azure
az login

# Définir les variables critiques
az webapp config appsettings set `
  --resource-group seeg-backend-rg `
  --name seeg-backend-api `
  --settings `
    DATABASE_URL="postgresql+asyncpg://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres" `
    DATABASE_URL_SYNC="postgresql://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres" `
    SECRET_KEY="$(openssl rand -hex 32)" `
    ENVIRONMENT="production" `
    DEBUG="false"
```

### 3. Via Azure DevOps Pipeline

Ajoutez dans votre `azure-pipelines.yml` :

```yaml
- task: AzureWebApp@1
  inputs:
    appName: 'seeg-backend-api'
    appSettings: |
      [
        {
          "name": "DATABASE_URL",
          "value": "$(DATABASE_URL)",
          "slotSetting": false
        },
        {
          "name": "SECRET_KEY",
          "value": "$(SECRET_KEY)",
          "slotSetting": false
        }
      ]
```

## 🔍 Vérification

Pour vérifier que les variables sont bien configurées :

```powershell
# Lister toutes les variables
az webapp config appsettings list `
  --resource-group seeg-backend-rg `
  --name seeg-backend-api

# Vérifier l'environnement détecté
curl https://seeg-backend-api.azurewebsites.net/api/v1/monitoring/health
```

## 🛡️ Sécurité

⚠️ **NE JAMAIS** :
- Committer le fichier `.env.production` avec des vraies clés
- Utiliser la même SECRET_KEY en dev et prod
- Laisser DEBUG=true en production
- Exposer les credentials de base de données

✅ **TOUJOURS** :
- Utiliser Azure Key Vault pour les secrets sensibles
- Générer des clés uniques avec `openssl rand -hex 32`
- Activer HTTPS Only dans Azure App Service
- Configurer les IP restrictions si nécessaire

## 📊 Monitoring

Les logs seront automatiquement visibles dans :
- **Azure Portal** → **App Service** → **Log stream**
- **Application Insights** (si configuré)
- **Azure Monitor** → **Logs**

## 🚨 Troubleshooting

Si l'API ne démarre pas, vérifiez :

1. **Logs de démarrage** :
```powershell
az webapp log tail `
  --resource-group seeg-backend-rg `
  --name seeg-backend-api
```

2. **Variables d'environnement** :
```powershell
az webapp config appsettings list `
  --resource-group seeg-backend-rg `
  --name seeg-backend-api | ConvertFrom-Json | Format-Table name, value
```

3. **État de l'application** :
```powershell
curl https://seeg-backend-api.azurewebsites.net/api/v1/monitoring/health
```
