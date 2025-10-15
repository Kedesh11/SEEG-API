#!/usr/bin/env python3
"""
Script pour ajouter la clé primaire composite à application_drafts
"""
import asyncio
import sys
from sqlalchemy import text
from app.db.database import async_engine

async def add_primary_key():
    """Ajoute la clé primaire composite (user_id, job_offer_id)"""
    print("🔑 Ajout de la clé primaire à application_drafts...")
    
    async with async_engine.begin() as conn:
        try:
            # Supprimer toute contrainte de clé primaire existante
            print("🗑️  Suppression des contraintes existantes...")
            await conn.execute(text("""
                ALTER TABLE application_drafts DROP CONSTRAINT IF EXISTS application_drafts_pkey CASCADE
            """))
            
            # Ajouter la clé primaire composite
            print("➕ Ajout de la clé primaire composite (user_id, job_offer_id)...")
            await conn.execute(text("""
                ALTER TABLE application_drafts 
                ADD CONSTRAINT application_drafts_pkey PRIMARY KEY (user_id, job_offer_id)
            """))
            
            print("✅ Clé primaire ajoutée avec succès")
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            raise
        
        # Vérifier le résultat
        result = await conn.execute(text("""
            SELECT a.attname
            FROM   pg_index i
            JOIN   pg_attribute a ON a.attrelid = i.indrelid
                                 AND a.attnum = ANY(i.indkey)
            WHERE  i.indrelid = 'application_drafts'::regclass
            AND    i.indisprimary
        """))
        
        print("\n🔑 Clé primaire:")
        for row in result.fetchall():
            print(f"  - {row[0]}")
        
        print("\n✅ Configuration terminée!")

if __name__ == "__main__":
    try:
        asyncio.run(add_primary_key())
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

