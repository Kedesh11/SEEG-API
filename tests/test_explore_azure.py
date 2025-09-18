"""
Test pour explorer la base de données Azure
"""
import pytest
from sqlalchemy import create_engine, text


class TestExploreAzure:
    """Tests pour explorer la base de données Azure."""
    
    def test_azure_database_connection(self):
        """Test la connexion à la base de données Azure."""
        try:
            database_url = "postgresql://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres"
            engine = create_engine(database_url, echo=False)
            
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                assert row[0] == 1
                
            print("✅ Connexion à la base de données Azure réussie")
            
        except Exception as e:
            pytest.fail(f"❌ Erreur de connexion à la base de données Azure: {e}")
    
    def test_azure_database_list_all_tables(self):
        """Test pour lister toutes les tables existantes."""
        try:
            database_url = "postgresql://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres"
            engine = create_engine(database_url, echo=False)
            
            with engine.connect() as connection:
                # Lister toutes les tables
                result = connection.execute(text("""
                    SELECT table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """))
                
                tables = result.fetchall()
                
                print(f"📊 Nombre total de tables: {len(tables)}")
                
                if tables:
                    print("📋 Tables existantes:")
                    for table in tables:
                        print(f"  - {table[0]} ({table[1]})")
                else:
                    print("⚠️ Aucune table trouvée dans le schéma public")
                    
        except Exception as e:
            pytest.fail(f"❌ Erreur lors de la liste des tables: {e}")
    
    def test_azure_database_list_all_schemas(self):
        """Test pour lister tous les schémas."""
        try:
            database_url = "postgresql://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres"
            engine = create_engine(database_url, echo=False)
            
            with engine.connect() as connection:
                # Lister tous les schémas
                result = connection.execute(text("""
                    SELECT schema_name
                    FROM information_schema.schemata
                    ORDER BY schema_name
                """))
                
                schemas = result.fetchall()
                
                print(f"📊 Nombre total de schémas: {len(schemas)}")
                
                print("📋 Schémas existants:")
                for schema in schemas:
                    print(f"  - {schema[0]}")
                    
        except Exception as e:
            pytest.fail(f"❌ Erreur lors de la liste des schémas: {e}")
    
    def test_azure_database_check_migrations(self):
        """Test pour vérifier les migrations Alembic."""
        try:
            database_url = "postgresql://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres"
            engine = create_engine(database_url, echo=False)
            
            with engine.connect() as connection:
                # Vérifier si la table alembic_version existe
                result = connection.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'alembic_version'
                    )
                """))
                
                exists = result.fetchone()[0]
                
                if exists:
                    print("✅ Table alembic_version existe")
                    
                    # Récupérer la version actuelle
                    result = connection.execute(text("SELECT version_num FROM alembic_version"))
                    version = result.fetchone()
                    
                    if version:
                        print(f"📊 Version actuelle: {version[0]}")
                    else:
                        print("⚠️ Aucune version trouvée")
                else:
                    print("⚠️ Table alembic_version n'existe pas")
                    print("💡 Il faut probablement exécuter les migrations")
                    
        except Exception as e:
            pytest.fail(f"❌ Erreur lors de la vérification des migrations: {e}")
    
    def test_azure_database_check_supabase_tables(self):
        """Test pour vérifier les tables Supabase."""
        try:
            database_url = "postgresql://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres"
            engine = create_engine(database_url, echo=False)
            
            with engine.connect() as connection:
                # Vérifier les tables Supabase communes
                supabase_tables = [
                    'auth.users', 'auth.sessions', 'auth.refresh_tokens',
                    'public.users', 'public.job_offers', 'public.applications'
                ]
                
                print("🔍 Vérification des tables Supabase:")
                
                for table in supabase_tables:
                    schema, table_name = table.split('.')
                    
                    result = connection.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = '{schema}' AND table_name = '{table_name}'
                        )
                    """))
                    
                    exists = result.fetchone()[0]
                    
                    if exists:
                        print(f"  ✅ {table} existe")
                    else:
                        print(f"  ❌ {table} n'existe pas")
                        
        except Exception as e:
            pytest.fail(f"❌ Erreur lors de la vérification des tables Supabase: {e}")
    
    def test_azure_database_database_info(self):
        """Test pour obtenir des informations sur la base de données."""
        try:
            database_url = "postgresql://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres"
            engine = create_engine(database_url, echo=False)
            
            with engine.connect() as connection:
                # Informations sur la base de données
                result = connection.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                print(f"📊 Version PostgreSQL: {version}")
                
                # Nom de la base de données
                result = connection.execute(text("SELECT current_database()"))
                db_name = result.fetchone()[0]
                print(f"📊 Nom de la base de données: {db_name}")
                
                # Utilisateur actuel
                result = connection.execute(text("SELECT current_user"))
                user = result.fetchone()[0]
                print(f"📊 Utilisateur actuel: {user}")
                
        except Exception as e:
            pytest.fail(f"❌ Erreur lors de la récupération des informations: {e}")
