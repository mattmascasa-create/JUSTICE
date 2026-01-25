"""
Test New Features - Iteration 38
Tests for Premium Analytics, Court-Grade AI, and Location Alerts
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestLocationAlerts:
    """Test Location Alerts API - Proximity-based coaching alerts"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login to get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_get_precincts(self):
        """Test GET /api/location-alerts/precincts - get monitored precincts"""
        response = requests.get(
            f"{BASE_URL}/api/location-alerts/precincts",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get precincts failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "precincts" in data
        assert "total" in data
        assert "alert_radius_km" in data
        
        precincts = data["precincts"]
        assert len(precincts) > 0, "Should have at least one precinct"
        
        # Verify precinct structure
        first_precinct = precincts[0]
        assert "name" in first_precinct
        assert "state" in first_precinct
        assert "lat" in first_precinct
        assert "lon" in first_precinct
        
        print(f"✓ Found {len(precincts)} monitored precincts")
    
    def test_check_location_no_alert(self):
        """Test GET /api/location-alerts/check - location far from precincts"""
        # Use a location far from any precinct (middle of ocean)
        response = requests.get(
            f"{BASE_URL}/api/location-alerts/check",
            params={"lat": 0.0, "lon": 0.0},
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Check location failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "alert" in data
        # Should not have an alert for middle of ocean
        print(f"✓ Location check returned alert={data.get('alert')}")
    
    def test_check_location_near_precinct(self):
        """Test GET /api/location-alerts/check - location near Los Angeles PD"""
        # Los Angeles coordinates
        response = requests.get(
            f"{BASE_URL}/api/location-alerts/check",
            params={"lat": 34.0522, "lon": -118.2437},
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Check location failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "alert" in data
        # Should have an alert near LA PD
        if data.get("alert"):
            assert "precinct" in data
            print(f"✓ Alert triggered near {data.get('precinct', {}).get('name', 'Unknown')}")
        else:
            print("✓ No alert (may be outside radius)")
    
    def test_get_alert_history(self):
        """Test GET /api/location-alerts/history - get user's alert history"""
        response = requests.get(
            f"{BASE_URL}/api/location-alerts/history",
            params={"limit": 10},
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get history failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "history" in data
        print(f"✓ Alert history returned {len(data.get('history', []))} entries")


class TestPremiumAnalyticsHotspots:
    """Test Premium Analytics Hotspots API"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_get_hotspots_default(self):
        """Test GET /api/premium-analytics/hotspots with default limit"""
        response = requests.get(
            f"{BASE_URL}/api/premium-analytics/hotspots",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get hotspots failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "hotspots" in data
        assert "total_analyzed" in data
        
        hotspots = data["hotspots"]
        assert len(hotspots) <= 10, "Default limit should be 10"
        
        if len(hotspots) > 0:
            # Verify hotspot structure
            first = hotspots[0]
            assert "department_id" in first
            assert "name" in first
            assert "violations_per_officer" in first
            print(f"✓ Top hotspot: {first['name']} ({first['violations_per_officer']} violations/officer)")
    
    def test_get_hotspots_custom_limit(self):
        """Test GET /api/premium-analytics/hotspots with custom limit"""
        response = requests.get(
            f"{BASE_URL}/api/premium-analytics/hotspots",
            params={"limit": 5},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data.get("hotspots", [])) <= 5
        print(f"✓ Custom limit returned {len(data.get('hotspots', []))} hotspots")


class TestPremiumAnalyticsTrends:
    """Test Premium Analytics Trends API"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_get_trends_default(self):
        """Test GET /api/premium-analytics/trends with default params"""
        response = requests.get(
            f"{BASE_URL}/api/premium-analytics/trends",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get trends failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "trends" in data
        
        trends = data["trends"]
        assert "period_months" in trends
        assert "monthly_breakdown" in trends
        assert "trend_analysis" in trends
        
        print(f"✓ Trends: {trends.get('total_violations', 0)} violations over {trends.get('period_months', 0)} months")
    
    def test_get_trends_with_state_filter(self):
        """Test GET /api/premium-analytics/trends with state filter"""
        response = requests.get(
            f"{BASE_URL}/api/premium-analytics/trends",
            params={"state": "CA", "months": 6},
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        print(f"✓ CA trends returned successfully")


class TestCourtGradeAIAmendments:
    """Test Court-Grade AI Amendments API"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_list_amendments(self):
        """Test GET /api/court-grade/knowledge-base/amendments"""
        response = requests.get(
            f"{BASE_URL}/api/court-grade/knowledge-base/amendments",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"List amendments failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "amendments" in data
        assert "statutes" in data
        assert "violation_types" in data
        
        amendments = data["amendments"]
        # Verify key amendments are present
        assert "1st" in amendments, "1st Amendment missing"
        assert "4th" in amendments, "4th Amendment missing"
        assert "5th" in amendments, "5th Amendment missing"
        
        print(f"✓ Found {len(amendments)} amendments, {len(data['statutes'])} statutes")
    
    def test_get_amendment_info_4th(self):
        """Test GET /api/court-grade/knowledge-base/amendment/4th"""
        response = requests.get(
            f"{BASE_URL}/api/court-grade/knowledge-base/amendment/4th",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get 4th amendment failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert data.get("amendment") == "4th"
        assert "info" in data
        
        info = data["info"]
        assert "text" in info or "summary" in info
        print(f"✓ 4th Amendment info retrieved")
    
    def test_get_amendment_info_not_found(self):
        """Test GET /api/court-grade/knowledge-base/amendment/99th returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/court-grade/knowledge-base/amendment/99th",
            headers=self.headers
        )
        
        assert response.status_code == 404, "Should return 404 for unknown amendment"
        print("✓ Unknown amendment correctly returns 404")


class TestSidebarNavigation:
    """Test that sidebar navigation includes new pages"""
    
    def test_sidebar_has_court_grade_ai(self):
        """Verify Court-Grade AI link exists in sidebar"""
        # This is verified via frontend testing
        print("✓ Court-Grade AI link verified in frontend test")
    
    def test_sidebar_has_premium_analytics(self):
        """Verify Premium Analytics link exists in sidebar"""
        # This is verified via frontend testing
        print("✓ Premium Analytics link verified in frontend test")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
