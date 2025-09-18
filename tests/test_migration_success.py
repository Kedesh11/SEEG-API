"""
Test simple pour vérifier que la migration a bien fonctionné
"""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.core.config.config import settings

class TestMigrationSuccess:
    """Tests pour vérifier le succès de la migration"""
    
    @pytest.mark.asyncio
    async def test_indexes_created(self):
        """Vérifier que les index de performance ont été créés"""
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            # Vérifier que les index ont été créés
            index_query = text("""
                SELECT indexname, tablename 
                FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND indexname LIKE 'idx_%'
                ORDER BY tablename, indexname;
            """)
            
            result = await db.execute(index_query)
            indexes = result.fetchall()
            
            # Vérifier qu'on a au moins les index principaux
            index_names = [idx.indexname for idx in indexes]
            
            expected_indexes = [
                'idx_applications_candidate_job',
                'idx_applications_status_created',
                'idx_job_offers_recruiter_status',
                'idx_notifications_user_read',
                'idx_candidate_profiles_gender_experience'
            ]
            
            for expected_idx in expected_indexes:
                assert expected_idx in index_names, f"Index {expected_idx} non trouvé"
            
            print(f"✅ {len(indexes)} index de performance trouvés")
            print(f"📊 Index principaux: {expected_indexes}")
            
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_notifications_uuid_id(self):
        """Vérifier que la table notifications utilise maintenant UUID"""
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            # Vérifier le type de la colonne id dans notifications
            column_query = text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = 'notifications' 
                AND column_name = 'id';
            """)
            
            result = await db.execute(column_query)
            column_info = result.fetchone()
            
            assert column_info is not None, "Colonne id non trouvée dans notifications"
            assert 'uuid' in column_info.data_type.lower(), f"Type de colonne incorrect: {column_info.data_type}"
            
            print(f"✅ Table notifications utilise maintenant UUID: {column_info.data_type}")
            
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_interview_slots_new_columns(self):
        """Vérifier que les nouvelles colonnes ont été ajoutées à interview_slots"""
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            # Vérifier les nouvelles colonnes
            columns_query = text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'interview_slots' 
                AND column_name IN ('recruiter_id', 'meeting_link', 'notes')
                ORDER BY column_name;
            """)
            
            result = await db.execute(columns_query)
            columns = result.fetchall()
            
            expected_columns = ['meeting_link', 'notes', 'recruiter_id']
            found_columns = [col.column_name for col in columns]
            
            for expected_col in expected_columns:
                assert expected_col in found_columns, f"Colonne {expected_col} non trouvée"
            
            print(f"✅ Nouvelles colonnes ajoutées à interview_slots: {found_columns}")
            
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_notifications_priority_column(self):
        """Vérifier que la colonne priority a été ajoutée à notifications"""
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            # Vérifier la colonne priority
            column_query = text("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns 
                WHERE table_name = 'notifications' 
                AND column_name = 'priority';
            """)
            
            result = await db.execute(column_query)
            column_info = result.fetchone()
            
            assert column_info is not None, "Colonne priority non trouvée dans notifications"
            assert column_info.data_type == 'character varying', f"Type de colonne incorrect: {column_info.data_type}"
            
            print(f"✅ Colonne priority ajoutée: {column_info.data_type} (défaut: {column_info.column_default})")
            
        await engine.dispose()
    
    @pytest.mark.asyncio
    async def test_unique_constraint_applications(self):
        """Vérifier que la contrainte unique a été ajoutée à applications"""
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            # Vérifier la contrainte unique
            constraint_query = text("""
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints 
                WHERE table_name = 'applications' 
                AND constraint_name = 'uq_applications_candidate_job';
            """)
            
            result = await db.execute(constraint_query)
            constraint_info = result.fetchone()
            
            assert constraint_info is not None, "Contrainte unique uq_applications_candidate_job non trouvée"
            assert constraint_info.constraint_type == 'UNIQUE', f"Type de contrainte incorrect: {constraint_info.constraint_type}"
            
            print(f"✅ Contrainte unique ajoutée: {constraint_info.constraint_name}")
            
        await engine.dispose()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
