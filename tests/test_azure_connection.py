"""
Test de connexion à la base de données Azure
"""
import pytest
from sqlalchemy import create_engine, text
from app.core.config.config import settings


class TestAzureConnection:
    """Tests de connexion à la base de données Azure."""
    
    def test_azure_database_connection(self):
        """Test la connexion à la base de données Azure."""
        try:
            # Créer un moteur de base de données
            engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
            
            # Tester la connexion
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                assert row[0] == 1
                
            print("✅ Connexion à la base de données Azure réussie")
            
        except Exception as e:
            pytest.fail(f"❌ Erreur de connexion à la base de données Azure: {e}")
    
    def test_azure_database_tables_exist(self):
        """Test que les tables principales existent."""
        try:
            engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
            
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
    
    def test_azure_database_users_table_structure(self):
        """Test la structure de la table users."""
        try:
            engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
            
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
                
                # Vérifier que les colonnes principales existent
                expected_columns = ['id', 'email', 'first_name', 'last_name', 'role']
                for col in expected_columns:
                    assert col in column_names, f"Colonne '{col}' manquante dans la table users"
                    print(f"✅ Colonne '{col}' présente dans la table users")
                    
        except Exception as e:
            pytest.fail(f"❌ Erreur lors de la vérification de la structure de la table users: {e}")
    
    def test_azure_database_applications_table_structure(self):
        """Test la structure de la table applications."""
        try:
            engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
            
            with engine.connect() as connection:
                # Vérifier la structure de la table applications
                result = connection.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'applications'
                    ORDER BY ordinal_position
                """))
                
                columns = result.fetchall()
                column_names = [col[0] for col in columns]
                
                # Vérifier que les colonnes principales existent
                expected_columns = ['id', 'candidate_id', 'job_offer_id', 'status', 'cover_letter']
                for col in expected_columns:
                    assert col in column_names, f"Colonne '{col}' manquante dans la table applications"
                    print(f"✅ Colonne '{col}' présente dans la table applications")
                    
        except Exception as e:
            pytest.fail(f"❌ Erreur lors de la vérification de la structure de la table applications: {e}")
    
    def test_azure_database_job_offers_table_structure(self):
        """Test la structure de la table job_offers."""
        try:
            engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
            
            with engine.connect() as connection:
                # Vérifier la structure de la table job_offers
                result = connection.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'job_offers'
                    ORDER BY ordinal_position
                """))
                
                columns = result.fetchall()
                column_names = [col[0] for col in columns]
                
                # Vérifier que les colonnes principales existent
                expected_columns = ['id', 'recruiter_id', 'title', 'description', 'location', 'contract_type']
                for col in expected_columns:
                    assert col in column_names, f"Colonne '{col}' manquante dans la table job_offers"
                    print(f"✅ Colonne '{col}' présente dans la table job_offers")
                    
        except Exception as e:
            pytest.fail(f"❌ Erreur lors de la vérification de la structure de la table job_offers: {e}")
    
    def test_azure_database_count_records(self):
        """Test le nombre d'enregistrements dans les tables principales."""
        try:
            engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
            
            with engine.connect() as connection:
                # Compter les enregistrements dans les tables principales
                tables_to_count = ['users', 'job_offers', 'applications']
                
                for table in tables_to_count:
                    result = connection.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.fetchone()[0]
                    print(f"📊 Table '{table}': {count} enregistrements")
                    
                    # Vérifier que la table n'est pas vide (optionnel)
                    # assert count > 0, f"Table '{table}' est vide"
                    
        except Exception as e:
            pytest.fail(f"❌ Erreur lors du comptage des enregistrements: {e}")
