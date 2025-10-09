"""
Script pour créer les recruteurs APRÈS application des migrations
À exécuter: python scripts/create_recruiters_after_migration.py
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
import structlog

logger = structlog.get_logger(__name__)


async def create_recruiters():
    """Créer les recruteurs dans la base de données"""
    
    users_data = [
        {
            "first_name": "Axel",
            "last_name": "Fouty",
            "email": "foutyaxel9@gmail.com",
            "password": "Axel@Recruteur",  # Mot de passe temporaire à changer
            "role": "recruiter",
            "phone": "+241066000001"
        },
        {
            "first_name": "Jessy",
            "last_name": "LOUEMBET",
            "email": "jessy@cnx4-0.com",
            "password": "Pass1234",  # Mot de passe temporaire à changer
            "role": "recruiter",
            "phone": "+241066000002"
        },
        {
            "first_name": "Steeve Saurel",
            "last_name": "LEGNONGO",
            "email": "slegnongo@seeg-gabon.com",
            "password": "steeve@Seeg",  # Mot de passe temporaire à changer
            "role": "observer",
            "phone": "+241066000003"
        }
    ]
    
    print("\n" + "="*70)
    print("       CREATION DES UTILISATEURS - ONE HCM SEEG")
    print("       (Recruteurs + Observateurs)")
    print("="*70 + "\n")
    
    created_count = 0
    existing_count = 0
    error_count = 0
    
    async with AsyncSessionLocal() as db:
        auth_service = AuthService(db)
        
        for idx, user_info in enumerate(users_data, 1):
            try:
                # Vérifier si l'utilisateur existe déjà
                result = await db.execute(
                    select(User).where(User.email == user_info["email"])
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    print(f"[{idx}/3] Utilisateur : {user_info['first_name']} {user_info['last_name']}")
                    print(f"        Email       : {user_info['email']}")
                    print(f"        Status      : ⚠️  EXISTE DEJA")
                    print(f"        ID          : {existing_user.id}")
                    print(f"        Role        : {existing_user.role}")
                    print()
                    existing_count += 1
                    continue
                
                # Créer l'utilisateur
                user_data = CreateUserRequest(**user_info)
                user = await auth_service.create_user(user_data)
                
                # Commit la transaction
                await db.commit()
                await db.refresh(user)
                
                print(f"[{idx}/3] Utilisateur : {user.first_name} {user.last_name}")
                print(f"        Email       : {user.email}")
                print(f"        Status      : ✅ CREE AVEC SUCCES")
                print(f"        ID          : {user.id}")
                print(f"        Role        : {user.role}")
                print(f"        Phone       : {user.phone}")
                print(f"        Password    : {user_info['password']}")
                print(f"        ⚠️  IMPORTANT: Demandez a l'utilisateur de changer son mot de passe !")
                print()
                created_count += 1
                
            except Exception as e:
                print(f"[{idx}/3] Utilisateur : {user_info['first_name']} {user_info['last_name']}")
                print(f"        Email       : {user_info['email']}")
                print(f"        Status      : ❌ ERREUR")
                print(f"        Erreur      : {str(e)}")
                print()
                error_count += 1
                await db.rollback()
    
    print("="*70)
    print("                         RESULTAT")
    print("="*70)
    print(f"  Utilisateurs crees     : {created_count}")
    print(f"    - Recruteurs         : 2")
    print(f"    - Observateurs       : 1")
    print(f"  Deja existants         : {existing_count}")
    print(f"  Erreurs                : {error_count}")
    print("="*70 + "\n")
    
    if created_count > 0:
        print("⚠️  N'OUBLIEZ PAS :")
        print("   1. Demandez aux utilisateurs de changer leurs mots de passe")
        print("   2. Verifiez leurs acces dans l'application")
        print("   3. Roles crees : recruiter (x2) + observer (x1)")
        print()


if __name__ == "__main__":
    print("\n🚀 Demarrage du script de creation des utilisateurs...\n")
    try:
        asyncio.run(create_recruiters())
        print("✅ Script termine avec succes !\n")
    except Exception as e:
        print(f"\n❌ Erreur critique: {str(e)}\n")
        sys.exit(1)

