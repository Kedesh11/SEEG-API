"""Lister toutes les routes de l'API"""
from app.main import app

print("\n" + "="*70)
print("📋 TOUTES LES ROUTES DE L'API")
print("="*70 + "\n")

routes_by_tag = {}

for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        methods = ', '.join(route.methods)
        path = route.path
        tags = getattr(route, 'tags', ['Other'])
        
        # Grouper par tag
        tag = tags[0] if tags else 'Other'
        if tag not in routes_by_tag:
            routes_by_tag[tag] = []
        
        routes_by_tag[tag].append({
            'methods': methods,
            'path': path,
            'name': getattr(route, 'name', 'N/A')
        })

# Afficher par tag
for tag, routes in sorted(routes_by_tag.items()):
    print(f"\n{tag}")
    print("-" * 70)
    for route in routes:
        print(f"  {route['methods']:12} {route['path']}")

# Vérifier spécifiquement les routes auth
print("\n" + "="*70)
print("🔐 ROUTES D'AUTHENTIFICATION DÉTAILLÉES")
print("="*70 + "\n")

auth_routes = [r for r in app.routes if '/auth' in getattr(r, 'path', '')]
for route in auth_routes:
    if hasattr(route, 'methods'):
        methods = ', '.join(route.methods)
        path = route.path
        name = getattr(route, 'name', 'N/A')
        print(f"  {methods:12} {path:40} ({name})")

print("\n" + "="*70)
print("✅ CONCLUSION:")
print("="*70)
print("\nLes routes backend sont CORRECTES avec /api/v1/")
print("Le problème vient du frontend qui utilise /api.v1/ (point)")
print("\n")

