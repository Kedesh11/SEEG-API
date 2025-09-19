"""
Script pour créer le premier administrateur
"""
import asyncio
import sys
import os

# Ajouter le répertoire racine du projet au path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_async_session
from app.models.user import User
from app.core.security.security import PasswordManager
from sqlalchemy import select

async def create_first_admin():
    """Créer le premier administrateur"""
    async for db in get_async_session():
        try:
            # Vérifier si un admin existe déjà
            result = await db.execute(
                select(User).where(User.role == "admin")
            )
            existing_admin = result.scalar_one_or_none()
            
            if existing_admin:
                print(f"✅ Un administrateur existe déjà: {existing_admin.email}")
                return
            
            # Créer le premier admin
            password_manager = PasswordManager()
            hashed_password = password_manager.hash_password("Sevan@Seeg")
            
            admin = User(
                email="sevankedesh11@gmail.com",
                first_name="Sevan Kedesh",
                last_name="IKISSA PENDY",
                role="admin",
                hashed_password=hashed_password
            )
            
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
            
            print(f"✅ Premier administrateur créé avec succès:")
            print(f"   Email: {admin.email}")
            print(f"   Nom: {admin.first_name} {admin.last_name}")
            print(f"   Rôle: {admin.role}")
            print(f"   ID: {admin.id}")
            
        except Exception as e:
            print(f"❌ Erreur lors de la création de l'admin: {e}")
            await db.rollback()
        finally:
            await db.close()
        break

if __name__ == "__main__":
    asyncio.run(create_first_admin())
 