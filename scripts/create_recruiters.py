"""
Script pour créer les recruteurs dans la base de données
"""
import asyncio
import sys
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import AsyncSessionLocal
from app.services.auth import AuthService
from app.schemas.auth import CreateUserRequest
from sqlalchemy import select
from app.models.user import User


async def create_recruiters():
    """Créer les recruteurs dans la base de données"""
    
    recruiters_data = [
        {
            "first_name": "Axel",
            "last_name": "Fouty",
            "email": "foutyaxel9@gmail.com",
            "password": "RecruteurAxel2024!",  # Mot de passe temporaire
            "role": "recruiter"
        },
        {
            "first_name": "Jessy",
            "last_name": "LOUEMBET",
            "email": "jessy@cnx4-0.com",
            "password": "RecruteurJessy2024!",  # Mot de passe temporaire
            "role": "recruiter"
        }
    ]
    
    print("\n" + "="*60)
    print("CREATION DES RECRUTEURS")
    print("="*60 + "\n")
    
    async with AsyncSessionLocal() as db:
        auth_service = AuthService(db)
        
        for idx, recruiter_info in enumerate(recruiters_data, 1):
            try:
                # Vérifier si l'utilisateur existe déjà
                result = await db.execute(
                    select(User).where(User.email == recruiter_info["email"])
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    print(f"❌ Recruteur {idx} : {recruiter_info['email']}")
                    print(f"   Existe déjà dans la base de données")
                    print(f"   ID: {existing_user.id}")
                    print()
                    continue
                
                # Créer le recruteur
                user_data = CreateUserRequest(**recruiter_info)
                user = await auth_service.create_user(user_data)
                
                # Commit la transaction
                await db.commit()
                await db.refresh(user)
                
                print(f"✅ Recruteur {idx} créé avec succès !")
                print(f"   Nom: {user.first_name} {user.last_name}")
                print(f"   Email: {user.email}")
                print(f"   Rôle: {user.role}")
                print(f"   ID: {user.id}")
                print(f"   Mot de passe temporaire: {recruiter_info['password']}")
                print(f"   ⚠️  Demandez au recruteur de changer son mot de passe !")
                print()
                
            except Exception as e:
                print(f"❌ Erreur lors de la création du recruteur {idx}")
                print(f"   Email: {recruiter_info['email']}")
                print(f"   Erreur: {str(e)}")
                print()
                await db.rollback()
    
    print("="*60)
    print("CREATION TERMINEE")
    print("="*60 + "\n")


if __name__ == "__main__":
    print("\n🚀 Démarrage du script de création des recruteurs...\n")
    asyncio.run(create_recruiters())
    print("✅ Script terminé !\n")

