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

### Évaluations
- `POST /api/v1/evaluations/protocol1` - Évaluation Protocol 1
- `POST /api/v1/evaluations/protocol2` - Évaluation Protocol 2

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
```

## 📊 Monitoring

- **Logs** : Structlog avec format JSON
- **Métriques** : Prometheus (optionnel)
- **Erreurs** : Sentry (optionnel)

## 🔒 Sécurité

- Authentification JWT
- Validation des données avec Pydantic
- CORS configuré pour le domaine de production
- Rate limiting
- Hachage des mots de passe avec bcrypt

## 📞 Support

Pour toute question ou problème :
- Email : dev@seeg.ga
- Documentation : https://www.seeg-talentsource.com/docs

## 📄 Licence

Propriétaire - SEEG

python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
pkill -f uvicorn && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001