"""
Script simplifié pour peupler la base de données avec des fake data
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from app.models.user import User
from app.models.job_offer import JobOffer
from app.models.application import Application, ApplicationDocument
from app.models.candidate_profile import CandidateProfile
from app.core.security.security import PasswordManager

async def seed_data():
    """Peupler la base avec des données de test"""
    
    database_url = "postgresql+asyncpg://postgres:    @localhost:5432/recruteur"
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("🔄 Peuplement de la base de données...")
    
    async with async_session() as session:
        try:
            # 1) Admin
            admin_result = await session.execute(select(User).where(User.email == "sevankedesh11@gmail.com"))
            admin = admin_result.scalar_one_or_none()
            
            if not admin:
                admin = User(
                    email="sevankedesh11@gmail.com",
                    first_name="Sevan Kedesh",
                    last_name="IKISSA PENDY",
                    role="admin",
                    phone="+24106000001",
                    hashed_password=PasswordManager.hash_password("Sevan@Seeg"),
                )
                session.add(admin)
                await session.flush()
                print("  ✓ Admin créé")
            else:
                print("  ✓ Admin existant")
            
            # 2) Recruiter
            recruiter_result = await session.execute(select(User).where(User.email == "recruteur@test.local"))
            recruiter = recruiter_result.scalar_one_or_none()
            
            if not recruiter:
                recruiter = User(
                    email="recruteur@test.local",
                    first_name="Jean",
                    last_name="Mavoungou",
                    role="recruiter",
                    hashed_password=PasswordManager.hash_password("Recrut3ur#2025"),
                    phone="+24107445566"
                )
                session.add(recruiter)
                await session.flush()
                print("  ✓ Recruteur créé")
            else:
                print("  ✓ Recruteur existant")
            
            # 3) Candidate
            candidate_result = await session.execute(select(User).where(User.email == "candidate@test.local"))
            candidate = candidate_result.scalar_one_or_none()
            
            if not candidate:
                candidate = User(
                    email="candidate@test.local",
                    first_name="Ada",
                    last_name="Lovelace",
                    role="candidate",
                    hashed_password=PasswordManager.hash_password("Password#2025"),
                    phone="+24100000000"
                )
                session.add(candidate)
                await session.flush()
                print("  ✓ Candidat créé")
            else:
                print("  ✓ Candidat existant")
            
            # 4) Job offer
            job_result = await session.execute(select(JobOffer).where(JobOffer.title == "Ingénieur Systèmes"))
            job = job_result.scalar_one_or_none()
            
            if not job:
                job = JobOffer(
                    recruiter_id=recruiter.id,
                    title="Ingénieur Systèmes",
                    description="Gestion systèmes et réseaux pour la SEEG",
                    location="Libreville",
                    contract_type="CDI",
                    department="IT",
                    requirements=["Linux", "Networking", "PostgreSQL"],
                    benefits=["Assurance santé", "Tickets restaurant"],
                    responsibilities=["Maintenir l'infrastructure", "Sécuriser le SI"],
                    status="open",
                    application_deadline=datetime.now(timezone.utc) + timedelta(days=30),
                )
                session.add(job)
                await session.flush()
                print("  ✓ Offre d'emploi créée")
            else:
                print("  ✓ Offre d'emploi existante")
            
            # 5) Application
            app_result = await session.execute(
                select(Application).where(
                    Application.candidate_id == candidate.id,
                    Application.job_offer_id == job.id,
                )
            )
            application = app_result.scalar_one_or_none()
            
            if not application:
                application = Application(
                    candidate_id=candidate.id,
                    job_offer_id=job.id,
                    status="pending",
                )
                session.add(application)
                await session.flush()
                print("  ✓ Candidature créée")
            else:
                print("  ✓ Candidature existante")
            
            # 6) Candidate profile
            profile_result = await session.execute(select(CandidateProfile).where(CandidateProfile.user_id == candidate.id))
            profile = profile_result.scalar_one_or_none()
            
            if not profile:
                profile = CandidateProfile(
                    user_id=candidate.id,
                    address="Quartier Centre, Libreville",
                    availability="Immédiate",
                    current_department="IT",
                    current_position="Analyste Système",
                    education="Master Informatique",
                    gender="F",
                    years_experience=5,
                    skills='["Linux","Networking","Python","PostgreSQL"]',
                )
                session.add(profile)
                await session.flush()
                print("  ✓ Profil candidat créé")
            else:
                print("  ✓ Profil candidat existant")
            
            await session.commit()
            print("\n✓ Base de données peuplée avec succès!")
            print(f"\n📋 Comptes de test créés:")
            print(f"  Admin: sevankedesh11@gmail.com / Sevan@Seeg")
            print(f"  Recruteur: recruteur@test.local / Recrut3ur#2025")
            print(f"  Candidat: candidate@test.local / Password#2025")
            
        except Exception as e:
            await session.rollback()
            print(f"\n✗ Erreur lors du peuplement:")
            print(f"  {type(e).__name__}: {e}")
            raise
        finally:
            await session.close()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_data())
