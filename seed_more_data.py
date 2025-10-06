"""
Script pour générer beaucoup plus de fake data dans la base de données
"""
import asyncio
import sys
import random
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
from app.models.notification import Notification
from app.models.interview import InterviewSlot
from app.core.security.security import PasswordManager

# Données fictives pour génération
FIRST_NAMES = [
    "Marie", "Jean", "Fatou", "Moussa", "Ada", "Pierre", "Aminata", "Ibrahim",
    "Sophie", "François", "Aïcha", "Omar", "Claire", "Mamadou", "Rachelle", "Youssouf",
    "Nadège", "Antoine", "Bintou", "Samba", "Émilie", "Boubacar", "Rosine", "Abdoul"
]

LAST_NAMES = [
    "Mavoungou", "Lovelace", "N'Dong", "Obiang", "Ella", "Nguema", "Oyono", "Bongo",
    "Allogho", "Mintsa", "Bekale", "Ondo", "Moussavou", "Dzondo", "Nzé", "Makaya",
    "Bounda", "Nkoghé", "Kombila", "Mangongo", "Moussounda", "Zogo", "Essono", "Yembit"
]

DEPARTMENTS = ["IT", "RH", "Finance", "Commercial", "Technique", "Logistique", "Marketing", "Production"]

POSITIONS = [
    "Développeur", "Analyste", "Chef de projet", "Technicien", "Ingénieur",
    "Responsable", "Consultant", "Assistant", "Manager", "Coordinateur"
]

SKILLS = [
    "Python", "JavaScript", "SQL", "Linux", "Networking", "PostgreSQL", "Docker",
    "FastAPI", "React", "Git", "AWS", "Azure", "Gestion de projet", "Communication",
    "Leadership", "Analyse de données", "Sécurité", "DevOps", "Agile", "Scrum"
]

JOB_TITLES = [
    "Développeur Full Stack", "Ingénieur Systèmes", "Analyste de données",
    "Chef de projet IT", "Administrateur réseaux", "Technicien support",
    "Responsable RH", "Gestionnaire comptable", "Chargé de communication",
    "Ingénieur qualité", "Responsable logistique", "Commercial terrain",
    "Développeur Backend", "Développeur Frontend", "Architecte solutions"
]

JOB_DESCRIPTIONS = [
    "Rejoignez notre équipe dynamique pour contribuer à des projets innovants.",
    "Nous recherchons un professionnel expérimenté pour renforcer notre équipe.",
    "Poste stratégique au sein d'une entreprise en pleine croissance.",
    "Opportunité unique de développer vos compétences dans un environnement stimulant.",
    "Participez à la transformation digitale de la SEEG."
]

CITIES = ["Libreville", "Port-Gentil", "Franceville", "Oyem", "Moanda", "Mouila", "Lambaréné"]

CONTRACT_TYPES = ["CDI", "CDD", "Stage", "Alternance"]

APPLICATION_STATUSES = ["pending", "reviewed", "shortlisted", "interviewed", "accepted", "rejected"]

async def seed_more_data():
    """Générer beaucoup plus de fake data"""
    
    database_url = "postgresql+asyncpg://postgres:    @localhost:5432/recruteur"
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("🔄 Génération de fake data supplémentaires...\n")
    
    async with async_session() as session:
        try:
            # Récupérer les utilisateurs existants
            result = await session.execute(select(User))
            existing_users = result.scalars().all()
            existing_emails = {u.email for u in existing_users}
            
            recruiters = [u for u in existing_users if u.role == "recruiter"]
            if not recruiters:
                print("⚠ Aucun recruteur trouvé, création d'un recruteur par défaut...")
                recruiter = User(
                    email="recruiter.default@seeg.ga",
                    first_name="Recruteur",
                    last_name="Par Défaut",
                    role="recruiter",
                    phone="+24107000000",
                    hashed_password=PasswordManager.hash_password("Password123!")
                )
                session.add(recruiter)
                await session.flush()
                recruiters = [recruiter]
            
            print(f"✓ {len(recruiters)} recruteur(s) disponible(s)")
            
            # 1. Créer plus de candidats
            print("\n📝 Création de 20 candidats supplémentaires...")
            new_candidates = []
            for i in range(20):
                email = f"candidate{i+10}@seeg.ga"
                if email in existing_emails:
                    continue
                    
                first_name = random.choice(FIRST_NAMES)
                last_name = random.choice(LAST_NAMES)
                
                candidate = User(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    role="candidate",
                    phone=f"+2410{random.randint(1000000, 9999999)}",
                    hashed_password=PasswordManager.hash_password("Password123!")
                )
                session.add(candidate)
                new_candidates.append(candidate)
            
            await session.flush()
            print(f"  ✓ {len(new_candidates)} candidats créés")
            
            # 2. Créer des profils pour les nouveaux candidats
            print("\n📋 Création des profils candidats...")
            for candidate in new_candidates:
                profile = CandidateProfile(
                    user_id=candidate.id,
                    address=f"{random.choice(['Quartier Centre', 'Quartier Résidentiel', 'Zone Industrielle'])}, {random.choice(CITIES)}",
                    availability=random.choice(["Immédiate", "1 mois", "2 mois", "Négociable"]),
                    current_department=random.choice(DEPARTMENTS),
                    current_position=random.choice(POSITIONS),
                    education=random.choice(["Bac+2", "Bac+3", "Bac+5", "Master", "Doctorat"]),
                    gender=random.choice(["M", "F"]),
                    years_experience=random.randint(0, 15),
                    skills=str(random.sample(SKILLS, k=random.randint(3, 8)))
                )
                session.add(profile)
            
            await session.flush()
            print(f"  ✓ {len(new_candidates)} profils créés")
            
            # 3. Créer plus d'offres d'emploi
            print("\n💼 Création de 15 offres d'emploi...")
            new_jobs = []
            for i in range(15):
                recruiter = random.choice(recruiters)
                job_title = random.choice(JOB_TITLES)
                
                job = JobOffer(
                    recruiter_id=recruiter.id,
                    title=f"{job_title} - {random.choice(['Expérimenté', 'Junior', 'Senior', 'Confirmé'])}",
                    description=random.choice(JOB_DESCRIPTIONS),
                    location=random.choice(CITIES),
                    contract_type=random.choice(CONTRACT_TYPES),
                    department=random.choice(DEPARTMENTS),
                    requirements=random.sample(SKILLS, k=random.randint(3, 6)),
                    benefits=random.sample([
                        "Assurance santé", "Tickets restaurant", "Prime annuelle",
                        "Formation continue", "Télétravail partiel", "Mutuelle famille"
                    ], k=random.randint(2, 4)),
                    responsibilities=random.sample([
                        "Développer des solutions innovantes",
                        "Gérer une équipe",
                        "Assurer le support technique",
                        "Participer aux réunions stratégiques",
                        "Maintenir la documentation",
                        "Former les nouveaux collaborateurs"
                    ], k=random.randint(2, 4)),
                    status=random.choice(["open", "open", "open", "closed"]),  # Plus de chances d'être ouvert
                    application_deadline=datetime.now(timezone.utc) + timedelta(days=random.randint(15, 90)),
                    salary_min=random.randint(300000, 800000),
                    salary_max=random.randint(800000, 2000000)
                )
                session.add(job)
                new_jobs.append(job)
            
            await session.flush()
            print(f"  ✓ {len(new_jobs)} offres d'emploi créées")
            
            # 4. Récupérer tous les candidats et offres
            result = await session.execute(select(User).where(User.role == "candidate"))
            all_candidates = result.scalars().all()
            
            result = await session.execute(select(JobOffer))
            all_jobs = result.scalars().all()
            
            # 5. Créer des candidatures
            print("\n📨 Création de 50 candidatures...")
            applications_created = 0
            
            for _ in range(50):
                candidate = random.choice(all_candidates)
                job = random.choice(all_jobs)
                
                # Vérifier si candidature existe déjà
                result = await session.execute(
                    select(Application).where(
                        Application.candidate_id == candidate.id,
                        Application.job_offer_id == job.id
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    application = Application(
                        candidate_id=candidate.id,
                        job_offer_id=job.id,
                        status=random.choice(APPLICATION_STATUSES),
                        reference_contacts=f"Référence: +2410{random.randint(1000000, 9999999)}",
                        availability_start=datetime.now(timezone.utc) + timedelta(days=random.randint(1, 60))
                    )
                    session.add(application)
                    applications_created += 1
            
            await session.flush()
            print(f"  ✓ {applications_created} candidatures créées")
            
            # 6. Ajouter quelques documents PDF fictifs
            print("\n📄 Ajout de documents PDF aux candidatures...")
            result = await session.execute(select(Application).limit(20))
            sample_applications = result.scalars().all()
            
            pdf_content = b"%PDF-1.4\n%Fake CV PDF for testing\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            
            docs_created = 0
            for app in sample_applications:
                if random.random() > 0.3:  # 70% des candidatures ont des documents
                    # CV
                    cv_doc = ApplicationDocument(
                        application_id=app.id,
                        document_type="cv",
                        file_name=f"CV_{app.id}.pdf",
                        file_data=pdf_content,
                        file_size=len(pdf_content),
                        file_type="application/pdf"
                    )
                    session.add(cv_doc)
                    docs_created += 1
                    
                    if random.random() > 0.5:  # 50% ont aussi une lettre de motivation
                        lm_doc = ApplicationDocument(
                            application_id=app.id,
                            document_type="cover_letter",
                            file_name=f"Lettre_Motivation_{app.id}.pdf",
                            file_data=pdf_content,
                            file_size=len(pdf_content),
                            file_type="application/pdf"
                        )
                        session.add(lm_doc)
                        docs_created += 1
            
            await session.flush()
            print(f"  ✓ {docs_created} documents PDF créés")
            
            # 7. Créer des notifications pour certains candidats
            print("\n🔔 Création de notifications...")
            notifs_created = 0
            
            for candidate in random.sample(all_candidates, min(30, len(all_candidates))):
                notif = Notification(
                    user_id=candidate.id,
                    title=random.choice([
                        "Nouvelle offre disponible",
                        "Votre candidature a été vue",
                        "Mise à jour de statut",
                        "Entretien planifié"
                    ]),
                    message=random.choice([
                        "Une nouvelle offre correspondant à votre profil est disponible.",
                        "Votre candidature a été consultée par un recruteur.",
                        "Le statut de votre candidature a été mis à jour.",
                        "Un entretien a été planifié pour votre candidature."
                    ]),
                    type=random.choice(["application", "job", "interview", "system"]),
                    read=random.choice([True, False])
                )
                session.add(notif)
                notifs_created += 1
            
            await session.flush()
            print(f"  ✓ {notifs_created} notifications créées")
            
            # 8. Créer des créneaux d'entretien
            print("\n🎯 Création de créneaux d'entretien...")
            result = await session.execute(
                select(Application).where(
                    Application.status.in_(["shortlisted", "interviewed"])
                ).limit(15)
            )
            interview_applications = result.scalars().all()
            
            interviews_created = 0
            for app in interview_applications:
                interview_date = datetime.now(timezone.utc) + timedelta(days=random.randint(1, 30))
                interview = InterviewSlot(
                    application_id=app.id,
                    candidate_name=f"{app.candidate.first_name} {app.candidate.last_name}" if app.candidate else "N/A",
                    job_title=app.job_offer.title if app.job_offer else "N/A",
                    date=interview_date.strftime("%Y-%m-%d"),
                    time=f"{random.randint(8, 17):02d}:00:00",
                    status=random.choice(["scheduled", "completed", "cancelled"]),
                    is_available=False,
                    location=random.choice(["Bureau RH", "Salle de réunion A", "Visioconférence", "Site production"]),
                    notes=random.choice(["RAS", "Confirmer par email", "Prévoir 1h", ""])
                )
                session.add(interview)
                interviews_created += 1
            
            await session.flush()
            print(f"  ✓ {interviews_created} entretiens planifiés")
            
            await session.commit()
            
            print("\n" + "="*60)
            print("✅ GÉNÉRATION TERMINÉE AVEC SUCCÈS!")
            print("="*60)
            print(f"\n📊 Résumé des données générées:")
            print(f"  • Candidats: {len(new_candidates)}")
            print(f"  • Profils: {len(new_candidates)}")
            print(f"  • Offres d'emploi: {len(new_jobs)}")
            print(f"  • Candidatures: {applications_created}")
            print(f"  • Documents PDF: {docs_created}")
            print(f"  • Notifications: {notifs_created}")
            print(f"  • Entretiens: {interviews_created}")
            print(f"\n🎉 La base de données est maintenant bien remplie!")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ Erreur lors de la génération:")
            print(f"  {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            await session.close()
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_more_data())
