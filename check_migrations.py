import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_migrations():
    # Connection string for local database
    db_url = "postgresql+asyncpg://postgres:    @localhost:5432/recruteur"
    
    try:
        engine = create_async_engine(db_url, echo=False)
        
        async with engine.begin() as conn:
            # Check if alembic_version table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'alembic_version'
                )
            """))
            table_exists = result.scalar()
            
            if table_exists:
                # Get current migration version
                result = await conn.execute(text("SELECT version_num FROM alembic_version"))
                version = result.scalar_one_or_none()
                
                if version:
                    print(f"✓ Migrations appliquées - Version actuelle: {version}")
                else:
                    print("⚠ Table alembic_version existe mais est vide")
            else:
                print("✗ Table alembic_version n'existe pas - Migrations non appliquées")
                
            # Check if main tables exist
            tables_to_check = ['users', 'job_offers', 'applications', 'application_documents']
            print("\nVérification des tables principales:")
            for table_name in tables_to_check:
                result = await conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table_name}'
                    )
                """))
                exists = result.scalar()
                status = "✓" if exists else "✗"
                print(f"  {status} Table '{table_name}': {'existe' if exists else 'manquante'}")
        
        await engine.dispose()
        
    except Exception as e:
        print(f"✗ Erreur de connexion à la base de données:")
        print(f"  {type(e).__name__}: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(check_migrations())
