"""
Test suite for Encounter Analytics Dashboard endpoints
Tests: GET /api/analytics/encounters/summary, patterns, hotspots, trends
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test_encounter@example.com"
TEST_PASSWORD = "testpass123"


class TestEncounterAnalytics:
    """Test Encounter Analytics endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.authenticated = True
        else:
            self.authenticated = False
            pytest.skip("Authentication failed - skipping authenticated tests")
    
    def test_health_check(self):
        """Test health endpoint is accessible"""
        response = self.session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print("✓ Health check passed")
    
    def test_analytics_summary_endpoint(self):
        """Test GET /api/analytics/encounters/summary returns correct structure"""
        response = self.session.get(f"{BASE_URL}/api/analytics/encounters/summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify required fields exist
        assert "total_encounters" in data, "Missing total_encounters field"
        assert "active_encounters" in data, "Missing active_encounters field"
        assert "completed_encounters" in data, "Missing completed_encounters field"
        assert "risk_score" in data, "Missing risk_score field"
        assert "officer_demeanor" in data, "Missing officer_demeanor field"
        assert "tone_distribution" in data, "Missing tone_distribution field"
        assert "violations_by_type" in data, "Missing violations_by_type field"
        assert "escalation_stats" in data, "Missing escalation_stats field"
        
        # Verify data types
        assert isinstance(data["total_encounters"], int), "total_encounters should be int"
        assert isinstance(data["active_encounters"], int), "active_encounters should be int"
        assert isinstance(data["risk_score"], int), "risk_score should be int"
        assert 0 <= data["risk_score"] <= 100, "risk_score should be 0-100"
        
        # Verify officer_demeanor structure
        demeanor = data["officer_demeanor"]
        assert "avg_aggression" in demeanor, "Missing avg_aggression in officer_demeanor"
        assert "max_aggression" in demeanor, "Missing max_aggression in officer_demeanor"
        assert "avg_intimidation" in demeanor, "Missing avg_intimidation in officer_demeanor"
        assert "avg_professionalism" in demeanor, "Missing avg_professionalism in officer_demeanor"
        
        print(f"✓ Summary endpoint returned valid data: {data['total_encounters']} encounters, risk_score={data['risk_score']}")
    
    def test_analytics_patterns_endpoint(self):
        """Test GET /api/analytics/encounters/patterns returns time-of-day and day-of-week data"""
        response = self.session.get(f"{BASE_URL}/api/analytics/encounters/patterns")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify required fields
        assert "by_hour" in data, "Missing by_hour field"
        assert "by_day" in data, "Missing by_day field"
        assert "by_type" in data, "Missing by_type field"
        assert "peak_hour" in data, "Missing peak_hour field"
        assert "peak_day" in data, "Missing peak_day field"
        
        # Verify by_hour structure (should have 24 entries)
        assert isinstance(data["by_hour"], list), "by_hour should be a list"
        assert len(data["by_hour"]) == 24, f"by_hour should have 24 entries, got {len(data['by_hour'])}"
        
        # Verify each hour entry has correct structure
        for hour_entry in data["by_hour"]:
            assert "hour" in hour_entry, "Missing hour in by_hour entry"
            assert "count" in hour_entry, "Missing count in by_hour entry"
            assert 0 <= hour_entry["hour"] <= 23, f"Invalid hour value: {hour_entry['hour']}"
        
        # Verify by_day structure (should have 7 entries)
        assert isinstance(data["by_day"], list), "by_day should be a list"
        assert len(data["by_day"]) == 7, f"by_day should have 7 entries, got {len(data['by_day'])}"
        
        # Verify each day entry has correct structure
        for day_entry in data["by_day"]:
            assert "day" in day_entry, "Missing day in by_day entry"
            assert "day_index" in day_entry, "Missing day_index in by_day entry"
            assert "count" in day_entry, "Missing count in by_day entry"
        
        print(f"✓ Patterns endpoint returned valid data: peak_hour={data['peak_hour']}, peak_day={data['peak_day']}")
    
    def test_analytics_hotspots_endpoint(self):
        """Test GET /api/analytics/encounters/hotspots returns geographic data"""
        response = self.session.get(f"{BASE_URL}/api/analytics/encounters/hotspots")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify required fields
        assert "hotspots" in data, "Missing hotspots field"
        assert "all_locations" in data, "Missing all_locations field"
        assert "total_mapped" in data, "Missing total_mapped field"
        
        # Verify data types
        assert isinstance(data["hotspots"], list), "hotspots should be a list"
        assert isinstance(data["all_locations"], list), "all_locations should be a list"
        assert isinstance(data["total_mapped"], int), "total_mapped should be int"
        
        # Verify hotspot structure if any exist
        if data["hotspots"]:
            hotspot = data["hotspots"][0]
            assert "latitude" in hotspot, "Missing latitude in hotspot"
            assert "longitude" in hotspot, "Missing longitude in hotspot"
            assert "count" in hotspot, "Missing count in hotspot"
            assert "addresses" in hotspot, "Missing addresses in hotspot"
            assert "types" in hotspot, "Missing types in hotspot"
        
        # Verify all_locations structure if any exist
        if data["all_locations"]:
            location = data["all_locations"][0]
            assert "encounter_id" in location, "Missing encounter_id in location"
            assert "latitude" in location, "Missing latitude in location"
            assert "longitude" in location, "Missing longitude in location"
        
        print(f"✓ Hotspots endpoint returned valid data: {data['total_mapped']} mapped locations, {len(data['hotspots'])} hotspots")
    
    def test_analytics_trends_endpoint(self):
        """Test GET /api/analytics/encounters/trends returns 30-day trend data"""
        response = self.session.get(f"{BASE_URL}/api/analytics/encounters/trends?days=30")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify required fields
        assert "period_days" in data, "Missing period_days field"
        assert "total_encounters" in data, "Missing total_encounters field"
        assert "daily_data" in data, "Missing daily_data field"
        assert "avg_encounters_per_day" in data, "Missing avg_encounters_per_day field"
        
        # Verify data types
        assert data["period_days"] == 30, f"Expected period_days=30, got {data['period_days']}"
        assert isinstance(data["total_encounters"], int), "total_encounters should be int"
        assert isinstance(data["daily_data"], list), "daily_data should be a list"
        
        # Verify daily_data has entries (should have ~30 days)
        assert len(data["daily_data"]) >= 30, f"daily_data should have at least 30 entries, got {len(data['daily_data'])}"
        
        # Verify daily_data entry structure
        if data["daily_data"]:
            day_entry = data["daily_data"][0]
            assert "date" in day_entry, "Missing date in daily_data entry"
            assert "encounters" in day_entry, "Missing encounters in daily_data entry"
            assert "avg_aggression" in day_entry, "Missing avg_aggression in daily_data entry"
        
        print(f"✓ Trends endpoint returned valid data: {data['total_encounters']} encounters over {data['period_days']} days")
    
    def test_analytics_trends_custom_days(self):
        """Test trends endpoint with custom days parameter"""
        response = self.session.get(f"{BASE_URL}/api/analytics/encounters/trends?days=7")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["period_days"] == 7, f"Expected period_days=7, got {data['period_days']}"
        print(f"✓ Trends endpoint with custom days=7 works correctly")
    
    def test_analytics_requires_auth(self):
        """Test that analytics endpoints require authentication"""
        # Create a new session without auth
        unauth_session = requests.Session()
        unauth_session.headers.update({"Content-Type": "application/json"})
        
        endpoints = [
            "/api/analytics/encounters/summary",
            "/api/analytics/encounters/patterns",
            "/api/analytics/encounters/hotspots",
            "/api/analytics/encounters/trends"
        ]
        
        for endpoint in endpoints:
            response = unauth_session.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 401, f"Expected 401 for {endpoint}, got {response.status_code}"
        
        print("✓ All analytics endpoints correctly require authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
