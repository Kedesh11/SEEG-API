#!/usr/bin/env python3
"""Script pour tester si l'API a accès aux variables ETL"""
import httpx
import asyncio

async def test_env():
    print("\n🔍 Test des variables d'environnement de l'API...\n")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Tester un endpoint simple pour voir les logs
        try:
            response = await client.get("http://localhost:8000/health")
            print(f"✅ API accessible: {response.status_code}")
        except Exception as e:
            print(f"❌ API non accessible: {e}")
            return
    
    print("\n💡 Vérifiez dans les logs de l'API (terminal uvicorn):")
    print("   Vous devriez voir: [INFO] Chargement additionnel: .env.etl (configuration ETL)")
    print("\n   Si ce message n'apparaît pas, l'API doit être redémarrée.")

if __name__ == "__main__":
    asyncio.run(test_env())

