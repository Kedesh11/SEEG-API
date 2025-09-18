"""
Tests pour les endpoints optimisés
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from app.main import app
from app.services.optimized_queries import OptimizedQueryService

client = TestClient(app)

class TestOptimizedEndpoints:
    """Tests pour les endpoints optimisés"""
    
    def test_optimized_endpoints_import(self):
        """Tester que les endpoints optimisés sont bien importés"""
        # Vérifier que l'application contient les routes optimisées
        routes = [route.path for route in app.routes]
        optimized_routes = [route for route in routes if '/optimized' in route]
        
        assert len(optimized_routes) > 0, "Aucune route optimisée trouvée"
        print(f"✅ Routes optimisées trouvées: {optimized_routes}")
    
    @patch('app.api.v1.endpoints.optimized.get_current_user')
    @patch('app.api.v1.endpoints.optimized.get_async_session')
    def test_applications_optimized_endpoint(self, mock_session, mock_user):
        """Tester l'endpoint des candidatures optimisées"""
        # Mock des dépendances
        mock_user.return_value = AsyncMock()
        mock_user.return_value.role = 'admin'
        
        mock_db = AsyncMock(spec=AsyncSession)
        mock_session.return_value.__aenter__.return_value = mock_db
        
        # Mock du service
        with patch('app.api.v1.endpoints.optimized.OptimizedQueryService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_applications_with_full_data.return_value = ([], 0)
            
            response = client.get("/api/v1/optimized/applications/optimized")
            
            assert response.status_code == 200
            data = response.json()
            assert "applications" in data
            assert "total_count" in data
            assert data["total_count"] == 0
    
    @patch('app.api.v1.endpoints.optimized.get_current_user')
    @patch('app.api.v1.endpoints.optimized.get_async_session')
    def test_dashboard_stats_optimized_endpoint(self, mock_session, mock_user):
        """Tester l'endpoint des statistiques optimisées"""
        # Mock des dépendances
        mock_user.return_value = AsyncMock()
        mock_user.return_value.role = 'admin'
        
        mock_db = AsyncMock(spec=AsyncSession)
        mock_session.return_value.__aenter__.return_value = mock_db
        
        # Mock du service
        with patch('app.api.v1.endpoints.optimized.OptimizedQueryService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_dashboard_stats_optimized.return_value = {
                'total_jobs': 0,
                'total_applications': 0,
                'unique_candidates': 0
            }
            
            response = client.get("/api/v1/optimized/dashboard/stats/optimized")
            
            assert response.status_code == 200
            data = response.json()
            assert "stats" in data
            assert data["stats"]["total_jobs"] == 0
    
    @patch('app.api.v1.endpoints.optimized.get_current_user')
    @patch('app.api.v1.endpoints.optimized.get_async_session')
    def test_candidate_applications_optimized_endpoint(self, mock_session, mock_user):
        """Tester l'endpoint des candidatures candidat optimisées"""
        # Mock des dépendances
        mock_user.return_value = AsyncMock()
        mock_user.return_value.role = 'admin'
        
        mock_db = AsyncMock(spec=AsyncSession)
        mock_session.return_value.__aenter__.return_value = mock_db
        
        # Mock du service
        with patch('app.api.v1.endpoints.optimized.OptimizedQueryService') as mock_service:
            mock_service_instance = AsyncMock()
            mock_service.return_value = mock_service_instance
            mock_service_instance.get_candidate_applications_optimized.return_value = []
            
            response = client.get("/api/v1/optimized/candidates/test-id/applications/optimized")
            
            assert response.status_code == 200
            data = response.json()
            assert "candidate_id" in data
            assert "applications" in data
            assert data["candidate_id"] == "test-id"
    
    def test_performance_comparison_endpoint_unauthorized(self):
        """Tester que l'endpoint de comparaison de performance nécessite des droits admin"""
        response = client.get("/api/v1/optimized/performance/comparison")
        
        # Devrait retourner 401 ou 403 car pas d'authentification
        assert response.status_code in [401, 403]
    
    @patch('app.api.v1.endpoints.optimized.get_current_user')
    def test_performance_comparison_endpoint_authorized(self, mock_user):
        """Tester l'endpoint de comparaison de performance avec droits admin"""
        # Mock des dépendances
        mock_user.return_value = AsyncMock()
        mock_user.return_value.role = 'admin'
        
        response = client.get("/api/v1/optimized/performance/comparison")
        
        assert response.status_code == 200
        data = response.json()
        assert "comparison" in data
        assert "recommendations" in data
        assert "old_approach_time" in data["comparison"]
        assert "new_approach_time" in data["comparison"]

class TestOptimizedQueryService:
    """Tests pour le service de requêtes optimisées"""
    
    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Tester l'initialisation du service"""
        mock_db = AsyncMock(spec=AsyncSession)
        service = OptimizedQueryService(mock_db)
        
        assert service.db == mock_db
        print("✅ Service OptimizedQueryService initialisé correctement")
    
    @pytest.mark.asyncio
    async def test_get_applications_with_full_data_empty(self):
        """Tester la récupération des candidatures avec données vides"""
        mock_db = AsyncMock(spec=AsyncSession)
        service = OptimizedQueryService(mock_db)
        
        # Mock des résultats de requête
        mock_result = AsyncMock()
        mock_result.unique.return_value.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # Mock du count
        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 0
        mock_db.execute.return_value = mock_count_result
        
        applications, total_count = await service.get_applications_with_full_data(limit=10)
        
        assert applications == []
        assert total_count == 0
        print("✅ Service gère correctement les données vides")
    
    @pytest.mark.asyncio
    async def test_get_dashboard_stats_optimized_empty(self):
        """Tester les statistiques du dashboard avec données vides"""
        mock_db = AsyncMock(spec=AsyncSession)
        service = OptimizedQueryService(mock_db)
        
        # Mock des résultats de requête
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        stats = await service.get_dashboard_stats_optimized()
        
        assert "total_jobs" in stats
        assert "total_applications" in stats
        assert "unique_candidates" in stats
        assert stats["total_jobs"] == 0
        print("✅ Service gère correctement les statistiques vides")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
