# Backend FastAPI - One HCM SEEG

Backend API pour le système de gestion RH One HCM SEEG, développé avec FastAPI et PostgreSQL.

## 🌐 Frontend de Production

Le frontend est déployé sur : **https://www.seeg-talentsource.com/**

## 🚀 Démarrage Rapide

### Prérequis

- Python 3.11+
- PostgreSQL (Azure Database)
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

## 🐳 Déploiement avec Docker

### Développement
```bash
docker-compose up -d
```

### Production
```bash
docker build -t seeg-backend .
docker run -p 8000:8000 --env-file .env.production seeg-backend
```

## ☁️ Déploiement sur Azure

### Option 1 : Script automatique
```bash
./deploy-azure.sh
```

### Option 2 : Manuel
1. Créer un App Service sur Azure
2. Configurer les variables d'environnement
3. Déployer le code via GitHub Actions ou Azure CLI

## 🔧 Configuration

### Variables d'environnement importantes

```env
# Base de données
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db

# Sécurité
SECRET_KEY=your-secret-key
ALLOWED_ORIGINS=["https://www.seeg-talentsource.com"]

# Email
SMTP_HOST=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

## 🧪 Tests

```bash
# Tests unitaires
pytest

# Tests avec couverture
pytest --cov=app

# Tests d'intégration
pytest tests/integration/

# Tests Azure
pytest tests/test_azure_*.py -v

# Tous les tests
python run_all_tests.py
```

### Couverture de tests

Le projet vise une couverture de tests de 80%+ avec :
- Tests d'API pour tous les endpoints
- Tests de services pour la logique métier
- Tests d'authentification et de sécurité
- Tests d'intégration end-to-end
- Tests des utilitaires et validations

## 📊 Monitoring

- **Logs** : Structlog avec format JSON
- **Métriques** : Prometheus (optionnel)
- **Erreurs** : Sentry (optionnel)

### Logs importants

- Upload de documents
- Erreurs de validation
- Suppression de documents
- Accès aux documents

### Métriques

- Nombre de documents par type
- Taille moyenne des fichiers
- Taux d'erreur d'upload
- Temps de réponse des endpoints

## 🔒 Sécurité

- Authentification JWT
- Validation des données avec Pydantic
- CORS configuré pour le domaine de production
- Rate limiting
- Hachage des mots de passe avec bcrypt
- Validation stricte des fichiers PDF

## 🐛 Dépannage

### Erreurs courantes

1. **"Seuls les fichiers PDF sont acceptés"**
   - Vérifier l'extension du fichier
   - Vérifier le contenu (magic number)

2. **"Le fichier n'est pas un PDF valide"**
   - Fichier corrompu
   - Format non-PDF

3. **"Candidature non trouvée"**
   - Vérifier l'ID de candidature
   - Vérifier les droits d'accès

### Solutions

- Vérifier les logs de l'application
- Tester avec un PDF valide
- Vérifier les permissions de l'utilisateur
- Contacter l'administrateur système

## 📞 Support

Pour toute question ou problème :
- Email : dev@seeg.ga
- Documentation : https://www.seeg-talentsource.com/docs
- API Documentation : http://localhost:8000/docs

## 📄 Licence

Propriétaire - SEEG

## 🚀 Commandes utiles

```bash
# Démarrer le serveur
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

# Redémarrer le serveur
pkill -f uvicorn && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001

# Tests avec la base Azure
pytest tests/test_azure_*.py -v

# Migration
alembic upgrade head

# Vérifier la structure des tables
python -c "from app.db.database import get_async_db; from app.models.application import ApplicationDocument; import asyncio; asyncio.run([db.execute(select(ApplicationDocument).limit(1)) for db in get_async_db()])"
```
