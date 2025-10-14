"""Test rapide de l'API locale"""
import requests

print("🔍 Test des routes API...\n")

# Test 1: Health check
try:
    r = requests.get("http://localhost:8000/monitoring/health", timeout=2)
    print(f"✅ /monitoring/health: {r.status_code}")
except Exception as e:
    print(f"❌ /monitoring/health: {e}")

# Test 2: Docs
try:
    r = requests.get("http://localhost:8000/docs", timeout=2)
    print(f"✅ /docs: {r.status_code}")
except Exception as e:
    print(f"❌ /docs: {e}")

# Test 3: Auth register v1
try:
    r = requests.post("http://localhost:8000/api/v1/auth/register", json={}, timeout=2)
    print(f"✅ /api/v1/auth/register: {r.status_code}")
except Exception as e:
    print(f"❌ /api/v1/auth/register: {e}")

# Test 4: Auth register sans préfixe
try:
    r = requests.post("http://localhost:8000/auth/register", json={}, timeout=2)
    print(f"✅ /auth/register: {r.status_code}")
except Exception as e:
    print(f"❌ /auth/register: {e}")

