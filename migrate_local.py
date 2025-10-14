"""
Script de migration pour la base de données locale
"""
import asyncio
import asyncpg
import os

# Configuration de la base de données locale
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "    "),  # 4 espaces
    "database": os.getenv("DB_NAME", "recruteur"),
}

async def run_migrations():
    """Exécuter les migrations"""
    print("="*60)
    print("🚀 MIGRATIONS BASE DE DONNÉES LOCALE")
    print("="*60)
    print(f"\n📍 Configuration:")
    print(f"   Host: {DB_CONFIG['host']}")
    print(f"   Port: {DB_CONFIG['port']}")
    print(f"   Database: {DB_CONFIG['database']}")
    print(f"   User: {DB_CONFIG['user']}")
    
    try:
        print("\n🔄 Connexion à la base de données...")
        conn = await asyncpg.connect(**DB_CONFIG)
        print("✅ Connecté!\n")
        
        # Migration 1: Ajouter questions_mtp aux job_offers
        print("📦 Migration 1: questions_mtp dans job_offers")
        try:
            await conn.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_name = 'job_offers' AND column_name = 'questions_mtp'
                    ) THEN
                        ALTER TABLE job_offers ADD COLUMN questions_mtp JSONB;
                        RAISE NOTICE '✅ Colonne questions_mtp ajoutée';
                    ELSE
                        RAISE NOTICE '⏭️  Colonne questions_mtp existe déjà';
                    END IF;
                END $$;
            """)
            print("   ✅ questions_mtp vérifiée")
        except Exception as e:
            print(f"   ⚠️  Erreur: {e}")
        
        # Migration 2: Convertir colonnes JSON en JSONB dans job_offers
        print("\n📦 Migration 2: Conversion JSON → JSONB dans job_offers")
        for col in ['requirements', 'benefits', 'responsibilities']:
            try:
                col_type = await conn.fetchval(f"""
                    SELECT data_type FROM information_schema.columns 
                    WHERE table_name = 'job_offers' AND column_name = '{col}'
                """)
                
                if col_type == 'json':
                    await conn.execute(f"""
                        ALTER TABLE job_offers 
                        ALTER COLUMN {col} TYPE JSONB USING {col}::JSONB
                    """)
                    print(f"   ✅ {col} converti en JSONB")
                else:
                    print(f"   ⏭️  {col} déjà en {col_type}")
            except Exception as e:
                print(f"   ⚠️  Erreur {col}: {e}")
        
        # Migration 3: offer_status (remplacer is_internal_only)
        print("\n📦 Migration 3: offer_status dans job_offers")
        try:
            # Vérifier si offer_status existe
            has_offer_status = await conn.fetchval("""
                SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name = 'job_offers' AND column_name = 'offer_status'
            """)
            
            if not has_offer_status:
                await conn.execute("""
                    ALTER TABLE job_offers ADD COLUMN offer_status VARCHAR(20) DEFAULT 'tous'
                """)
                print("   ✅ offer_status ajoutée")
                
                # Migrer les données si is_internal_only existe
                has_is_internal = await conn.fetchval("""
                    SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_name = 'job_offers' AND column_name = 'is_internal_only'
                """)
                
                if has_is_internal:
                    await conn.execute("""
                        UPDATE job_offers 
                        SET offer_status = CASE 
                            WHEN is_internal_only = true THEN 'interne' 
                            ELSE 'externe' 
                        END
                        WHERE offer_status = 'tous'
                    """)
                    await conn.execute("ALTER TABLE job_offers DROP COLUMN is_internal_only")
                    print("   ✅ Données migrées et is_internal_only supprimée")
            else:
                print("   ⏭️  offer_status existe déjà")
        except Exception as e:
            print(f"   ⚠️  Erreur: {e}")
        
        # Migration 4: Colonnes dans applications
        print("\n📦 Migration 4: Nouvelles colonnes dans applications")
        columns_to_add = {
            'has_been_manager': 'BOOLEAN DEFAULT FALSE',
            'ref_entreprise': 'VARCHAR(255)',
            'ref_fullname': 'VARCHAR(255)',
            'ref_mail': 'VARCHAR(255)',
            'ref_contact': 'VARCHAR(50)'
        }
        
        for col_name, col_type in columns_to_add.items():
            try:
                exists = await conn.fetchval(f"""
                    SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_name = 'applications' AND column_name = '{col_name}'
                """)
                
                if not exists:
                    await conn.execute(f"ALTER TABLE applications ADD COLUMN {col_name} {col_type}")
                    print(f"   ✅ {col_name} ajoutée")
                else:
                    print(f"   ⏭️  {col_name} existe déjà")
            except Exception as e:
                print(f"   ⚠️  Erreur {col_name}: {e}")
        
        # Migration 5: Convertir mtp_answers en JSONB
        print("\n📦 Migration 5: Conversion mtp_answers → JSONB")
        try:
            mtp_type = await conn.fetchval("""
                SELECT data_type FROM information_schema.columns 
                WHERE table_name = 'applications' AND column_name = 'mtp_answers'
            """)
            
            if mtp_type == 'json':
                await conn.execute("""
                    ALTER TABLE applications 
                    ALTER COLUMN mtp_answers TYPE JSONB USING mtp_answers::JSONB
                """)
                print("   ✅ mtp_answers converti en JSONB")
            else:
                print(f"   ⏭️  mtp_answers déjà en {mtp_type}")
        except Exception as e:
            print(f"   ⚠️  Erreur: {e}")
        
        # Migration 6: Table alembic_version
        print("\n📦 Migration 6: Table alembic_version")
        try:
            table_exists = await conn.fetchval("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'alembic_version'
            """)
            
            if not table_exists:
                await conn.execute("""
                    CREATE TABLE alembic_version (
                        version_num VARCHAR(32) NOT NULL,
                        CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                    )
                """)
                print("   ✅ Table alembic_version créée")
            
            # Mettre à jour la version
            await conn.execute("DELETE FROM alembic_version")
            await conn.execute("INSERT INTO alembic_version (version_num) VALUES ('20251014_local')")
            print("   ✅ Version mise à jour: 20251014_local")
        except Exception as e:
            print(f"   ⚠️  Erreur: {e}")
        
        await conn.close()
        
        print("\n" + "="*60)
        print("✅ TOUTES LES MIGRATIONS TERMINÉES AVEC SUCCÈS")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Erreur de connexion: {e}")
        print("\n💡 Assurez-vous que:")
        print("   1. PostgreSQL est lancé localement")
        print("   2. La base de données existe")
        print("   3. Les credentials sont corrects")
        print("\n📝 Variables d'environnement utilisables:")
        print("   DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migrations())
    exit(0 if success else 1)

