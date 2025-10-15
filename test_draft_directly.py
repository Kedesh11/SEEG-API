#!/usr/bin/env python3
"""
Test direct de sauvegarde de brouillon sans passer par l'API
"""
import asyncio
import uuid
from sqlalchemy import text
from app.db.database import async_engine

async def test_draft_directly():
    """Test direct sur la base de données"""
    print("🧪 Test direct de sauvegarde de brouillon...")
    
    async with async_engine.begin() as conn:
        # Générer des UUIDs de test
        test_user_id = "37b2f065-71bb-4380-be60-72ba61671cd3"
        test_job_id = "d985cda1-05e8-4863-8add-709f37664944"
        
        # Supprimer le brouillon s'il existe
        print(f"🗑️  Nettoyage du brouillon existant...")
        await conn.execute(text("""
            DELETE FROM application_drafts 
            WHERE user_id = :user_id AND job_offer_id = :job_id
        """), {"user_id": test_user_id, "job_id": test_job_id})
        
        # Insérer un nouveau brouillon
        print(f"➕ Insertion d'un nouveau brouillon...")
        await conn.execute(text("""
            INSERT INTO application_drafts (user_id, job_offer_id, form_data, ui_state, created_at, updated_at)
            VALUES (:user_id, :job_id, :form_data, :ui_state, NOW(), NOW())
        """), {
            "user_id": test_user_id,
            "job_id": test_job_id,
            "form_data": '{"test": "data"}',
            "ui_state": '{"step": 1}'
        })
        print("✅ Brouillon inséré")
        
        # Lire le brouillon
        result = await conn.execute(text("""
            SELECT user_id, job_offer_id, form_data, ui_state, created_at, updated_at
            FROM application_drafts
            WHERE user_id = :user_id AND job_offer_id = :job_id
        """), {"user_id": test_user_id, "job_id": test_job_id})
        
        row = result.fetchone()
        if row:
            print("\n📋 Brouillon récupéré:")
            print(f"  - user_id: {row[0]}")
            print(f"  - job_offer_id: {row[1]}")
            print(f"  - form_data: {row[2]}")
            print(f"  - ui_state: {row[3]}")
            print(f"  - created_at: {row[4]}")
            print(f"  - updated_at: {row[5]}")
            
            print("\n✅ Test direct réussi!")
        else:
            print("\n❌ Brouillon non trouvé")

if __name__ == "__main__":
    try:
        asyncio.run(test_draft_directly())
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

