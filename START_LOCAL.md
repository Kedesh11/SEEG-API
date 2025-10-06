# 🚀 Guide de démarrage - Base de données locale

## ✅ Configuration effectuée

### Base de données PostgreSQL locale
- **Serveur**: localhost
- **Port**: 5432
- **Base**: recruteur
- **User**: postgres
- **Password**: 4 espaces

### Tables créées (13)
✓ users
✓ job_offers
✓ applications
✓ application_documents
✓ application_drafts
✓ application_history
✓ candidate_profiles
✓ email_logs
✓ interview_slots
✓ notifications
✓ protocol1_evaluations
✓ protocol2_evaluations
✓ seeg_agents

### Données de test insérées

#### Comptes utilisateurs
1. **Admin**
   - Email: `sevankedesh11@gmail.com`
   - Password: `Sevan@Seeg`
   - Rôle: admin

2. **Recruteur**
   - Email: `recruteur@test.local`
   - Password: `Recrut3ur#2025`
   - Rôle: recruiter

3. **Candidat**
   - Email: `candidate@test.local`
   - Password: `Password#2025`
   - Rôle: candidate

#### Données de test
- ✓ 1 offre d'emploi (Ingénieur Systèmes)
- ✓ 1 candidature
- ✓ 1 profil candidat

## 🚀 Démarrage de l'API

### Étape 1: Activer l'environnement virtuel
```powershell
.\env\Scripts\activate
```

### Étape 2: Démarrer le serveur
```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Étape 3: Accéder à l'API
- **API**: http://localhost:8000
- **Documentation Swagger**: http://localhost:8000/docs
- **Documentation ReDoc**: http://localhost:8000/redoc

## 🧪 Tester l'API

### Test de connexion admin
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "sevankedesh11@gmail.com", "password": "Sevan@Seeg"}'
```

### Obtenir la liste des offres d'emploi
```bash
curl http://localhost:8000/api/v1/jobs/
```

## 🔧 Scripts utiles

### Vérifier les données
```powershell
python verify_data.py
```

### Vérifier les tables
```powershell
python check_migrations.py
```

### Recréer les tables (si nécessaire)
```powershell
python create_tables_direct.py
```

### Réinsérer les données de test
```powershell
python seed_data_simple.py
```

## 📝 Notes importantes

- **bcrypt version**: Downgraded à 4.1.2 pour compatibilité
- **Alembic**: Non utilisé (connexion avec mot de passe à espaces problématique)
- **Tables**: Créées directement via SQLAlchemy
- **Migrations**: À gérer manuellement si nécessaire

## 🔍 Debugging

Si vous rencontrez des problèmes:

1. **Vérifier la connexion PostgreSQL**:
   ```powershell
   python -c "import asyncio; from sqlalchemy.ext.asyncio import create_async_engine; asyncio.run(create_async_engine('postgresql+asyncpg://postgres:    @localhost:5432/recruteur').connect())"
   ```

2. **Vérifier l'environnement virtuel**:
   ```powershell
   python --version
   pip list | Select-String "fastapi|sqlalchemy|asyncpg"
   ```

3. **Logs de l'API**:
   Les logs structurés (JSON) s'affichent dans la console lors de l'exécution d'uvicorn.

## 🎯 Prochaines étapes

1. ✅ Base de données configurée
2. ✅ Tables créées
3. ✅ Données de test insérées
4. 🔄 Démarrer l'API (`uvicorn`)
5. 🔄 Tester les endpoints
6. 🔄 Développer/tester de nouvelles fonctionnalités
