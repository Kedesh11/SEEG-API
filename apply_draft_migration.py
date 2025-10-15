#!/usr/bin/env python3
"""
Script pour appliquer la migration des timestamps sur application_drafts
"""
import asyncio
import sys
from sqlalchemy import text
from app.db.database import async_engine

async def apply_migration():
    """Applique la migration directement"""
    print("🔄 Application de la migration pour application_drafts...")
    
    async with async_engine.begin() as conn:
        # Vérifier si les colonnes existent
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='application_drafts' 
            AND column_name IN ('created_at', 'updated_at')
        """))
        existing_columns = [row[0] for row in result.fetchall()]
        
        print(f"📊 Colonnes existantes: {existing_columns}")
        
        # Ajouter created_at si elle n'existe pas
        if 'created_at' not in existing_columns:
            print("➕ Ajout de la colonne created_at...")
            await conn.execute(text("""
                ALTER TABLE application_drafts 
                ADD COLUMN created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            """))
            print("✅ Colonne created_at ajoutée")
        else:
            print("✓ Colonne created_at existe déjà")
        
        # Ajouter updated_at si elle n'existe pas
        if 'updated_at' not in existing_columns:
            print("➕ Ajout de la colonne updated_at...")
            await conn.execute(text("""
                ALTER TABLE application_drafts 
                ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            """))
            print("✅ Colonne updated_at ajoutée")
        else:
            print("✓ Colonne updated_at existe déjà")
        
        # Ajouter les commentaires
        print("📝 Ajout des commentaires...")
        await conn.execute(text("""
            COMMENT ON COLUMN application_drafts.created_at IS 'Date et heure de création du brouillon';
        """))
        await conn.execute(text("""
            COMMENT ON COLUMN application_drafts.updated_at IS 'Date et heure de dernière modification du brouillon';
        """))
        
        # Vérifier le résultat
        result = await conn.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name='application_drafts' 
            ORDER BY ordinal_position
        """))
        
        print("\n📋 Structure finale de application_drafts:")
        print("-" * 80)
        for row in result.fetchall():
            print(f"  {row[0]:20} {row[1]:30} NULL: {row[2]:5} DEFAULT: {row[3]}")
        print("-" * 80)
        
        print("\n✅ Migration appliquée avec succès!")

if __name__ == "__main__":
    try:
        asyncio.run(apply_migration())
    except Exception as e:
        print(f"\n❌ Erreur lors de la migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

