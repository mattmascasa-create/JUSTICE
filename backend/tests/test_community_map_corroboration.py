"""
Test Community Incident Map and AI Witness Corroboration APIs
Tests for iteration 42 - Community Map and Corroboration features
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "password123"
TEST_ENCOUNTER_ID = "enc_191bdcbb293a"  # Known encounter for testing


class TestCommunityMapPublicEndpoints:
    """Community Map API tests - Public endpoints (no auth required)"""
    
    def test_get_incidents(self):
        """GET /api/community-map/incidents - returns incident data"""
        response = requests.get(f"{BASE_URL}/api/community-map/incidents")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        assert "incidents" in data
        assert "count" in data
        assert isinstance(data["incidents"], list)
        print(f"✓ GET /api/community-map/incidents - returned {data['count']} incidents")
    
    def test_get_incidents_with_filters(self):
        """GET /api/community-map/incidents - with filter parameters"""
        params = {
            "radius_miles": 25,
            "days": 60,
            "limit": 100
        }
        response = requests.get(f"{BASE_URL}/api/community-map/incidents", params=params)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        assert data.get("filters", {}).get("radius_miles") == 25
        assert data.get("filters", {}).get("days") == 60
        print(f"✓ GET /api/community-map/incidents with filters - returned {data['count']} incidents")
    
    def test_get_incidents_with_type_filter(self):
        """GET /api/community-map/incidents - filter by incident type"""
        params = {
            "incident_types": "traffic_stop,arrest"
        }
        response = requests.get(f"{BASE_URL}/api/community-map/incidents", params=params)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        print(f"✓ GET /api/community-map/incidents with type filter - returned {data['count']} incidents")
    
    def test_get_statistics(self):
        """GET /api/community-map/statistics - returns map statistics"""
        response = requests.get(f"{BASE_URL}/api/community-map/statistics")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        assert "statistics" in data
        
        stats = data["statistics"]
        assert "total_incidents" in stats
        assert "total_encounters" in stats
        assert "total_complaints" in stats
        print(f"✓ GET /api/community-map/statistics - total incidents: {stats['total_incidents']}")
    
    def test_get_hotspots(self):
        """GET /api/community-map/hotspots - returns hotspot data"""
        response = requests.get(f"{BASE_URL}/api/community-map/hotspots")
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        assert "hotspots" in data
        assert "count" in data
        assert isinstance(data["hotspots"], list)
        
        # Verify hotspot structure if any exist
        if data["hotspots"]:
            hotspot = data["hotspots"][0]
            assert "lat" in hotspot
            assert "lon" in hotspot
            assert "incident_count" in hotspot
            assert "intensity" in hotspot
        print(f"✓ GET /api/community-map/hotspots - returned {data['count']} hotspots")
    
    def test_get_hotspots_with_days_filter(self):
        """GET /api/community-map/hotspots - with days parameter"""
        params = {"days": 180}
        response = requests.get(f"{BASE_URL}/api/community-map/hotspots", params=params)
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        print(f"✓ GET /api/community-map/hotspots with days=180 - returned {data['count']} hotspots")
    
    def test_get_officer_locations_requires_params(self):
        """GET /api/community-map/officer-locations - requires officer_id or badge_number"""
        response = requests.get(f"{BASE_URL}/api/community-map/officer-locations")
        assert response.status_code == 200
        
        data = response.json()
        assert "error" in data
        assert data.get("locations") == []
        print("✓ GET /api/community-map/officer-locations - correctly requires params")


class TestCorroborationAuthenticatedEndpoints:
    """Corroboration API tests - Requires authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        if login_response.status_code != 200:
            pytest.skip(f"Login failed: {login_response.status_code}")
        
        # API returns access_token, not token
        self.token = login_response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.user_id = login_response.json().get("user", {}).get("user_id")
    
    def test_corroboration_requires_auth(self):
        """POST /api/corroboration/analyze/{id} - requires authentication"""
        response = requests.post(f"{BASE_URL}/api/corroboration/analyze/test_enc")
        assert response.status_code in [401, 403]
        print("✓ POST /api/corroboration/analyze - correctly requires auth")
    
    def test_get_corroboration_history(self):
        """GET /api/corroboration/history - returns user's history"""
        response = requests.get(
            f"{BASE_URL}/api/corroboration/history",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        assert "history" in data
        assert "count" in data
        assert isinstance(data["history"], list)
        print(f"✓ GET /api/corroboration/history - returned {data['count']} records")
    
    def test_get_corroboration_history_with_limit(self):
        """GET /api/corroboration/history - with limit parameter"""
        response = requests.get(
            f"{BASE_URL}/api/corroboration/history",
            headers=self.headers,
            params={"limit": 5}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data.get("success") is True
        assert len(data.get("history", [])) <= 5
        print("✓ GET /api/corroboration/history with limit=5 - works correctly")
    
    def test_analyze_corroboration_invalid_encounter(self):
        """POST /api/corroboration/analyze/{id} - returns 404 for invalid encounter"""
        response = requests.post(
            f"{BASE_URL}/api/corroboration/analyze/invalid_encounter_id",
            headers=self.headers
        )
        assert response.status_code == 404
        print("✓ POST /api/corroboration/analyze - returns 404 for invalid encounter")
    
    def test_get_encounter_corroboration_summary(self):
        """GET /api/corroboration/encounter/{id}/summary - returns summary"""
        # First get user's encounters to find a valid one
        encounters_response = requests.get(
            f"{BASE_URL}/api/encounters",
            headers=self.headers
        )
        
        if encounters_response.status_code != 200:
            pytest.skip("Could not get encounters")
        
        encounters = encounters_response.json().get("encounters", [])
        if not encounters:
            pytest.skip("No encounters found for user")
        
        encounter_id = encounters[0].get("encounter_id")
        
        response = requests.get(
            f"{BASE_URL}/api/corroboration/encounter/{encounter_id}/summary",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "has_analysis" in data
        print(f"✓ GET /api/corroboration/encounter/{encounter_id}/summary - has_analysis: {data['has_analysis']}")
    
    def test_analyze_corroboration_for_valid_encounter(self):
        """POST /api/corroboration/analyze/{id} - runs analysis for valid encounter"""
        # Get user's encounters
        encounters_response = requests.get(
            f"{BASE_URL}/api/encounters",
            headers=self.headers
        )
        
        if encounters_response.status_code != 200:
            pytest.skip("Could not get encounters")
        
        encounters = encounters_response.json().get("encounters", [])
        if not encounters:
            pytest.skip("No encounters found for user")
        
        encounter_id = encounters[0].get("encounter_id")
        
        response = requests.post(
            f"{BASE_URL}/api/corroboration/analyze/{encounter_id}",
            headers=self.headers,
            timeout=60  # Analysis may take time
        )
        
        # Should return 200 with analysis or 400 if already analyzed
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            data = response.json()
            assert "corroboration_id" in data
            assert "corroboration_score" in data
            assert "score_interpretation" in data
            assert "nearby_encounters" in data
            assert "officer_history" in data
            assert "legal_value" in data
            print(f"✓ POST /api/corroboration/analyze/{encounter_id} - score: {data['corroboration_score']}")
        else:
            print(f"✓ POST /api/corroboration/analyze/{encounter_id} - returned {response.status_code}")
    
    def test_get_corroboration_details_invalid_id(self):
        """GET /api/corroboration/{id} - returns 404 for invalid corroboration"""
        response = requests.get(
            f"{BASE_URL}/api/corroboration/invalid_corr_id",
            headers=self.headers
        )
        assert response.status_code == 404
        print("✓ GET /api/corroboration/{id} - returns 404 for invalid ID")


class TestIncidentDataStructure:
    """Verify incident data structure from Community Map API"""
    
    def test_incident_has_required_fields(self):
        """Verify incident objects have required fields"""
        response = requests.get(f"{BASE_URL}/api/community-map/incidents")
        assert response.status_code == 200
        
        data = response.json()
        incidents = data.get("incidents", [])
        
        if incidents:
            incident = incidents[0]
            # Required fields
            assert "id" in incident
            assert "type" in incident
            assert "lat" in incident
            assert "lon" in incident
            assert "has_violations" in incident
            
            # Verify lat/lon are numbers
            assert isinstance(incident["lat"], (int, float))
            assert isinstance(incident["lon"], (int, float))
            print(f"✓ Incident data structure verified - type: {incident['type']}")
        else:
            print("✓ No incidents to verify structure (empty result)")


class TestStatisticsDataStructure:
    """Verify statistics data structure"""
    
    def test_statistics_has_breakdown(self):
        """Verify statistics includes violation and type breakdowns"""
        response = requests.get(f"{BASE_URL}/api/community-map/statistics")
        assert response.status_code == 200
        
        data = response.json()
        stats = data.get("statistics", {})
        
        assert "violation_breakdown" in stats
        assert "encounter_types" in stats
        assert isinstance(stats["violation_breakdown"], list)
        assert isinstance(stats["encounter_types"], list)
        
        # Verify breakdown structure if data exists
        if stats["violation_breakdown"]:
            vb = stats["violation_breakdown"][0]
            assert "violation" in vb
            assert "count" in vb
        
        if stats["encounter_types"]:
            et = stats["encounter_types"][0]
            assert "type" in et
            assert "count" in et
        
        print(f"✓ Statistics structure verified - {len(stats['violation_breakdown'])} violation types, {len(stats['encounter_types'])} encounter types")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
