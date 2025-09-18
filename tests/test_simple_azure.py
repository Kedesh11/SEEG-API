"""
Test simple de connexion à la base de données Azure
"""
import pytest
from sqlalchemy import create_engine, text
import os


class TestSimpleAzure:
    """Tests simples de connexion à la base de données Azure."""
    
    def test_azure_database_connection_simple(self):
        """Test simple la connexion à la base de données Azure."""
        try:
            # URL de connexion directe
            database_url = "postgresql://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres"
            
            # Créer un moteur de base de données
            engine = create_engine(database_url, echo=False)
            
            # Tester la connexion
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                assert row[0] == 1
                
            print("✅ Connexion à la base de données Azure réussie")
            
        except Exception as e:
            pytest.fail(f"❌ Erreur de connexion à la base de données Azure: {e}")
    
    def test_azure_database_tables_simple(self):
        """Test simple que les tables principales existent."""
        try:
            database_url = "postgresql://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres"
            engine = create_engine(database_url, echo=False)
            
            with engine.connect() as connection:
                # Vérifier que les tables principales existent
                tables_to_check = [
                    'users', 'job_offers', 'applications', 
                    'protocol1_evaluations', 'protocol2_evaluations',
                    'notifications', 'interview_slots'
                ]
                
                for table in tables_to_check:
                    result = connection.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = '{table}'
                        )
                    """))
                    exists = result.fetchone()[0]
                    assert exists, f"Table '{table}' n'existe pas"
                    print(f"✅ Table '{table}' existe")
                    
        except Exception as e:
            pytest.fail(f"❌ Erreur lors de la vérification des tables: {e}")
    
    def test_azure_database_count_simple(self):
        """Test simple le nombre d'enregistrements dans les tables principales."""
        try:
            database_url = "postgresql://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres"
            engine = create_engine(database_url, echo=False)
            
            with engine.connect() as connection:
                # Compter les enregistrements dans les tables principales
                tables_to_count = ['users', 'job_offers', 'applications']
                
                for table in tables_to_count:
                    result = connection.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    print(f"📊 Table '{table}': {count} enregistrements")
                    
        except Exception as e:
            pytest.fail(f"❌ Erreur lors du comptage des enregistrements: {e}")
    
    def test_azure_database_users_structure_simple(self):
        """Test simple la structure de la table users."""
        try:
            database_url = "postgresql://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres"
            engine = create_engine(database_url, echo=False)
            
            with engine.connect() as connection:
                # Vérifier la structure de la table users
                result = connection.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'users'
                    ORDER BY ordinal_position
                """))
                
                columns = result.fetchall()
                column_names = [col[0] for col in columns]
                
                print(f"📊 Colonnes de la table users: {column_names}")
                
                # Vérifier que les colonnes principales existent
                expected_columns = ['id', 'email', 'first_name', 'last_name', 'role']
                for col in expected_columns:
                    assert col in column_names, f"Colonne '{col}' manquante dans la table users"
                    print(f"✅ Colonne '{col}' présente dans la table users")
                    
        except Exception as e:
            pytest.fail(f"❌ Erreur lors de la vérification de la structure de la table users: {e}")
    
    def test_azure_database_sample_data_simple(self):
        """Test simple récupération de données d'exemple."""
        try:
            database_url = "postgresql://Sevan:Azure%40Seeg@seegrecruiter.postgres.database.azure.com:5432/postgres"
            engine = create_engine(database_url, echo=False)
            
            with engine.connect() as connection:
                # Récupérer quelques utilisateurs
                result = connection.execute(text("SELECT id, email, first_name, last_name, role FROM users LIMIT 5"))
                users = result.fetchall()
                
                print(f"📊 Nombre d'utilisateurs récupérés: {len(users)}")
                
                for user in users:
                    print(f"✅ Utilisateur: {user[1]} ({user[4]}) - {user[2]} {user[3]}")
                
                # Récupérer quelques offres d'emploi
                result = connection.execute(text("SELECT id, title, location, contract_type FROM job_offers LIMIT 5"))
                job_offers = result.fetchall()
                
                print(f"📊 Nombre d'offres d'emploi récupérées: {len(job_offers)}")
                
                for job in job_offers:
                    print(f"✅ Offre: {job[1]} ({job[2]}) - {job[3]}")
                    
        except Exception as e:
            pytest.fail(f"❌ Erreur lors de la récupération des données d'exemple: {e}")
