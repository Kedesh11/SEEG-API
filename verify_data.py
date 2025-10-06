"""
Script pour vérifier que les données ont bien été insérées dans la base
"""
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func

from app.models.user import User
from app.models.job_offer import JobOffer
from app.models.application import Application
from app.models.candidate_profile import CandidateProfile

async def verify_data():
    """Vérifier les données dans la base"""
    
    database_url = "postgresql+asyncpg://postgres:    @localhost:5432/recruteur"
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("🔍 Vérification des données dans la base...\n")
    
    async with async_session() as session:
        try:
            # Count users by role
            result = await session.execute(
                select(User.role, func.count(User.id))
                .group_by(User.role)
            )
            users_by_role = dict(result.fetchall())
            
            print("📊 Utilisateurs par rôle:")
            for role, count in users_by_role.items():
                print(f"  • {role}: {count}")
            
            # List all users
            result = await session.execute(select(User))
            users = result.scalars().all()
            
            print(f"\n👥 Liste des utilisateurs ({len(users)}):")
            for user in users:
                print(f"  • {user.email} ({user.role}) - {user.first_name} {user.last_name}")
            
            # Count job offers
            result = await session.execute(select(func.count(JobOffer.id)))
            job_count = result.scalar()
            
            print(f"\n💼 Offres d'emploi: {job_count}")

            
            if job_count > 0:
                result = await session.execute(select(JobOffer))
                jobs = result.scalars().all()
                for job in jobs:
                    print(f"  • {job.title} ({job.status}) - {job.location}")
            
            # Count applications
            result = await session.execute(select(func.count(Application.id)))
            app_count = result.scalar()
            
            print(f"\n📝 Candidatures: {app_count}")
            
            if app_count > 0:
                result = await session.execute(select(Application))
                applications = result.scalars().all()
                for app in applications:
                    print(f"  • Candidature ID: {app.id} (statut: {app.status})")
            
            # Count candidate profiles
            result = await session.execute(select(func.count(CandidateProfile.id)))
            profile_count = result.scalar()
            
            print(f"\n📋 Profils candidats: {profile_count}")
            
            print("\n✅ Vérification terminée avec succès!")
            
        except Exception as e:
            print(f"\n❌ Erreur lors de la vérification:")
            print(f"  {type(e).__name__}: {e}")
            raise
        finally:
            await session.close()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify_data())
