"""
Tests for recommendation and destination endpoints
"""
import pytest
from fastapi.testclient import TestClient
from datetime import date, timedelta
from sqlalchemy.orm import Session


class TestDestinations:
    """Tests for destinations endpoints"""

    def test_list_destinations(self, client: TestClient):
        """Test listing all destinations"""
        response = client.get("/api/v1/destinations")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "name" in data[0]
        assert "country" in data[0]

    def test_list_destinations_with_query(self, client: TestClient):
        """Test searching destinations by query"""
        response = client.get("/api/v1/destinations?query=Paris")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert any("paris" in d["name"].lower() for d in data)

    def test_list_destinations_by_country(self, client: TestClient):
        """Test filtering destinations by country"""
        response = client.get("/api/v1/destinations?country=JP")
        assert response.status_code == 200
        data = response.json()
        assert all(d["country_code"] == "JP" for d in data)

    def test_list_destinations_max_results(self, client: TestClient):
        """Test limiting results"""
        response = client.get("/api/v1/destinations?max_results=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

    def test_get_destination_details(self, client: TestClient):
        """Test getting destination details"""
        response = client.get("/api/v1/destinations/paris_fr")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "paris_fr"
        assert data["name"] == "Paris"
        assert data["country"] == "France"

    def test_get_destination_not_found(self, client: TestClient):
        """Test getting non-existent destination"""
        response = client.get("/api/v1/destinations/nonexistent")
        assert response.status_code == 404

    def test_list_destinations_invalid_max_results(self, client: TestClient):
        """Test validation for max_results parameter"""
        response = client.get("/api/v1/destinations?max_results=0")
        assert response.status_code == 422

        response = client.get("/api/v1/destinations?max_results=200")
        assert response.status_code == 422


class TestHealthCheck:
    """Tests for health check endpoint"""

    def test_health_check(self, client: TestClient):
        """Test health check endpoint"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestVisaRequirements:
    """Tests for visa requirements endpoint"""

    def test_check_visa_requirements(self, client: TestClient):
        """Test checking visa requirements"""
        response = client.get("/api/v1/visa-requirements/US/FR")
        assert response.status_code == 200
        data = response.json()
        assert "visa" in data
        assert "summary" in data


class TestWeather:
    """Tests for weather endpoint"""

    def test_get_weather(self, client: TestClient):
        """Test getting weather for a location"""
        response = client.get("/api/v1/weather/48.8566/2.3522")
        assert response.status_code == 200
        data = response.json()
        assert "condition" in data
        assert "temperature" in data


class TestAttractions:
    """Tests for attractions endpoint"""

    def test_get_attractions(self, client: TestClient):
        """Test getting attractions for a location"""
        response = client.get("/api/v1/attractions/48.8566/2.3522")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_attractions_natural_only(self, client: TestClient):
        """Test getting natural attractions only"""
        response = client.get("/api/v1/attractions/48.8566/2.3522?natural_only=true")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
