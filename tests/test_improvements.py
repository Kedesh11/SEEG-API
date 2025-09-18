#!/usr/bin/env python3
"""
Script de test pour vérifier les améliorations des relations
"""
import asyncio
import time
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config.config import settings
from app.services.optimized_queries import OptimizedQueryService

async def test_improvements():
    """Tester les améliorations des relations"""
    
    # Configuration de la base de données
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        service = OptimizedQueryService(db)
        
        print("🚀 Test des améliorations des relations")
        print("=" * 50)
        
        # Test 1: Récupération des candidatures optimisées
        print("\n📊 Test 1: Récupération des candidatures optimisées")
        start_time = time.time()
        
        try:
            applications, total_count = await service.get_applications_with_full_data(
                limit=10,
                include_documents=True,
                include_evaluations=True
            )
            
            end_time = time.time()
            print(f"✅ {len(applications)} candidatures récupérées en {end_time - start_time:.4f}s")
            print(f"📈 Total disponible: {total_count}")
            
            if applications:
                app = applications[0]
                print(f"�� Exemple de données récupérées:")
                print(f"   - Candidat: {app['candidate']['first_name']} {app['candidate']['last_name']}")
                print(f"   - Offre: {app['job_offer']['title']}")
                print(f"   - Documents: {len(app['documents'])}")
                print(f"   - Historique: {len(app['history'])}")
                print(f"   - Entretiens: {len(app['interview_slots'])}")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        # Test 2: Statistiques du dashboard
        print("\n📊 Test 2: Statistiques du dashboard optimisées")
        start_time = time.time()
        
        try:
            stats = await service.get_dashboard_stats_optimized()
            end_time = time.time()
            
            print(f"✅ Statistiques récupérées en {end_time - start_time:.4f}s")
            print(f"📈 Offres d'emploi: {stats.get('total_jobs', 0)}")
            print(f"📈 Candidatures totales: {stats.get('total_applications', 0)}")
            print(f"📈 Candidats uniques: {stats.get('unique_candidates', 0)}")
            print(f"📈 Répartition par statut: {stats.get('status_breakdown', {})}")
            
            dept_stats = stats.get('department_stats', [])
            if dept_stats:
                print(f"📈 Statistiques par département:")
                for dept in dept_stats:
                    print(f"   - {dept['department']}: {dept['job_count']} offres, {dept['application_count']} candidatures")
                    
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        # Test 3: Candidatures d'un candidat
        print("\n📊 Test 3: Candidatures d'un candidat optimisées")
        
        try:
            # Récupérer un candidat existant
            from sqlalchemy import select
            from app.models.user import User
            
            result = await db.execute(select(User).where(User.role == 'candidate').limit(1))
            candidate = result.scalar_one_or_none()
            
            if candidate:
                start_time = time.time()
                applications = await service.get_candidate_applications_optimized(str(candidate.id))
                end_time = time.time()
                
                print(f"✅ {len(applications)} candidatures récupérées pour {candidate.first_name} {candidate.last_name} en {end_time - start_time:.4f}s")
                
                if applications:
                    app = applications[0]
                    print(f"🔍 Exemple de candidature:")
                    print(f"   - Offre: {app['job_offer']['title']}")
                    print(f"   - Statut: {app['status']}")
                    print(f"   - Documents: {len(app['documents'])}")
                    print(f"   - Entretiens: {len(app['interview_slots'])}")
            else:
                print("⚠️ Aucun candidat trouvé pour le test")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")
        
        # Test 4: Vérification des index
        print("\n📊 Test 4: Vérification des index de performance")
        
        try:
            from sqlalchemy import text
            
            # Vérifier que les index ont été créés
            index_query = text("""
                SELECT indexname, tablename, indexdef 
                FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND indexname LIKE 'idx_%'
                ORDER BY tablename, indexname;
            """)
            
            result = await db.execute(index_query)
            indexes = result.fetchall()
            
            print(f"✅ {len(indexes)} index de performance trouvés:")
            for idx in indexes:
                print(f"   - {idx.indexname} sur {idx.tablename}")
                
        except Exception as e:
            print(f"❌ Erreur lors de la vérification des index: {e}")
    
    await engine.dispose()
    print("\n🎉 Tests terminés!")

if __name__ == "__main__":
    asyncio.run(test_improvements())
