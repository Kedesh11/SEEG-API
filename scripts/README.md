# 📦 Scripts de Déploiement SEEG-API

Scripts automatisés pour déployer l'API SEEG sur Azure.

---

## 🚀 Démarrage Rapide

### Windows (PowerShell)

```powershell
# Premier déploiement (crée toutes les ressources)
az login
.\scripts\deploy-azure.ps1

# Mise à jour rapide
.\scripts\mise_a_jour.ps1

# Configuration Application Insights
.\scripts\create-app-insights.ps1
```

### Linux/Mac (Bash)

```bash
# Premier déploiement (crée toutes les ressources)
az login
chmod +x scripts/deploy-azure.sh
./scripts/deploy-azure.sh

# Mise à jour rapide
chmod +x scripts/mise_a_jour.sh
./scripts/mise_a_jour.sh

# Configuration Application Insights
chmod +x scripts/setup-app-insights.sh
./scripts/setup-app-insights.sh
```

---

## 📋 Liste des Scripts

### PowerShell (.ps1) - Pour Windows

| Script | Description | Durée | Usage |
|--------|-------------|-------|-------|
| `deploy-azure.ps1` | Déploiement complet (crée infrastructure) | 20-30 min | Premier déploiement |
| `deploy-production.ps1` | Déploiement sur infra existante | 10-15 min | Redéploiement complet |
| `mise_a_jour.ps1` | Mise à jour rapide (CI/CD) | 3-5 min | Mise à jour quotidienne |
| `create-app-insights.ps1` | Créer Application Insights | 2-3 min | Configuration monitoring |
| `get-app-insights.ps1` | Récupérer connection string | <1 min | Récupération config |
| `setup-app-insights.ps1` | Setup complet App Insights | 2-3 min | Configuration complète |

### Bash (.sh) - Pour Linux/Mac

| Script | Description | Durée | Usage |
|--------|-------------|-------|-------|
| `deploy-azure.sh` | Déploiement complet (crée infrastructure) | 20-30 min | Premier déploiement |
| `deploy-production.sh` | Déploiement sur infra existante | 10-15 min | Redéploiement complet |
| `mise_a_jour.sh` | Mise à jour rapide (CI/CD) | 3-5 min | Mise à jour quotidienne |
| `setup-app-insights.sh` | Setup complet App Insights | 2-3 min | Configuration monitoring |

---

## 🎯 Cas d'Usage

### Scénario 1: Nouveau Projet (Première Fois)

```powershell
# Windows
az login
.\scripts\deploy-azure.ps1
.\scripts\create-app-insights.ps1
```

```bash
# Linux/Mac
az login
chmod +x scripts/deploy-azure.sh scripts/setup-app-insights.sh
./scripts/deploy-azure.sh
./scripts/setup-app-insights.sh
```

**Résultat**: Infrastructure complète créée avec monitoring.

---

### Scénario 2: Mise à Jour du Code

```powershell
# Windows - Après modification du code
.\scripts\mise_a_jour.ps1
```

```bash
# Linux/Mac - Après modification du code
./scripts/mise_a_jour.sh
```

**Résultat**: Nouvelle version déployée en 3-5 minutes.

---

### Scénario 3: Redéploiement Complet

```powershell
# Windows - Infrastructure existe déjà
.\scripts\deploy-production.ps1
```

```bash
# Linux/Mac - Infrastructure existe déjà
./scripts/deploy-production.sh
```

**Résultat**: Application redéployée avec tests de santé.

---

## ⚙️ Pré-requis

### Outils Nécessaires

- ✅ **Azure CLI** ([Installation](https://docs.microsoft.com/cli/azure/install-azure-cli))
- ✅ **Docker** ([Installation](https://docs.docker.com/get-docker/))
- ✅ **Git** (optionnel, pour versioning)

### Vérification

```bash
# Vérifier Azure CLI
az --version

# Vérifier Docker
docker --version

# Se connecter à Azure
az login
```

---

## 🔧 Configuration

### Variables à Personnaliser

**Pour `deploy-production`**:
```powershell
# Ouvrir le script et modifier:
$RESOURCE_GROUP = "votre-resource-group"
$APP_SERVICE_NAME = "votre-app-service"
$CONTAINER_REGISTRY = "votre-registry.azurecr.io"
```

**Pour `deploy-azure`**:
```powershell
# Ouvrir le script et modifier:
$RESOURCE_GROUP = "seeg-backend-rg"
$APP_SERVICE_NAME = "seeg-backend-api"
$LOCATION = "France Central"
$SKU = "B2"  # Taille de l'instance
```

---

## 📊 Comparaison des Scripts

| Fonctionnalité | deploy-azure | deploy-production | mise_a_jour |
|----------------|--------------|-------------------|-------------|
| Crée Resource Group | ✅ | ❌ | ❌ |
| Crée ACR | ✅ | ❌ | ❌ |
| Crée App Service | ✅ | ❌ | ❌ |
| Build Docker | ✅ | ✅ | ✅ |
| Push vers ACR | ✅ | ✅ | ✅ |
| Configure App Insights | ✅ | ✅ | ✅ (vérif) |
| Tests de santé | ✅ | ✅ | ❌ |
| Migrations DB | ❌ | ✅ | ❌ |
| Scaling auto | ✅ | ❌ | ❌ |

---

## 🛡️ Sécurité

### Bonnes Pratiques

1. **Ne jamais commiter les credentials**
   - Les scripts génèrent automatiquement les `SECRET_KEY`
   - Utilisez Azure Key Vault pour les mots de passe

2. **Logs et Monitoring**
   - Application Insights configuré automatiquement
   - Logs disponibles via `az webapp log tail`

3. **Rollback Rapide**
   ```bash
   # Revenir à une version précédente
   docker images  # Lister les versions
   # Puis redéployer avec le tag souhaité
   ```

---

## 📝 Logs et Debugging

### Voir les Logs en Temps Réel

```bash
# Logs de l'application
az webapp log tail --name seeg-backend-api --resource-group seeg-backend-rg

# Logs Application Insights
az monitor app-insights query \
  --app seeg-api-insights \
  --resource-group seeg-rg \
  --analytics-query "traces | limit 100"
```

### Tests de Santé

```bash
# Vérifier le health endpoint
curl https://seeg-backend-api.azurewebsites.net/health

# Vérifier l'API
curl https://seeg-backend-api.azurewebsites.net/docs
```

---

## 🔄 Workflow CI/CD Recommandé

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Azure

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      - name: Deploy
        run: .\scripts\mise_a_jour.ps1
```

### Déploiement Manuel

```bash
# Développement local -> Staging
git push origin develop
# Déclenche automatiquement mise_a_jour.ps1

# Staging -> Production
git push origin main
# Déclenche automatiquement deploy-production.ps1
```

---

## ❓ FAQ

**Q: Quel script pour un nouveau projet ?**  
R: Utilisez `deploy-azure.ps1` (Windows) ou `deploy-azure.sh` (Linux/Mac)

**Q: Comment faire une mise à jour rapide ?**  
R: Utilisez `mise_a_jour.ps1` ou `mise_a_jour.sh`

**Q: Les tests de santé échouent ?**  
R: Attendez 2-3 minutes supplémentaires, l'application peut mettre du temps à démarrer

**Q: Application Insights ne fonctionne pas ?**  
R: Exécutez `create-app-insights.ps1` puis relancez le déploiement

**Q: Comment voir les coûts Azure ?**  
R: Portal Azure > Cost Management > Cost Analysis

**Q: Puis-je utiliser un autre cloud provider ?**  
R: Les scripts sont spécifiques à Azure, mais peuvent être adaptés pour AWS/GCP

---

## 📞 Support

- **Documentation complète**: [docs/SCRIPTS_DEPLOYMENT.md](../docs/SCRIPTS_DEPLOYMENT.md)
- **Application Insights**: [docs/APPLICATION_INSIGHTS.md](../docs/APPLICATION_INSIGHTS.md)
- **Guide démarrage**: [docs/QUICKSTART.md](../docs/QUICKSTART.md)

---

## 📦 Structure des Fichiers

```
scripts/
├── README.md                    # Ce fichier
├── deploy-azure.ps1            # Déploiement complet (Windows)
├── deploy-azure.sh             # Déploiement complet (Linux)
├── deploy-production.ps1       # Déploiement app (Windows)
├── deploy-production.sh        # Déploiement app (Linux)
├── mise_a_jour.ps1            # Mise à jour rapide (Windows)
├── mise_a_jour.sh             # Mise à jour rapide (Linux)
├── create-app-insights.ps1    # Créer App Insights (Windows)
├── get-app-insights.ps1       # Récupérer config (Windows)
├── setup-app-insights.ps1     # Setup complet (Windows)
└── setup-app-insights.sh      # Setup complet (Linux)
```

---

**Dernière mise à jour**: 2025-10-02  
**Version**: 1.0.0  
**Mainteneur**: Sevan Kedesh IKISSA

