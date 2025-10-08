# 🔴 PROBLÈME CORS SUR AZURE - SOLUTION

## ❌ ERREUR

```
Access to fetch at 'https://seeg-backend-api.azurewebsites.net/api/v1/auth/login' 
from origin 'http://localhost:8080' has been blocked by CORS policy: 
No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

---

## 🔍 DIAGNOSTIC

Le frontend (localhost:8080) essaie de se connecter à l'API Azure, mais :
- ⚠️ L'API Azure ne retourne pas les headers CORS
- ⚠️ Le navigateur bloque la requête

**Causes possibles** :
1. Les variables d'environnement CORS ne sont pas configurées sur Azure
2. Le serveur Azure ne démarre pas correctement
3. Les middlewares CORS ne sont pas activés

---

## ✅ SOLUTIONS

### SOLUTION 1 : Configurer les variables d'environnement Azure (RECOMMANDÉ)

Dans **Azure Portal** → **App Service** → **Configuration** → **Application settings** :

```bash
# CORS - CRITIQUE
ALLOWED_ORIGINS=http://localhost:8080,http://localhost:3000,https://www.seeg-talentsource.com,https://seeg-hcm.vercel.app,https://seeg-backend-api.azurewebsites.net
ALLOWED_CREDENTIALS=true

# Autres variables importantes
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<VOTRE_SECRET_KEY_SECURISEE>

# Database Azure
DATABASE_URL=postgresql+asyncpg://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres
DATABASE_URL_SYNC=postgresql://Sevan:Sevan%40Seeg@seeg-postgres-server.postgres.database.azure.com:5432/postgres
```

**Puis redémarrer** l'App Service.

---

### SOLUTION 2 : Vérifier que l'App Service démarre

```bash
# Via Azure CLI
az webapp log tail --name seeg-backend-api --resource-group <votre-rg>

# Chercher les erreurs de démarrage
```

---

### SOLUTION 3 : Configurer CORS dans le portail Azure

**Azure Portal** → **App Service** → **CORS** :

Ajouter les origines :
- `http://localhost:8080`
- `http://localhost:3000`
- `https://www.seeg-talentsource.com`
- `https://seeg-hcm.vercel.app`

✅ Cocher "Enable Access-Control-Allow-Credentials"

---

### SOLUTION 4 : Vérifier le code CORS (déjà OK dans votre code)

```python
# app/main.py - ligne ~223
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # ✅ Configuré
    allow_credentials=settings.ALLOWED_CREDENTIALS,  # ✅ Configuré
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🧪 TEST RAPIDE CORS

### Depuis votre navigateur (Console DevTools)

```javascript
fetch('https://seeg-backend-api.azurewebsites.net/health', {
  method: 'GET'
})
.then(r => r.json())
.then(data => console.log('✅ API accessible:', data))
.catch(e => console.error('❌ Erreur:', e));
```

**Si ça fonctionne** : Le serveur Azure est up
**Si ça échoue** : Problème de démarrage du serveur

---

## 🔧 COMMANDES POUR DIAGNOSTIQUER

### 1. Vérifier si l'API Azure est accessible

```bash
# Test health
curl https://seeg-backend-api.azurewebsites.net/health

# Test avec CORS header
curl -H "Origin: http://localhost:8080" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     https://seeg-backend-api.azurewebsites.net/api/v1/auth/login
```

### 2. Vérifier les logs Azure

```bash
az webapp log tail --name seeg-backend-api --resource-group <votre-rg>
```

### 3. Redémarrer l'App Service

```bash
az webapp restart --name seeg-backend-api --resource-group <votre-rg>
```

---

## ⚡ SOLUTION RAPIDE RECOMMANDÉE

### Étape 1 : Aller sur Azure Portal

1. Ouvrir **https://portal.azure.com**
2. Chercher **seeg-backend-api**
3. Aller dans **Configuration** → **Application settings**

### Étape 2 : Ajouter ces variables

```
ALLOWED_ORIGINS = http://localhost:8080,http://localhost:3000,https://www.seeg-talentsource.com,https://seeg-hcm.vercel.app
ALLOWED_CREDENTIALS = true
```

### Étape 3 : Redémarrer

Cliquer sur **Restart** en haut

### Étape 4 : Attendre 2-3 minutes

Le redémarrage prend du temps

### Étape 5 : Retester depuis le frontend

---

## 📋 CHECKLIST DE VÉRIFICATION

- [ ] Variables CORS configurées sur Azure
- [ ] App Service redémarré
- [ ] Logs Azure vérifiés (pas d'erreur de démarrage)
- [ ] Test /health fonctionne
- [ ] Frontend peut se connecter

---

## 💡 ALTERNATIVE : Déployer une nouvelle version

Si les variables d'environnement ne fonctionnent pas, **redéployez** avec les derniers changements :

```bash
# Votre code local fonctionne, donc redéployer devrait résoudre
.\scripts\deploy-azure.ps1
```

---

**Le problème est UNIQUEMENT la configuration CORS sur Azure, pas votre code !** ✅

