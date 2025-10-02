# 📦 Scripts de Déploiement - SEEG-API

Documentation complète des scripts de déploiement disponibles pour **SEEG-API**.

---

## 📋 Table des Matières

- [Scripts PowerShell (.ps1)](#scripts-powershell-ps1)
- [Scripts Bash (.sh)](#scripts-bash-sh)
- [Comparaison des Scripts](#comparaison-des-scripts)
- [Utilisation](#utilisation)
- [Variables d'Environnement](#variables-denvironnement)

---

## 🔷 Scripts PowerShell (.ps1)

### 1. `deploy-production.ps1`

**Description**: Script complet de déploiement en production avec toutes les validations.

**Fonctionnalités**:
- ✅ Validation des prérequis (Azure CLI, Docker)
- ✅ Construction de l'image Docker
- ✅ Push vers Azure Container Registry
- ✅ Configuration de l'App Service
- ✅ Configuration automatique d'Application Insights
- ✅ Redémarrage de l'App Service
- ✅ Tests de santé post-déploiement (30 tentatives)
- ✅ Exécution des migrations de base de données

**Usage**:
```powershell
# Se connecter à Azure
az login

# Exécuter le déploiement complet
.\scripts\deploy-production.ps1
```

**Variables configurables**:
```powershell
$RESOURCE_GROUP = "one-hcm-seeg-rg"
$APP_SERVICE_NAME = "one-hcm-seeg-backend"
$LOCATION = "France Central"
$SKU = "B2"
$CONTAINER_REGISTRY = "onehcmseeg.azurecr.io"
$IMAGE_NAME = "one-hcm-seeg-backend"
```

---

### 2. `deploy-azure.ps1`

**Description**: Script de déploiement complet créant toutes les ressources Azure.

**Fonctionnalités**:
- ✅ Création du Resource Group
- ✅ Création de l'Azure Container Registry
- ✅ Création de l'App Service Plan
- ✅ Création de l'App Service
- ✅ Configuration du Container
- ✅ Configuration automatique d'Application Insights
- ✅ Configuration des variables d'environnement
- ✅ Configuration des logs
- ✅ Configuration du scaling automatique (1-3 instances)

**Usage**:
```powershell
# Se connecter à Azure
az login

# Exécuter le déploiement initial
.\scripts\deploy-azure.ps1
```

**Variables configurables**:
```powershell
$RESOURCE_GROUP = "seeg-backend-rg"
$APP_SERVICE_NAME = "seeg-backend-api"
$LOCATION = "France Central"
$SKU = "B2"
$ACR_NAME = "seegbackend"
$IMAGE_NAME = "seeg-backend"
```

---

### 3. `mise_a_jour.ps1`

**Description**: Script de mise à jour rapide (déploiement continu).

**Fonctionnalités**:
- ✅ Construction de l'image Docker
- ✅ Push vers ACR
- ✅ Mise à jour du container
- ✅ Vérification et configuration d'Application Insights si manquant
- ✅ Redémarrage de l'App Service

**Usage**:
```powershell
# Mise à jour rapide après modification du code
.\scripts\mise_a_jour.ps1
```

**Durée**: ~3-5 minutes

---

### 4. `create-app-insights.ps1`

**Description**: Script pour créer Application Insights et récupérer la connection string.

**Fonctionnalités**:
- ✅ Vérification de la connexion Azure
- ✅ Création du Resource Group si nécessaire
- ✅ Création d'Application Insights
- ✅ Récupération de la connection string
- ✅ Sauvegarde dans `.env.insights`

**Usage**:
```powershell
az login
.\scripts\create-app-insights.ps1
```

---

### 5. `get-app-insights.ps1`

**Description**: Script simplifié pour récupérer la connection string existante.

**Usage**:
```powershell
.\scripts\get-app-insights.ps1
```

---

### 6. `setup-app-insights.ps1`

**Description**: Script complet de configuration Application Insights (création + configuration).

**Usage**:
```powershell
.\scripts\setup-app-insights.ps1
```

---

## 🔶 Scripts Bash (.sh)

### 1. `deploy-production.sh`

**Description**: Équivalent Bash du script PowerShell de déploiement production.

**Usage**:
```bash
# Rendre exécutable
chmod +x scripts/deploy-production.sh

# Se connecter à Azure
az login

# Exécuter le déploiement
./scripts/deploy-production.sh
```

---

### 2. `deploy-azure.sh`

**Description**: Équivalent Bash du script PowerShell de déploiement initial.

**Usage**:
```bash
chmod +x scripts/deploy-azure.sh
az login
./scripts/deploy-azure.sh
```

---

### 3. `mise_a_jour.sh`

**Description**: Équivalent Bash du script PowerShell de mise à jour rapide.

**Usage**:
```bash
chmod +x scripts/mise_a_jour.sh
./scripts/mise_a_jour.sh
```

---

### 4. `setup-app-insights.sh`

**Description**: Équivalent Bash du script PowerShell pour Application Insights.

**Usage**:
```bash
chmod +x scripts/setup-app-insights.sh
./scripts/setup-app-insights.sh
```

---

## 📊 Comparaison des Scripts

| Script | Création Ressources | App Insights | Migrations | Tests Santé | Scaling | Durée |
|--------|---------------------|--------------|------------|-------------|---------|-------|
| `deploy-production` | ❌ | ✅ Auto | ✅ | ✅ | ❌ | ~10-15 min |
| `deploy-azure` | ✅ | ✅ Auto | ❌ | ✅ | ✅ | ~20-30 min |
| `mise_a_jour` | ❌ | ✅ Check | ❌ | ❌ | ❌ | ~3-5 min |
| `create-app-insights` | ⚠️ App Insights | ✅ Création | ❌ | ❌ | ❌ | ~2-3 min |

**Légende**:
- ✅ Inclus
- ❌ Non inclus
- ⚠️ Partiel

---

## 🚀 Utilisation

### Premier Déploiement (Infrastructure complète)

**Windows**:
```powershell
# 1. Se connecter à Azure
az login

# 2. Créer toutes les ressources
.\scripts\deploy-azure.ps1

# 3. Vérifier le déploiement
curl https://seeg-backend-api.azurewebsites.net/health
```

**Linux/Mac**:
```bash
# 1. Se connecter à Azure
az login

# 2. Rendre exécutable et déployer
chmod +x scripts/deploy-azure.sh
./scripts/deploy-azure.sh

# 3. Vérifier le déploiement
curl https://seeg-backend-api.azurewebsites.net/health
```

---

### Déploiement sur Infrastructure Existante

**Windows**:
```powershell
.\scripts\deploy-production.ps1
```

**Linux/Mac**:
```bash
./scripts/deploy-production.sh
```

---

### Mise à Jour Rapide (CI/CD)

**Windows**:
```powershell
# Après modification du code
.\scripts\mise_a_jour.ps1
```

**Linux/Mac**:
```bash
./scripts/mise_a_jour.sh
```

---

### Configuration Application Insights

**Méthode 1 - Script automatique (Windows)**:
```powershell
.\scripts\create-app-insights.ps1
```

**Méthode 2 - Script automatique (Linux/Mac)**:
```bash
chmod +x scripts/setup-app-insights.sh
./scripts/setup-app-insights.sh
```

**Méthode 3 - Récupération existante**:
```powershell
.\scripts\get-app-insights.ps1
```

---

## ⚙️ Variables d'Environnement

### Variables Configurées Automatiquement

Tous les scripts de déploiement configurent automatiquement ces variables:

```bash
# Base de données
DATABASE_URL=postgresql+asyncpg://...

# Sécurité
SECRET_KEY=<généré automatiquement>
ENVIRONMENT=production
DEBUG=false

# Configuration serveur
WORKERS=4
MAX_REQUESTS=1000
TIMEOUT_KEEP_ALIVE=5
WEBSITES_PORT=8000

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=support@seeg-talentsource.com
SMTP_TLS=true

# Application Insights (si disponible)
APPLICATIONINSIGHTS_CONNECTION_STRING=<récupéré automatiquement>
```

---

## 🔧 Personnalisation

### Modifier les Variables

**Dans PowerShell**:
```powershell
# Éditer le script
notepad .\scripts\deploy-production.ps1

# Modifier les variables en haut du fichier
$RESOURCE_GROUP = "votre-resource-group"
$APP_SERVICE_NAME = "votre-app-service"
```

**Dans Bash**:
```bash
# Éditer le script
nano scripts/deploy-production.sh

# Modifier les variables en haut du fichier
RESOURCE_GROUP="votre-resource-group"
APP_SERVICE_NAME="votre-app-service"
```

---

## 🛡️ Sécurité

### Bonnes Pratiques

1. **Ne jamais commiter les credentials**:
   - Les scripts génèrent automatiquement les `SECRET_KEY`
   - Les mots de passe de base de données doivent être dans Azure Key Vault

2. **Utiliser Azure Key Vault** (recommandé):
   ```bash
   # Stocker un secret
   az keyvault secret set \
     --vault-name seeg-vault \
     --name database-password \
     --value "VotreMotDePasse"
   
   # Récupérer dans le script
   DATABASE_PASSWORD=$(az keyvault secret show \
     --vault-name seeg-vault \
     --name database-password \
     --query value -o tsv)
   ```

3. **Rotation des clés**:
   - Les `SECRET_KEY` sont régénérées à chaque déploiement complet
   - Pour éviter la déconnexion des utilisateurs, utilisez `mise_a_jour` au lieu de `deploy-production`

---

## 📋 Logs et Debugging

### Afficher les logs en temps réel

**Azure CLI**:
```bash
# Logs de l'App Service
az webapp log tail \
  --name seeg-backend-api \
  --resource-group seeg-backend-rg

# Logs d'Application Insights (après déploiement)
az monitor app-insights query \
  --app seeg-api-insights \
  --resource-group seeg-rg \
  --analytics-query "traces | order by timestamp desc | limit 100"
```

**Portail Azure**:
1. Ouvrir le portail: https://portal.azure.com
2. Rechercher votre App Service
3. Menu **Monitoring** > **Log stream**

---

## 🔄 Rollback

### Revenir à une version précédente

**Windows**:
```powershell
# Lister les tags disponibles
docker images onehcmseeg.azurecr.io/one-hcm-seeg-backend

# Redéployer une version spécifique
$IMAGE_TAG = "v1.0.0"  # Remplacer par le tag souhaité

az webapp config container set `
  --name one-hcm-seeg-backend `
  --resource-group one-hcm-seeg-rg `
  --docker-custom-image-name "onehcmseeg.azurecr.io/one-hcm-seeg-backend:$IMAGE_TAG"

az webapp restart `
  --name one-hcm-seeg-backend `
  --resource-group one-hcm-seeg-rg
```

**Linux/Mac**:
```bash
# Même procédure en Bash
IMAGE_TAG="v1.0.0"

az webapp config container set \
  --name one-hcm-seeg-backend \
  --resource-group one-hcm-seeg-rg \
  --docker-custom-image-name "onehcmseeg.azurecr.io/one-hcm-seeg-backend:$IMAGE_TAG"

az webapp restart \
  --name one-hcm-seeg-backend \
  --resource-group one-hcm-seeg-rg
```

---

## ❓ FAQ

### Q: Quel script utiliser pour un nouveau projet ?
**R**: Utilisez `deploy-azure.ps1` ou `deploy-azure.sh` pour créer toute l'infrastructure.

### Q: Comment faire une mise à jour rapide ?
**R**: Utilisez `mise_a_jour.ps1` ou `mise_a_jour.sh` pour un déploiement en 3-5 minutes.

### Q: Application Insights n'est pas configuré ?
**R**: Exécutez `create-app-insights.ps1` puis relancez votre script de déploiement.

### Q: Les tests de santé échouent ?
**R**: Attendez 2-3 minutes supplémentaires pour le démarrage complet de l'application.

### Q: Comment voir les logs en temps réel ?
**R**: `az webapp log tail --name <app-name> --resource-group <rg-name>`

### Q: Différence entre PowerShell et Bash ?
**R**: Fonctionnalités identiques, choisissez selon votre OS (Windows = PowerShell, Linux/Mac = Bash).

---

## 📞 Support

Pour toute question ou problème:
1. Consultez les logs: `az webapp log tail`
2. Vérifiez Application Insights: Portal Azure > seeg-api-insights
3. Vérifiez le status: `curl https://<app-name>.azurewebsites.net/health`

---

**Dernière mise à jour**: 2025-10-02  
**Version**: 1.0.0  
**Projet**: SEEG-API - One HCM

