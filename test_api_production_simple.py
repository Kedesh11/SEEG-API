"""
Test simple de l'API en production Azure
=========================================
Teste les endpoints publics et identifie les problèmes
"""
import asyncio
import httpx
import json

API_BASE_URL = "https://seeg-backend-api.azurewebsites.net"

async def test_api_simple():
    """Test simple des endpoints de base."""
    print("\n" + "="*80)
    print("🧪 TEST API PRODUCTION - Endpoints de base")
    print("="*80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Documentation Swagger (public)
        print("\n📝 Test 1: Documentation Swagger")
        try:
            response = await client.get(f"{API_BASE_URL}/docs")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ Swagger accessible")
            else:
                print(f"   ❌ Erreur {response.status_code}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        # Test 2: Endpoint public - Liste des offres d'emploi
        print("\n📝 Test 2: GET /api/v1/public/jobs (public, sans auth)")
        try:
            response = await client.get(f"{API_BASE_URL}/api/v1/public/jobs")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Endpoint public fonctionne")
                print(f"   Nombre d'offres: {len(data.get('data', []))}")
            else:
                print(f"   ❌ Erreur {response.status_code}")
                print(f"   Réponse: {response.text[:200]}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        # Test 3: Login endpoint (pour voir s'il fonctionne)
        print("\n📝 Test 3: POST /api/v1/auth/login (test structure)")
        try:
            # Test avec credentials invalides pour voir la structure de réponse
            response = await client.post(
                f"{API_BASE_URL}/api/v1/auth/login",
                json={"email": "test@test.com", "password": "test"}
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 401:
                print(f"   ✅ Endpoint login répond (401 = credentials invalides, normal)")
            elif response.status_code == 500:
                print(f"   ❌ ERREUR 500 sur login")
                print(f"   Réponse: {response.text[:300]}")
            else:
                print(f"   Status: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    print("\n" + "="*80)
    print("🏁 TEST TERMINÉ")
    print("="*80)
    print("\n💡 Pour tester les endpoints authentifiés:")
    print("   1. Créez un utilisateur de test en production")
    print("   2. Modifiez test_users_endpoint_azure.py avec les credentials")
    print("   3. Lancez: python test_users_endpoint_azure.py")

if __name__ == "__main__":
    asyncio.run(test_api_simple())

