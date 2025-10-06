import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Assurer l'import du package app quand exécuté directement
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Sanitize d'éventuelles variables d'environnement mal nommées (ex: "$env:DATABASE_URL")
for key in list(os.environ.keys()):
    if key.startswith("$env:"):
        fixed = key.split(":", 1)[1]
        os.environ[fixed] = os.environ[key]
        del os.environ[key]

# Définir des valeurs par défaut correctes si absentes
# Forcer des URLs locales (mot de passe = 4 espaces directs, pas encodés)
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:    @localhost:5432/recruteur"
os.environ["DATABASE_URL_SYNC"] = "postgresql://postgres:    @localhost:5432/recruteur"

from app.db.database import AsyncSessionLocal
import subprocess
from app.models.user import User
from app.models.job_offer import JobOffer
from app.models.application import Application, ApplicationDocument, ApplicationHistory
from app.core.security.security import PasswordManager
from app.models.candidate_profile import CandidateProfile
from app.models.interview import InterviewSlot
from app.models.evaluation import Protocol1Evaluation, Protocol2Evaluation
from app.models.notification import Notification
from app.models.email import EmailLog
import base64


ADMIN_EMAIL = "sevankedesh11@gmail.com"
ADMIN_PASSWORD = "Sevan@Seeg"


async def seed():
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        # 1) Admin (vérifier si les tables existent, sinon exécuter migrations)
        try:
            admin = (await session.execute(select(User).where(User.email == ADMIN_EMAIL))).scalar_one_or_none()
        except Exception as e:
            # Si tables absentes (UndefinedTableError), tenter une migration Alembic
            if 'UndefinedTableError' in type(e).__name__ or 'relation' in str(e).lower():
                try:
                    # Utilise le Python courant pour exécuter alembic
                    subprocess.check_call([sys.executable, '-m', 'alembic', '-c', 'alembic.ini', 'upgrade', 'head'])
                except Exception:
                    raise e
                # Recréer une session après migration
                await session.close()
                async with AsyncSessionLocal() as session2:
                    admin = (await session2.execute(select(User).where(User.email == ADMIN_EMAIL))).scalar_one_or_none()
                    session = session2  # réutiliser pour la suite
            else:
                raise
        if not admin:
            admin = User(
                email=ADMIN_EMAIL,
                first_name="Sevan Kedesh",
                last_name="IKISSA PENDY",
                role="admin",
                hashed_password=PasswordManager.hash_password(ADMIN_PASSWORD),
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)

        # 2) Recruiter
        recruiter_email = "recruteur@test.local"
        recruiter = (await session.execute(select(User).where(User.email == recruiter_email))).scalar_one_or_none()
        if not recruiter:
            recruiter = User(
                email=recruiter_email,
                first_name="Jean",
                last_name="Mavoungou",
                role="recruiter",
                hashed_password=PasswordManager.hash_password("Recrut3ur#2025"),
            )
            session.add(recruiter)
            await session.commit()
            await session.refresh(recruiter)

        # 3) Candidate
        candidate_email = "candidate@test.local"
        candidate = (await session.execute(select(User).where(User.email == candidate_email))).scalar_one_or_none()
        if not candidate:
            candidate = User(
                email=candidate_email,
                first_name="Ada",
                last_name="Lovelace",
                role="candidate",
                hashed_password=PasswordManager.hash_password("Password#2025"),
            )
            session.add(candidate)
            await session.commit()
            await session.refresh(candidate)

        # 4) Job offer
        job = (await session.execute(select(JobOffer).where(JobOffer.title == "Ingénieur Systèmes"))).scalar_one_or_none()
        if not job:
            job = JobOffer(
                recruiter_id=recruiter.id,
                title="Ingénieur Systèmes",
                description="Gestion systèmes et réseaux",
                location="Libreville",
                contract_type="CDI",
                department="IT",
                requirements=["Linux", "Networking"],
                benefits=["Assurance", "Tickets restau"],
                responsibilities=["Maintenir infra", "Sécuriser SI"],
                status="open",
                application_deadline=datetime.utcnow() + timedelta(days=30),
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)

        # 5) Application
        application = (await session.execute(
            select(Application).where(
                Application.candidate_id == candidate.id,
                Application.job_offer_id == job.id,
            )
        )).scalar_one_or_none()
        if not application:
            application = Application(
                candidate_id=candidate.id,
                job_offer_id=job.id,
                status="pending",
            )
            session.add(application)
            await session.commit()

        # 6) Candidate profile
        profile = (await session.execute(select(CandidateProfile).where(CandidateProfile.user_id == candidate.id))).scalar_one_or_none()
        if not profile:
            profile = CandidateProfile(
                user_id=candidate.id,
                address="Quartier Centre, Libreville",
                availability="Immediate",
                current_department="IT",
                current_position="Analyste",
                education="Master Informatique",
                gender="F",
                years_experience=5,
                skills='["Linux","Networking","Python"]',
            )
            session.add(profile)
            await session.commit()

        # 7) Application documents (PDF factice)
        pdf_bytes = b"%PDF-1.4\n%Fake Minimal PDF for tests\n"
        existing_doc = (await session.execute(select(ApplicationDocument).where(ApplicationDocument.application_id == application.id))).scalar_one_or_none()
        if not existing_doc:
            doc = ApplicationDocument(
                application_id=application.id,
                document_type="cv",
                file_name="cv_candidate.pdf",
                file_data=pdf_bytes,
                file_size=len(pdf_bytes),
                file_type="application/pdf",
            )
            session.add(doc)
            await session.commit()

        # 8) Application history
        history = ApplicationHistory(
            application_id=application.id,
            changed_by=admin.id,
            previous_status="pending",
            new_status="reviewed",
            notes="Vérification initiale effectuée",
        )
        session.add(history)
        await session.commit()

        # 9) Interview slot
        slot = InterviewSlot(
            application_id=application.id,
            candidate_name=f"{candidate.first_name} {candidate.last_name}",
            job_title=job.title,
            date="2025-10-15",
            time="10:00:00",
            status="scheduled",
            is_available=False,
            location="Bureau RH",
            notes="Premier entretien",
        )
        session.add(slot)
        await session.commit()

        # 10) Evaluations
        p1 = (await session.execute(select(Protocol1Evaluation).where(Protocol1Evaluation.application_id == application.id))).scalar_one_or_none()
        if not p1:
            p1 = Protocol1Evaluation(
                application_id=application.id,
                evaluator_id=recruiter.id,
                status="completed",
                completed=True,
                documents_verified=True,
                cv_score=18.5,
                documentary_score=17.0,
                mtp_score=16.0,
                interview_score=15.0,
                overall_score=16.5,
                total_score=16.8,
                general_summary="Profil solide",
            )
            session.add(p1)
            await session.commit()

        p2 = (await session.execute(select(Protocol2Evaluation).where(Protocol2Evaluation.application_id == application.id))).scalar_one_or_none()
        if not p2:
            p2 = Protocol2Evaluation(
                application_id=application.id,
                evaluator_id=admin.id,
                completed=True,
                interview_completed=True,
                qcm_role_completed=True,
                qcm_codir_completed=True,
                qcm_role_score=17.0,
                qcm_codir_score=16.0,
                overall_score=16.5,
                interview_notes="Bonne communication",
                visit_notes="",
                skills_gap_notes="",
            )
            session.add(p2)
            await session.commit()

        # 11) Notification
        notif = Notification(
            user_id=candidate.id,
            related_application_id=application.id,
            title="Candidature mise à jour",
            message="Votre candidature a été revue",
            type="application",
            read=False,
        )
        session.add(notif)
        await session.commit()

        # 12) EmailLog
        email_log = EmailLog(
            application_id=application.id,
            to=candidate.email,
            subject="Confirmation de candidature",
            html="<p>Merci pour votre candidature</p>",
            category="application",
            sent_at=datetime.utcnow(),
            email_metadata={"provider": "dummy"},
        )
        session.add(email_log)
        await session.commit()


if __name__ == "__main__":
    # Config par défaut pour la DB si non fournie
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:%20%20%20%20@SEEG:5432/recruteur")
    asyncio.run(seed())


