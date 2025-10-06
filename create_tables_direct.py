"""
Script pour créer directement les tables dans la base de données locale
en contournant Alembic et les problèmes d'authentification
"""
import asyncio
import sys
from pathlib import Path

# Ensure app module is importable
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import all models to ensure they are registered with Base.metadata
from app.models.base import Base
from app.models.user import User
from app.models.job_offer import JobOffer
from app.models.application import Application, ApplicationDocument, ApplicationDraft, ApplicationHistory
from app.models.candidate_profile import CandidateProfile
from app.models.interview import InterviewSlot
from app.models.evaluation import Protocol1Evaluation, Protocol2Evaluation
from app.models.notification import Notification
from app.models.email import EmailLog
from app.models.seeg_agent import SeegAgent

async def create_all_tables():
    """Créer toutes les tables directement via SQLAlchemy"""
    
    # Connection string avec mot de passe (4 espaces)
    database_url = "postgresql+asyncpg://postgres:    @localhost:5432/recruteur"
    
    print("🔄 Connexion à la base de données...")
    try:
        engine = create_async_engine(database_url, echo=False)
        
        print("🔄 Création de toutes les tables...")
        async with engine.begin() as conn:
            # Drop all tables first (optional, comment out to keep existing data)
            # await conn.run_sync(Base.metadata.drop_all)
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
        
        print("✓ Toutes les tables ont été créées avec succès!")
        
        # List created tables
        async with engine.begin() as conn:
            result = await conn.execute(sqlalchemy.text("""
                SELECT tablename 
                FROM pg_catalog.pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """))
            tables = [row[0] for row in result.fetchall()]
            
        print(f"\n📋 Tables créées ({len(tables)}):")
        for table in tables:
            print(f"  ✓ {table}")
        
        await engine.dispose()
        return True
        
    except Exception as e:
        print(f"✗ Erreur lors de la création des tables:")
        print(f"  {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    import sqlalchemy
    success = asyncio.run(create_all_tables())
    sys.exit(0 if success else 1)
