# Scripts de Migration SQL - SEEG API

Ce dossier contient les scripts de migration SQL pour les environnements **local** et **Azure**.

## 📁 Fichiers

- `migrate_database_local.py` - Script pour PostgreSQL en local
- `migrate_database_azure.py` - Script pour Azure PostgreSQL

## 🚀 Utilisation

### Migration Locale

```bash
# Voir le statut
python scripts/migrate_database_local.py --action status

# Appliquer les migrations
python scripts/migrate_database_local.py --action upgrade

# Réappliquer les migrations modifiées
python scripts/migrate_database_local.py --action upgrade --force-modified

# Rollback
python scripts/migrate_database_local.py --action rollback --target 20251016_create_email_logs
```

### Migration Azure

```bash
# Voir le statut
python scripts/migrate_database_azure.py --action status

# Appliquer les migrations
python scripts/migrate_database_azure.py --action upgrade

# Réappliquer les migrations modifiées
python scripts/migrate_database_azure.py --action upgrade --force-modified

# Rollback
python scripts/migrate_database_azure.py --action rollback --target 20251016_create_email_logs
```

## ⚙️ Configuration

### Local (`migrate_database_local.py`)

Modifiez les lignes 77-82 :

```python
host: str = "localhost"
port: int = 5432
database: str = "seeg_db"
user: str = "postgres"
password: str = "postgres"  # ⚠️ Votre mot de passe local
```

### Azure (`migrate_database_azure.py`)

Modifiez les lignes 77-86 :

```python
host: str = "seeg-postgres-server.postgres.database.azure.com"
port: int = 5432
database: str = "postgres"
user: str = "Sevan"
password: str = "Sevan@Seeg"  # ⚠️ Votre mot de passe Azure

# Configuration Azure pour le firewall
resource_group: str = "seeg-backend-rg"
server_name: str = "seeg-postgres-server"
my_ip: str = "41.158.96.219"  # ⚠️ Votre IP publique actuelle
```

## 📝 Créer une Nouvelle Migration

1. Créer le fichier SQL dans `app/db/migrations/sql/` :

```sql
-- Description: Brève description de la migration
-- Depends: 20251016_create_email_logs

CREATE TABLE ma_nouvelle_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ma_table_name ON ma_nouvelle_table(name);
```

2. (Optionnel) Créer le fichier de rollback dans `app/db/migrations/sql/rollback/` :

```sql
DROP TABLE IF EXISTS ma_nouvelle_table CASCADE;
```

3. Lancer la migration :

```bash
python scripts/migrate_database_local.py --action upgrade
```

## ✨ Fonctionnalités

✅ **Auto-Discovery** : Découverte automatique des fichiers `.sql`  
✅ **Checksum** : Détection des modifications via MD5  
✅ **Transactions** : Support transactionnel avec rollback automatique  
✅ **Dépendances** : Vérification des dépendances entre migrations  
✅ **Historique** : Table `migration_history` avec tous les détails  
✅ **Firewall Azure** : Gestion automatique des règles (Azure uniquement)  
✅ **Logs Structurés** : Traçabilité complète avec timestamps  
✅ **Idempotence** : Les migrations peuvent être réexécutées sans danger  

## 📊 Format des Noms de Fichiers

```
{YYYYMMDD}_{nom_de_la_migration}.sql
```

Exemples :
- `20251016_create_email_logs.sql`
- `20251017_add_notifications_table.sql`
- `20251018_alter_users_add_status.sql`

## 🔍 Table `migration_history`

Colonnes principales :
- `version` : Version de la migration (nom du fichier sans .sql)
- `name` : Nom lisible de la migration
- `description` : Description extraite du commentaire SQL
- `checksum` : MD5 du contenu SQL
- `applied_at` : Date/heure d'application
- `status` : `completed`, `failed`, `rolled_back`, `modified`
- `execution_time_ms` : Temps d'exécution en millisecondes
- `error_message` : Message d'erreur en cas d'échec

## 🛡️ Meilleures Pratiques

1. **Toujours tester en local d'abord** avant d'appliquer sur Azure
2. **Créer des rollbacks** pour les migrations critiques
3. **Utiliser des transactions** (déjà géré par le script)
4. **Vérifier le statut** avant et après migration
5. **Documenter** chaque migration avec `-- Description:`
6. **Déclarer les dépendances** avec `-- Depends:`
7. **Ne jamais modifier** une migration déjà appliquée (créer une nouvelle)

## 🆘 Dépannage

### Erreur de connexion locale

```bash
# Vérifier que PostgreSQL est démarré
psql -U postgres -d seeg_db -c "SELECT 1;"
```

### Erreur de connexion Azure

```bash
# Vérifier votre IP
curl https://api.ipify.org

# Mettre à jour la configuration dans migrate_database_azure.py
```

### Migration bloquée

```bash
# Voir l'état détaillé
python scripts/migrate_database_local.py --action status --verbose

# Vérifier la table migration_history
psql -U postgres -d seeg_db -c "SELECT * FROM migration_history ORDER BY applied_at DESC LIMIT 10;"
```


