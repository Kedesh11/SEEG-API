# 🔄 Guide ETL - Export Temps Réel vers Azure Blob Storage

## 🎯 Vue d'Ensemble

Système d'**ETL (Extract, Transform, Load) temps réel** qui exporte automatiquement les candidatures vers Azure Blob Storage lors de leur création.

### Architecture

```
Candidature créée
    ↓
Webhook déclenché (/webhooks/application-submitted)
    ↓
Récupération données complètes (PostgreSQL)
    ↓
Export JSON vers Blob Storage (Data Lake)
    ↓
Optionnel: Azure Function pour traitement supplémentaire
```

### Data Lake Structure

```
Azure Storage Account: seegairaweu001
├── raw/                                              # Données brutes
│   └── applications/
│       └── ingestion_date=2025-10-17/
│           ├── json/                                 # JSON avec toutes les infos
│           │   └── {application_id}.json
│           └── documents/                            # PDF pour OCR
│               └── {application_id}/
│                   ├── cv_{filename}.pdf
│                   ├── cover_letter_{filename}.pdf
│                   └── diplome_{filename}.pdf
├── curated/                                          # Données nettoyées (futur)
└── features/                                         # Features ML (futur)
```

### Ce qui est exporté

**1. JSON Complet** (`applications/.../json/{id}.json`) :
- ✅ Candidature (application) : status, mtp_answers, références, dates
- ✅ Candidat (user) : email, nom, téléphone, adresse, matricule, poste, expérience
- ✅ Profil Candidat (candidate_profile) : compétences, salaire attendu, LinkedIn, portfolio, éducation
- ✅ Offre d'emploi (job_offer) : titre, description, localisation, questions MTP
- ✅ Metadata : timestamps, source, version

**2. Documents PDF Séparés** (`applications/.../documents/{id}/...`) :
- ✅ CV (prêt pour OCR)
- ✅ Lettre de motivation (prêt pour OCR)
- ✅ Diplôme (prêt pour OCR)
- ✅ Metadata : type, application_id, ready_for_ocr=true
```

---

## ⚙️ Configuration

### 1. Charger la Configuration ETL

**PowerShell :**
```powershell
# Charger les variables d'environnement
. .\load_etl_config.ps1
```

**Ou manuellement :**
```powershell
$env:AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=seegairaweu001;AccountKey=...;EndpointSuffix=core.windows.net"
$env:WEBHOOK_SECRET="test-secret-key"
```

### 2. Variables d'Environnement Requises

| Variable | Description | Exemple |
|----------|-------------|---------|
| `AZURE_STORAGE_CONNECTION_STRING` | Connection string du Storage Account | `DefaultEndpointsProtocol=https;AccountName=...` |
| `WEBHOOK_SECRET` | Token de sécurité pour le webhook | `test-secret-key` (dev) ou fort en prod |
| `AZ_FUNC_ON_APP_SUBMITTED_URL` | URL Azure Function (optionnel) | `https://func.azurewebsites.net/api/...` |
| `AZ_FUNC_ON_APP_SUBMITTED_KEY` | Clé Azure Function (optionnel) | `xxx` |

### 3. Configuration Production (Azure App Service)

Dans **Azure Portal → App Service → Configuration → Application Settings** :

```bash
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=seegairaweu001;AccountKey=xxx;EndpointSuffix=core.windows.net
WEBHOOK_SECRET=<generer-secret-fort-48-caracteres>
```

---

## 🚀 Utilisation

### Workflow Automatique (Recommandé)

L'ETL est déclenché **automatiquement** à chaque création de candidature si vous appelez le webhook depuis l'endpoint de création.

### Déclenchement Manuel du Webhook

**1. Via API (cURL) :**

```bash
curl -X POST https://seeg-backend-api.azurewebsites.net/api/v1/webhooks/application-submitted \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: test-secret-key" \
  -d '{
    "application_id": "28c0a358-e55e-4dc6-8a11-71e165ff9b29",
    "last_watermark": "2025-10-17T00:00:00Z"
  }'
```

**2. Via Python :**

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/webhooks/application-submitted",
        headers={
            "X-Webhook-Token": "test-secret-key",
            "Content-Type": "application/json"
        },
        json={
            "application_id": "28c0a358-e55e-4dc6-8a11-71e165ff9b29",
            "last_watermark": "2025-10-17T00:00:00Z"
        }
    )
    print(response.json())
```

**3. Via Script de Test :**

```bash
# Charger la config ETL
. .\load_etl_config.ps1

# Lancer l'API (dans un terminal séparé)
uvicorn app.main:app --reload

# Tester le webhook
python test_etl_webhook.py
```

---

## 📊 Format d'Export

### JSON Export (Blob Storage)

**Chemin :** `raw/applications/ingestion_date=2025-10-17/{application_id}.json`

**Structure :**

```json
{
  "_metadata": {
    "entity_type": "application",
    "entity_id": "28c0a358-e55e-4dc6-8a11-71e165ff9b29",
    "ingestion_timestamp": "2025-10-17T08:30:00.000Z",
    "source": "seeg-api",
    "version": "1.0"
  },
  "id": "28c0a358-e55e-4dc6-8a11-71e165ff9b29",
  "candidate_id": "93da6d05-74de-4ba6-a807-76513186993f",
  "job_offer_id": "dbf17c25-febc-4d9e-a34e-19c6e1017167",
  "status": "pending",
  "mtp_answers": {
    "reponses_metier": [...],
    "reponses_talent": [...],
    "reponses_paradigme": [...]
  },
  "has_been_manager": false,
  "ref_entreprise": "...",
  "ref_fullname": "...",
  "ref_mail": "...",
  "ref_contact": "...",
  "created_at": "2025-10-17T08:25:00.000Z",
  "updated_at": "2025-10-17T08:25:00.000Z",
  "candidate": {
    "email": "test@example.com",
    "first_name": "Jean",
    "last_name": "Dupont"
  },
  "job_offer": {
    "title": "Ingénieur DevOps",
    "location": "Libreville"
  }
}
```

---

## 🧪 Tests

### Test Local

```bash
# 1. Charger la configuration
. .\load_etl_config.ps1

# 2. Lancer l'API (terminal 1)
uvicorn app.main:app --reload

# 3. Tester le webhook (terminal 2)
python test_etl_webhook.py
```

### Test Production

```bash
# Tester directement sur Azure
curl -X POST https://seeg-backend-api.azurewebsites.net/api/v1/webhooks/application-submitted \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Token: <PRODUCTION_SECRET>" \
  -d '{
    "application_id": "28c0a358-e55e-4dc6-8a11-71e165ff9b29"
  }'
```

---

## 🔍 Vérification des Exports

### Via Azure Portal

1. Aller sur https://portal.azure.com
2. Chercher `seegairaweu001`
3. **Containers** → `raw`
4. Naviguer vers `applications/ingestion_date=YYYY-MM-DD/`
5. Télécharger et vérifier les fichiers JSON

### Via Azure CLI

```bash
# Lister les exports du jour
az storage blob list \
  --container-name raw \
  --prefix "applications/ingestion_date=$(date +%Y-%m-%d)" \
  --account-name seegairaweu001 \
  --account-key "2/kZrX2Unadnl4mknZw4HMqvOPioAEI6XAWSbjQ1MdzwTiQiiM8IxaW3+IHTJ+k9fTlev+k5zWdS+ASt2rJj1w==" \
  --output table

# Télécharger un export spécifique
az storage blob download \
  --container-name raw \
  --name "applications/ingestion_date=2025-10-17/{application_id}.json" \
  --file "export.json" \
  --account-name seegairaweu001 \
  --account-key "..."
```

### Via Python

```python
from azure.storage.blob import BlobServiceClient

connection_string = "DefaultEndpointsProtocol=https;..."
blob_service = BlobServiceClient.from_connection_string(connection_string)
container_client = blob_service.get_container_client("raw")

# Lister les blobs
blobs = container_client.list_blobs(name_starts_with="applications/")
for blob in blobs:
    print(f"{blob.name} - {blob.size} bytes")
```

---

## 🔧 Troubleshooting

### ❌ Erreur : "AZURE_STORAGE_CONNECTION_STRING non définie"

**Solution :**
```bash
# Charger la configuration
. .\load_etl_config.ps1

# Ou définir manuellement
$env:AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=..."
```

### ❌ Erreur 401 : "Webhook non autorisé"

**Solution :**
```bash
# Vérifier que le header est correct
X-Webhook-Token: test-secret-key

# Ou désactiver la validation (dev only)
# Laisser WEBHOOK_SECRET vide
```

### ❌ Erreur 404 : "Candidature introuvable"

**Solution :**
- Vérifier que l'`application_id` existe dans la base
- Utiliser un ID d'une candidature existante

### ❌ Erreur : "Import azure.storage.blob could not be resolved"

**Solution :**
```bash
# Installer les dépendances
pip install azure-storage-blob==12.19.0 azure-identity==1.15.0
```

---

## 📈 Évolutions Futures

### Phase 2 : Export Curated (Données Nettoyées)

```python
# Enrichissement et nettoyage
raw → curated/applications/ (JSON nettoyé, normalisé)
```

### Phase 3 : Features ML

```python
# Extraction de features pour ML
curated → features/applications/ (Parquet, prêt pour ML)
```

### Phase 4 : Export Batch

```python
# Export batch quotidien
Toutes les candidatures modifiées dans les 24h → Blob Storage
```

---

## ✅ Checklist Déploiement Production

- [ ] `AZURE_STORAGE_CONNECTION_STRING` définie dans Azure App Service
- [ ] `WEBHOOK_SECRET` fort (48+ caractères) défini
- [ ] Conteneur `raw` créé dans Azure Storage
- [ ] Firewall Azure Storage configuré (si nécessaire)
- [ ] Tests ETL validés en local
- [ ] Monitoring des exports activé (logs)
- [ ] Alerte configurée en cas d'échec d'export

---

📝 **Maintenu par :** Équipe SEEG Tech  
📅 **Dernière mise à jour :** 17 octobre 2024

