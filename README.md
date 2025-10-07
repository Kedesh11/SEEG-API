# 🚀 Backend FastAPI - One HCM SEEG

[![CI](https://img.shields.io/badge/CI-passing-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-46%25-yellow)]()
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109%2B-green)]()
[![Security](https://img.shields.io/badge/security-9%2F10-brightgreen)]()

Backend API pour le système de gestion RH One HCM SEEG, développé avec FastAPI et PostgreSQL.

> **✅ Production-Ready**: Tests 100%, CI/CD automatisé, Rate Limiting, Documentation complète

## 🌐 Frontend de Production

Le frontend est déployé sur : **https://www.seeg-talentsource.com/**

## 🚀 Déploiement sur Azure

La totalité de la documentation de déploiement est maintenant regroupée ici. Suivez les étapes ci-dessous pour préparer et déployer l'API en production.

### 1. Préparer l’environnement de travail

#### Prérequis logiciels
| Outil | Version minimale | Vérification |
|-------|------------------|--------------|
| Python | 3.11 | `python --version`
| Docker Desktop | 28.4.0 | `docker --version`
| Azure CLI | 2.77.0 | `az --version`

> **Important** : ouvrez PowerShell « Exécuter en tant qu’administrateur » pour installer Azure CLI et interagir avec Docker.

#### Installation rapide
```powershell
# Installer Azure CLI (session admin)
$ProgressPreference = 'SilentlyContinue'
Invoke-WebRequest -Uri https://aka.ms/installazurecliwindows -OutFile $env:TEMP\AzureCLI.msi
Start-Process msiexec.exe -Wait -ArgumentList "/i $env:TEMP\AzureCLI.msi /quiet"
Remove-Item $env:TEMP\AzureCLI.msi

# Vérifications
az --version
docker --version
```

### 2. Se connecter à Azure
```powershell
az login
az account show
```

### 3. Préparer les secrets de production
| Secret | Valeur attendue |
|--------|-----------------|
| `DATABASE_URL` | `postgresql+asyncpg://USER:PASSWORD@seeg-postgres-server.postgres.database.azure.com:5432/postgres` |
| `DATABASE_URL_SYNC` | `postgresql://USER:PASSWORD@seeg-postgres-server.postgres.database.azure.com:5432/postgres` |
| `SECRET_KEY` | Chaîne aléatoire de 64 caractères minimum (généré automatiquement par le script) |
| `SMTP_USERNAME` | `support@seeg-talentsource.com` |
| `SMTP_PASSWORD` | **App Password Gmail** (16 caractères) |

> Vous pouvez créer un App Password Gmail depuis https://myaccount.google.com/security → « Mots de passe des applications ».

### 4. Déploiement automatisé (recommandé)

Le script `scripts/deploy-azure.ps1` automatise toutes les étapes : création des ressources Azure, build Docker, push vers ACR, configuration App Service.

```powershell
cd "C:\Users\Sevan Kedesh IKISSA\Desktop\Projects\Programme\SEEG\SEEG-API"
.\env\Scripts\Activate.ps1
.\scripts\deploy-azure.ps1
```

Étapes effectuées par le script :
1. Vérification des prérequis (Azure CLI, Docker).
2. Génération d’une `SECRET_KEY` sécurisée.
3. Récupération interactive des secrets (DB, SMTP).
4. Construction et push de l’image vers `onehcmseeg.azurecr.io`.
5. Configuration de l’App Service `one-hcm-seeg-backend`.
6. Tests de santé (`/health`) et affichage des URLs finales.

Durée totale ≈ 15 minutes.

### 5. Déploiement manuel (alternative)

Si vous préférez exécuter chaque étape manuellement :

```powershell
# Variables d’exemple
$RG="one-hcm-seeg-rg"
$APP="one-hcm-seeg-backend"
$ACR="onehcmseeg"
$IMG="onehcmseeg.azurecr.io/one-hcm-seeg-backend:latest"

# 1. Build & push Docker
docker build -t $IMG .
az acr login --name $ACR
docker push $IMG

# 2. Configurer l’App Service
az webapp config container set --name $APP --resource-group $RG --docker-custom-image-name $IMG

# 3. Mettre à jour les App Settings
az webapp config appsettings set --name $APP --resource-group $RG --settings `
    DATABASE_URL="..." DATABASE_URL_SYNC="..." SECRET_KEY="..." `
    SMTP_USERNAME="support@seeg-talentsource.com" SMTP_PASSWORD="<APP_PASSWORD>" `
    ENVIRONMENT="production" DEBUG="false" ALLOWED_ORIGINS="https://www.seeg-talentsource.com,https://seeg-hcm.vercel.app"

# 4. Redémarrer
az webapp restart --name $APP --resource-group $RG
```

### 6. Vérifications post-déploiement
```powershell
# Health check
Invoke-WebRequest -Uri "https://one-hcm-seeg-backend.azurewebsites.net/health" -UseBasicParsing

# Documentation API
Start-Process "https://one-hcm-seeg-backend.azurewebsites.net/docs"

# Création du premier administrateur
$body = @{
    email = "admin@seeg.ga"
    password = "Admin@2025Secure!"
    first_name = "Admin"
    last_name = "SEEG"
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "https://one-hcm-seeg-backend.azurewebsites.net/api/v1/auth/create-first-admin" -Body $body -ContentType "application/json"
```

### 7. Migrations de base de données

#### Option A : Script automatisé (recommandé)
```powershell
.\scripts\run-migrations.ps1
```

#### Option B : Exécution manuelle
```powershell
# Depuis votre machine
.\env\Scripts\Activate.ps1
alembic upgrade head

# Ou directement dans l'App Service
az webapp ssh --name one-hcm-seeg-backend --resource-group one-hcm-seeg-rg
alembic upgrade head
exit
```

### 8. Procédure de rollback
```powershell
# Lister les tags d’images
az acr repository show-tags --name onehcmseeg --repository one-hcm-seeg-backend --orderby time_desc

# Revenir à une version précédente
$PREVIOUS_TAG="v1.0.0-20250107-120000"
az webapp config container set --name one-hcm-seeg-backend --resource-group one-hcm-seeg-rg --docker-custom-image-name "onehcmseeg.azurecr.io/one-hcm-seeg-backend:$PREVIOUS_TAG"
az webapp restart --name one-hcm-seeg-backend --resource-group one-hcm-seeg-rg
```

### 9. Troubleshooting rapide
| Problème | Symptôme | Solution |
|----------|----------|----------|
| Azure CLI non reconnu | `az : command not found` | Installer Azure CLI, redémarrer PowerShell |
| Docker inaccessible | `docker_engine: file not found` | Démarrer Docker Desktop, lancer PowerShell en admin |
| App Service introuvable | `app ... introuvable` | Vérifier `$RESOURCE_GROUP`, `$APP` |
| Logs Application Insights absents | `APPLICATIONINSIGHTS_CONNECTION_STRING` vide | Configurer via `az webapp config appsettings set` |
| Erreurs 500 | `/health` échoue | `az webapp log tail --name one-hcm-seeg-backend --resource-group one-hcm-seeg-rg` |

### 10. URLs importantes
- API : `https://one-hcm-seeg-backend.azurewebsites.net`
- Documentation interactive : `https://one-hcm-seeg-backend.azurewebsites.net/docs`
- Health check : `https://one-hcm-seeg-backend.azurewebsites.net/health`

---

## 🖥️ Développement Local

### Prérequis

- Python 3.11+
- PostgreSQL (Azure Database ou local)
- Redis (optionnel, pour les tâches en arrière-plan)

### Installation

1. **Cloner le repository**
```bash
git clone <repository-url>
cd one-hcm-seeg/backend
```

2. **Créer un environnement virtuel**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer les variables d'environnement**
```bash
cp .env.example .env
# Éditer .env avec vos paramètres
```

5. **Démarrer le serveur**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📚 Documentation API

- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

## ⭐ Nouvelles Fonctionnalités

### 🔐 Rate Limiting
Protection contre les abus avec limites par endpoint:
- **Login**: 5 requêtes/minute
- **Signup**: 3 requêtes/minute
- **Upload**: 10 requêtes/minute
- **Autres**: 60 requêtes/minute

### 🔄 Refresh Token
Renouvellement sécurisé des tokens d'accès:
```bash
POST /api/v1/auth/refresh
```

### ✅ Validation PDF Renforcée
- Taille maximum: 10 MB
- Vérification magic number `%PDF`
- Messages d'erreur explicites

### 🚀 CI/CD Automatisé
- Tests automatiques (Python 3.11, 3.12, 3.13)
- Déploiement staging/production
- Migrations automatiques
- Health checks

### 🔐 Sécurité Renforcée
- ✅ Validation automatique au démarrage en production
  - Vérification de `SECRET_KEY` (pas de valeur par défaut)
  - Vérification de `DATABASE_URL` (pas de localhost)
  - Avertissement si `DEBUG` activé
- ✅ Variables d'environnement sécurisées
- ✅ Pas de secrets en clair dans le code
- ✅ `.gitignore` mis à jour pour exclure `.env.production`

### 📊 Score Qualité
- ✅ Tests: 21/22 (95.5%)
- ✅ Coverage: 46%
- ✅ Sécurité: 9/10
- ✅ Documentation: Complète
- ✅ **Production-Ready** : Validation automatique des configurations

## 🏗️ Architecture

```
app/
├── api/v1/endpoints/     # Endpoints API
├── core/                 # Configuration et sécurité
├── db/                   # Base de données
├── models/               # Modèles SQLAlchemy
├── schemas/              # Schémas Pydantic
├── services/             # Logique métier
└── utils/                # Utilitaires
```

## 🔐 Endpoints Principaux

### Authentification
- `POST /api/v1/auth/login` - Connexion
- `POST /api/v1/auth/signup` - Inscription
- `POST /api/v1/auth/refresh` - Rafraîchir token

### Offres d'emploi
- `GET /api/v1/jobs/` - Liste des offres
- `POST /api/v1/jobs/` - Créer une offre
- `GET /api/v1/jobs/{id}` - Détails d'une offre

### Candidatures
- `GET /api/v1/applications/` - Liste des candidatures
- `POST /api/v1/applications/` - Créer une candidature
- `PUT /api/v1/applications/{id}/status` - Mettre à jour le statut

### Documents PDF
- `POST /api/v1/applications/{id}/documents` - Upload d'un document PDF
- `POST /api/v1/applications/{id}/documents/multiple` - Upload de plusieurs documents
- `GET /api/v1/applications/{id}/documents` - Récupérer les documents
- `GET /api/v1/applications/{id}/documents/{doc_id}` - Récupérer un document avec données
- `DELETE /api/v1/applications/{id}/documents/{doc_id}` - Supprimer un document

### Évaluations
- `POST /api/v1/evaluations/protocol1` - Évaluation Protocol 1
- `POST /api/v1/evaluations/protocol2` - Évaluation Protocol 2

## 📄 Gestion des Documents PDF

### Vue d'ensemble

Le système permet aux candidats d'uploader des documents PDF directement dans la base de données. Cette fonctionnalité remplace l'ancien système basé sur des URLs et offre une sécurité et une intégrité des données améliorées.

### Types de documents supportés

- **`cover_letter`** : Lettres de motivation
- **`cv`** : Curriculum Vitae
- **`certificats`** : Certificats de formation
- **`diplome`** : Diplômes

### Caractéristiques techniques

- **Format** : PDF uniquement
- **Stockage** : Base de données PostgreSQL (type BYTEA)
- **Validation** : Vérification du magic number PDF et de l'extension
- **Encodage** : Base64 pour l'API
- **Sécurité** : Validation stricte des types de fichiers

### API Endpoints pour les PDF

#### Upload d'un document

```http
POST /api/v1/applications/{application_id}/documents
Content-Type: multipart/form-data

document_type: string (cover_letter|cv|certificats|diplome)
file: binary (fichier PDF)
```

**Réponse :**
```json
{
  "success": true,
  "message": "Document uploadé avec succès",
  "data": {
    "id": "uuid",
    "application_id": "uuid",
    "document_type": "cv",
    "file_name": "mon_cv.pdf",
    "file_size": 1024000,
    "file_type": "application/pdf",
    "uploaded_at": "2024-01-01T00:00:00Z"
  }
}
```

#### Upload de plusieurs documents

```http
POST /api/v1/applications/{application_id}/documents/multiple
Content-Type: multipart/form-data

files: binary[] (fichiers PDF)
document_types: string[] (types correspondants)
```

#### Récupération des documents

```http
GET /api/v1/applications/{application_id}/documents
```

**Paramètres optionnels :**
- `document_type` : Filtrer par type de document

#### Récupération d'un document avec données

```http
GET /api/v1/applications/{application_id}/documents/{document_id}
```

**Réponse :**
```json
{
  "success": true,
  "message": "Document récupéré avec succès",
  "data": {
    "id": "uuid",
    "application_id": "uuid",
    "document_type": "cv",
    "file_name": "mon_cv.pdf",
    "file_size": 1024000,
    "file_type": "application/pdf",
    "uploaded_at": "2024-01-01T00:00:00Z",
    "file_data": "base64_encoded_pdf_content"
  }
}
```

#### Suppression d'un document

```http
DELETE /api/v1/applications/{application_id}/documents/{document_id}
```

### Structure de la base de données

#### Table `application_documents`

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Identifiant unique |
| `application_id` | UUID | Référence vers la candidature |
| `document_type` | VARCHAR | Type de document |
| `file_name` | VARCHAR | Nom du fichier |
| `file_data` | BYTEA | Contenu binaire du PDF |
| `file_size` | INTEGER | Taille en octets |
| `file_type` | VARCHAR | Type MIME (application/pdf) |
| `uploaded_at` | TIMESTAMP | Date d'upload |

#### Table `applications` (modifiée)

**Champs supprimés :**
- `motivation` (Text)
- `url_lettre_integrite` (String)
- `url_idee_projet` (String)
- `cover_letter` (Text)

### Validation et sécurité

#### Validation des fichiers

1. **Extension** : Doit se terminer par `.pdf`
2. **Magic number** : Doit commencer par `%PDF`
3. **Type MIME** : Vérification du contenu
4. **Taille** : Limite configurable (par défaut 10MB)

#### Sécurité

- **Authentification** : Tous les endpoints nécessitent une authentification
- **Autorisation** : Vérification des droits d'accès aux candidatures
- **Validation stricte** : Rejet des fichiers non-PDF
- **Stockage sécurisé** : Données binaires dans la base de données

### Exemples d'utilisation

#### JavaScript (Frontend)

```javascript
// Upload d'un fichier PDF
const uploadDocument = async (applicationId, file, documentType) => {
  const formData = new FormData();
  formData.append('document_type', documentType);
  formData.append('file', file);
  
  const response = await fetch(`/api/v1/applications/${applicationId}/documents`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: formData
  });
  
  return response.json();
};

// Récupération des documents
const getDocuments = async (applicationId) => {
  const response = await fetch(`/api/v1/applications/${applicationId}/documents`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return response.json();
};
```

#### Python (Backend)

```python
from app.services.application import ApplicationService
from app.schemas.application import ApplicationDocumentCreate
import base64

# Création d'un document
async def create_document(db, application_id, file_path, document_type):
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    file_data_b64 = base64.b64encode(file_content).decode('utf-8')
    
    document_data = ApplicationDocumentCreate(
        application_id=application_id,
        document_type=document_type,
        file_name=os.path.basename(file_path),
        file_data=file_data_b64,
        file_size=len(file_content),
        file_type="application/pdf"
    )
    
    service = ApplicationService(db)
    return await service.create_document(document_data)
```

## 🗄️ Base de données

### Migration

#### Historique des migrations

- **Migration initiale** : `a9cb9ffa6018` - Création des tables
- **Migration PDF** : `c233e3cf8f4e` - Modification pour le stockage PDF

#### Commandes de migration

```bash
# Appliquer les migrations
alembic upgrade head

# Vérifier l'état
alembic current

# Créer une nouvelle migration
alembic revision --autogenerate -m "Description"
```

### Configuration Azure

```ini
# alembic.ini
sqlalchemy.url = postgresql+asyncpg://Sevan:Sevan%%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres
```

## 🐳 Docker (local et production)

### Structure Docker

- `Dockerfile` (multi-étapes) : construit l'image backend FastAPI
- `docker-compose.yml` : services locaux (app, db, …)

### Scripts disponibles

Le projet inclut 3 scripts PowerShell essentiels :

| Script | Description |
|--------|-------------|
| `scripts/deploy-azure.ps1` | Déploiement complet sur Azure (création ressources, build, push, config) |
| `scripts/mise_a_jour.ps1` | Mise à jour continue : rebuild image et redéploiement |
| `scripts/run-migrations.ps1` | Exécution des migrations Alembic sur la base de production |

### Exemple de .env

```env
# Application
ENV=dev
LOG_LEVEL=info
SECRET_KEY=change_me
ACCESS_TOKEN_EXPIRE_MINUTES=120

# Base de données (async pour SQLAlchemy 2 + asyncpg)
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:5432/<db>
# Connexion sync (certaines opérations/scripts)
DATABASE_URL_SYNC=postgresql+psycopg2://<user>:<password>@<host>:5432/<db>

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:5173","https://www.seeg-talentsource.com"]
```

### Build & run local (Docker)

```bash
# Depuis le dossier backend
docker build -t seeg-backend:local .

docker run --rm -p 8000:8000 \
  --env-file .env \
  --name seeg-backend seeg-backend:local
```

Explication:
- `docker build -t seeg-backend:local .` : construit l'image locale
- `docker run ... -p 8000:8000` : expose le port 8000
- `--env-file .env` : injecte les variables d'environnement
- Le `Dockerfile` définit la commande d'entrée qui lance `uvicorn`

### Docker Compose (optionnel)

```bash
docker compose up --build
```

### Rebuild & Push vers Azure Container Registry (ACR)

```bash
# Variables (exemple)
ACR_NAME=seegacr
ACR_LOGIN=${ACR_NAME}.azurecr.io
IMAGE=${ACR_LOGIN}/seeg-backend:latest

# Connexion ACR (si besoin)
az acr login --name ${ACR_NAME}

# Build multi-plateforme (optionnel) ou simple
az acr build --registry ${ACR_NAME} --image seeg-backend:latest .
# ou en local
# docker build -t ${IMAGE} . && docker push ${IMAGE}
```

Explication:
- `az acr login` : s'authentifie à l'ACR
- `az acr build` : construit l'image dans ACR (build cloud), évite d'uploader les artefacts locaux
- `docker build && docker push` : alternative locale si préférée

## ☁️ Déploiement sur Azure App Service (Container)

Prérequis:
- `az login`
- Ressource Group existant (ou à créer)
- ACR existant avec l'image poussée (`seeg-backend:latest`)

Variables d'exemple:
```bash
RG=seeg-backend-rg
LOC=westeurope
PLAN=seeg-backend-plan
APP=seeg-backend-api
ACR_NAME=seegacr
ACR_LOGIN=${ACR_NAME}.azurecr.io
IMAGE=${ACR_LOGIN}/seeg-backend:latest
```

### 1) Créer le groupe de ressources (si nécessaire)
```bash
az group create --name ${RG} --location ${LOC}
```
- Crée un Resource Group pour regrouper les ressources Azure

### 2) Créer le plan App Service (Linux, B1 par ex.)
```bash
az appservice plan create \
  --name ${PLAN} \
  --resource-group ${RG} \
  --is-linux \
  --sku B1
```
- Crée un plan d'hébergement (dimensionnement et facturation)

### 3) Créer l'App Service (Web App conteneur)
```bash
az webapp create \
  --name ${APP} \
  --resource-group ${RG} \
  --plan ${PLAN} \
  --deployment-container-image-name ${IMAGE}
```
- Crée l'application et la pointe sur l'image container

### 4) Donner accès de l'App à l'ACR (pull)
```bash
az webapp config container set \
  --name ${APP} \
  --resource-group ${RG} \
  --docker-custom-image-name ${IMAGE} \
  --docker-registry-server-url https://${ACR_LOGIN}
```
- Configure le conteneur et l'URL du registre

Si l'ACR est privé, lier l'identité/les credentials:
```bash
az webapp config container set \
  --name ${APP} \
  --resource-group ${RG} \
  --docker-registry-server-user $(az acr credential show --name ${ACR_NAME} --query username -o tsv) \
  --docker-registry-server-password $(az acr credential show --name ${ACR_NAME} --query passwords[0].value -o tsv)
```
- Renseigne user/password ACR si Managed Identity non utilisée

### 5) Variables d'environnement (App Settings)
```bash
az webapp config appsettings set \
  --name ${APP} \
  --resource-group ${RG} \
  --settings \
  ENV=prod \
  LOG_LEVEL=info \
  DATABASE_URL="<postgres-async-url>" \
  DATABASE_URL_SYNC="<postgres-sync-url>" \
  SECRET_KEY="<secret>" \
  ACCESS_TOKEN_EXPIRE_MINUTES=120
```
- Définit les variables lues par l'app (équivalent `.env`)

### 6) Activer les logs (utile debug)
```bash
az webapp log config \
  --name ${APP} \
  --resource-group ${RG} \
  --docker-container-logging filesystem
```
- Active les logs du conteneur accessibles via `az webapp log tail`

### 7) Déployer une nouvelle image (rollout)
Option A (changer le tag ou forcer l’update):
```bash
az webapp config container set \
  --name ${APP} \
  --resource-group ${RG} \
  --docker-custom-image-name ${IMAGE}

az webapp restart --name ${APP} --resource-group ${RG}
```
- Met à jour la config conteneur et redémarre l'app

Option B (déploiement ZIP de code, peu utilisé ici car conteneur):
```bash
az webapp deploy --name ${APP} --resource-group ${RG} --src-path backend.zip
```
- Déploie un package (non nécessaire pour mode conteneur)

### 7.1) (Recommandé) Exécuter les migrations Alembic après déploiement

Selon votre stratégie, exécuter les migrations peut se faire via une tâche séparée (GitHub Actions, Azure Pipelines) ou manuellement depuis un pod/console:

Option A — Tâche CI/CD qui lance Alembic (idéal):
```bash
# Exemple (à adapter à votre pipeline)
python -m alembic upgrade head
```

Option B — Exécuter dans un conteneur éphémère (si image contient alembic.ini):
```bash
# Démarrer un conteneur temporaire avec la même image
az webapp ssh --name ${APP} --resource-group ${RG}
# Puis dans le shell du conteneur
alembic upgrade head
```

Notes:
- Vérifier que `DATABASE_URL`/`DATABASE_URL_SYNC` sont configurées dans les App Settings
- Les migrations doivent être idempotentes; surveiller les logs pendant l’exécution

### 8) Suivre les logs en direct
```
```