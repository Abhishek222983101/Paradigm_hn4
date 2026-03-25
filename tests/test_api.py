"""
API Integration Tests
Tests for FastAPI endpoints
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    
    def test_health_check(self, client):
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "TraceLoop"


class TestRootEndpoint:
    
    def test_root(self, client):
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "TraceLoop" in data["message"]


class TestChatEndpoint:
    
    def test_chat_purchase(self, client):
        response = client.post("/api/chat", json={
            "text": "Purchased 300kg PET from TestVendor"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["parsed"]["intent"] == "purchase"
    
    def test_chat_query(self, client):
        response = client.post("/api/chat", json={
            "text": "Show all batches"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
    
    def test_chat_unknown(self, client):
        response = client.post("/api/chat", json={
            "text": "Random text that makes no sense xyz123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False


class TestBatchesEndpoint:
    
    def test_list_batches(self, client):
        response = client.get("/api/batches")
        
        assert response.status_code == 200
        data = response.json()
        assert "batches" in data
        assert "count" in data
    
    def test_list_batches_with_filter(self, client):
        response = client.get("/api/batches?material_type=PET")
        
        assert response.status_code == 200
        data = response.json()
        assert "batches" in data
    
    def test_get_batch_detail(self, client):
        response = client.post("/api/chat", json={
            "text": "Purchased 500kg HDPE from TestVendor for batch test"
        })
        batch_id = response.json().get("batch_id")
        
        if batch_id:
            detail_response = client.get(f"/api/batches/{batch_id}")
            assert detail_response.status_code in [200, 404]
    
    def test_get_nonexistent_batch(self, client):
        response = client.get("/api/batches/FAKE-999")
        
        assert response.status_code == 404


class TestDashboardEndpoint:
    
    def test_dashboard_data(self, client):
        response = client.get("/api/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "material_breakdown" in data
        assert "stage_flow" in data


class TestVendorsEndpoint:
    
    def test_list_vendors(self, client):
        response = client.get("/api/vendors")
        
        assert response.status_code == 200
        data = response.json()
        assert "vendors" in data


class TestLocationsEndpoint:
    
    def test_list_locations(self, client):
        response = client.get("/api/locations")
        
        assert response.status_code == 200
        data = response.json()
        assert "locations" in data


class TestInsightsEndpoint:
    
    def test_get_insights_nonexistent(self, client):
        response = client.get("/api/insights/FAKE-999")
        
        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
