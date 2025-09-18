#!/usr/bin/env python3
"""
Test simple de l'API
"""
import asyncio
import sys
from app.core.config import settings

def test_config():
    """Test de la configuration"""
    print("🔍 Test de la configuration...")
    
    try:
        print(f"  ✅ App: {settings.APP_NAME}")
        print(f"  ✅ Version: {settings.APP_VERSION}")
        print(f"  ✅ CORS: {settings.ALLOWED_ORIGINS}")
        print(f"  ✅ Frontend autorisé: {'https://www.seeg-talentsource.com' in settings.ALLOWED_ORIGINS}")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def test_imports():
    """Test des imports"""
    print("🔍 Test des imports...")
    
    try:
        from app.main_simple import app
        print("  ✅ Application FastAPI importée")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    """Fonction principale"""
    print("🚀 TEST API SIMPLE")
    print("=" * 40)
    
    tests = [
        ("Configuration", test_config),
        ("Imports", test_imports),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 20)
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 40)
    print("📊 RÉSULTATS")
    print("=" * 40)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<20} {status}")
        if not result:
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 SUCCÈS!")
        print("✅ L'API est prête")
        print("🌐 URL locale: http://localhost:8001")
        print("📚 Documentation: http://localhost:8001/docs")
        print("🔍 Health check: http://localhost:8001/health")
        print("ℹ️  Info: http://localhost:8001/info")
    else:
        print("⚠️ ÉCHECS DÉTECTÉS")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
