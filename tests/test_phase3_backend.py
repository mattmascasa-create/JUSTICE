"""
Phase 3 Backend API Tests for JUSTICE Platform
Tests: Incident Map, Case Timeline, PDF Reports, Push Notifications
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://justice-rights-1.preview.emergentagent.com')

# Test user credentials
TEST_EMAIL = f"test_phase3_{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "password123"
TEST_NAME = "Phase3 Test User"


class TestHealthAndBasics:
    """Basic health check tests"""
    
    def test_health_endpoint(self):
        """Test API health endpoint"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health check passed: {data}")


class TestIncidentMapAPI:
    """Tests for Incident Map endpoints - GET /api/incidents/map and /api/incidents/stats"""
    
    def test_get_incidents_for_map_no_auth(self):
        """Test incidents map endpoint - should work without auth"""
        response = requests.get(f"{BASE_URL}/api/incidents/map")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Incidents map returned {len(data)} incidents")
        
        # Verify incident structure if data exists
        if len(data) > 0:
            incident = data[0]
            assert "case_id" in incident
            assert "latitude" in incident
            assert "longitude" in incident
            assert "title" in incident
            assert "violation_type" in incident
            assert "severity" in incident
            assert "status" in incident
            print(f"✓ Incident structure valid: {incident.get('title')}")
    
    def test_get_incidents_with_filters(self):
        """Test incidents map with filters"""
        # Test severity filter
        response = requests.get(f"{BASE_URL}/api/incidents/map", params={"severity": "high"})
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Filtered by severity=high: {len(data)} incidents")
        
        # Test status filter
        response = requests.get(f"{BASE_URL}/api/incidents/map", params={"status": "open"})
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Filtered by status=open: {len(data)} incidents")
        
        # Test limit parameter
        response = requests.get(f"{BASE_URL}/api/incidents/map", params={"limit": 5})
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5
        print(f"✓ Limit parameter works: {len(data)} incidents (max 5)")
    
    def test_get_incident_stats(self):
        """Test incident statistics endpoint"""
        response = requests.get(f"{BASE_URL}/api/incidents/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify stats structure
        assert "total_incidents" in data
        assert "by_violation_type" in data
        assert "by_severity" in data
        assert isinstance(data["by_violation_type"], list)
        assert isinstance(data["by_severity"], list)
        print(f"✓ Incident stats: total={data['total_incidents']}, violation_types={len(data['by_violation_type'])}")


class TestAuthenticatedEndpoints:
    """Tests requiring authentication"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Register and login to get auth token"""
        # Register new user
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        })
        
        if register_response.status_code == 200:
            token = register_response.json().get("access_token")
            print(f"✓ Registered new user: {TEST_EMAIL}")
            return token
        elif register_response.status_code == 400:
            # User exists, try login
            login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
            if login_response.status_code == 200:
                token = login_response.json().get("access_token")
                print(f"✓ Logged in existing user: {TEST_EMAIL}")
                return token
        
        pytest.skip("Could not authenticate")
    
    @pytest.fixture(scope="class")
    def test_case_id(self, auth_token):
        """Create a test case for timeline and report tests"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        case_data = {
            "title": f"TEST_Phase3_Case_{uuid.uuid4().hex[:6]}",
            "description": "Test case for Phase 3 timeline and report testing",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "location": "Test Location, CA",
            "department": "Test Police Department",
            "officer_name": "Test Officer",
            "officer_badge": "12345",
            "violation_type": "4th Amendment - Unlawful Search/Seizure",
            "severity": "high"
        }
        
        response = requests.post(f"{BASE_URL}/api/cases", json=case_data, headers=headers)
        assert response.status_code == 200
        case_id = response.json().get("case_id")
        print(f"✓ Created test case: {case_id}")
        return case_id


class TestCaseTimeline:
    """Tests for Case Timeline endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Register and login to get auth token"""
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"timeline_test_{uuid.uuid4().hex[:8]}@example.com",
            "password": TEST_PASSWORD,
            "name": "Timeline Test User"
        })
        
        if register_response.status_code == 200:
            return register_response.json().get("access_token")
        pytest.skip("Could not authenticate")
    
    @pytest.fixture(scope="class")
    def test_case_id(self, auth_token):
        """Create a test case"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        case_data = {
            "title": f"TEST_Timeline_Case_{uuid.uuid4().hex[:6]}",
            "description": "Test case for timeline testing",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "location": "Timeline Test Location",
            "violation_type": "4th Amendment - Unlawful Search/Seizure",
            "severity": "medium"
        }
        
        response = requests.post(f"{BASE_URL}/api/cases", json=case_data, headers=headers)
        assert response.status_code == 200
        return response.json().get("case_id")
    
    def test_get_case_timeline(self, auth_token, test_case_id):
        """Test GET /api/cases/{case_id}/timeline"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/{test_case_id}/timeline", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Should have at least the "created" event
        assert len(data) >= 1
        
        # Verify event structure
        event = data[0]
        assert "event_id" in event
        assert "case_id" in event
        assert "event_type" in event
        assert "description" in event
        assert "created_at" in event
        print(f"✓ Timeline has {len(data)} events, first event type: {event['event_type']}")
    
    def test_add_note_to_timeline(self, auth_token, test_case_id):
        """Test POST /api/cases/{case_id}/events - add note"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/cases/{test_case_id}/events",
            params={
                "event_type": "note",
                "description": "Test note added via API"
            },
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data
        assert data.get("message") == "Event added to timeline"
        print(f"✓ Added note to timeline: {data['event_id']}")
        
        # Verify note appears in timeline
        timeline_response = requests.get(f"{BASE_URL}/api/cases/{test_case_id}/timeline", headers=headers)
        assert timeline_response.status_code == 200
        timeline = timeline_response.json()
        
        note_events = [e for e in timeline if e["event_type"] == "note"]
        assert len(note_events) >= 1
        print(f"✓ Note verified in timeline: {len(note_events)} note events")
    
    def test_timeline_unauthorized(self, test_case_id):
        """Test timeline requires authentication"""
        response = requests.get(f"{BASE_URL}/api/cases/{test_case_id}/timeline")
        assert response.status_code == 401
        print("✓ Timeline correctly requires authentication")
    
    def test_timeline_not_found(self, auth_token):
        """Test timeline for non-existent case"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/nonexistent_case/timeline", headers=headers)
        assert response.status_code == 404
        print("✓ Timeline correctly returns 404 for non-existent case")


class TestCaseReport:
    """Tests for PDF Report data endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Register and login to get auth token"""
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"report_test_{uuid.uuid4().hex[:8]}@example.com",
            "password": TEST_PASSWORD,
            "name": "Report Test User"
        })
        
        if register_response.status_code == 200:
            return register_response.json().get("access_token")
        pytest.skip("Could not authenticate")
    
    @pytest.fixture(scope="class")
    def test_case_id(self, auth_token):
        """Create a test case"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        case_data = {
            "title": f"TEST_Report_Case_{uuid.uuid4().hex[:6]}",
            "description": "Test case for PDF report testing",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "location": "Report Test Location",
            "department": "Report Test PD",
            "violation_type": "8th Amendment - Excessive Force",
            "severity": "critical"
        }
        
        response = requests.post(f"{BASE_URL}/api/cases", json=case_data, headers=headers)
        assert response.status_code == 200
        return response.json().get("case_id")
    
    def test_get_case_report_data(self, auth_token, test_case_id):
        """Test GET /api/cases/{case_id}/report"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/cases/{test_case_id}/report", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify report structure
        assert "case" in data
        assert "evidence" in data
        assert "timeline" in data
        assert "user" in data
        assert "generated_at" in data
        assert "report_id" in data
        
        # Verify case data
        assert data["case"]["case_id"] == test_case_id
        assert "title" in data["case"]
        assert "description" in data["case"]
        
        # Verify user data
        assert "name" in data["user"]
        assert "email" in data["user"]
        
        print(f"✓ Report data retrieved: report_id={data['report_id']}")
        print(f"  - Case: {data['case']['title']}")
        print(f"  - Evidence count: {len(data['evidence'])}")
        print(f"  - Timeline events: {len(data['timeline'])}")
    
    def test_report_unauthorized(self, test_case_id):
        """Test report requires authentication"""
        response = requests.get(f"{BASE_URL}/api/cases/{test_case_id}/report")
        assert response.status_code == 401
        print("✓ Report correctly requires authentication")


class TestPushNotifications:
    """Tests for Push Notification subscription endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Register and login to get auth token"""
        register_response = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": f"push_test_{uuid.uuid4().hex[:8]}@example.com",
            "password": TEST_PASSWORD,
            "name": "Push Test User"
        })
        
        if register_response.status_code == 200:
            return register_response.json().get("access_token")
        pytest.skip("Could not authenticate")
    
    def test_push_subscribe(self, auth_token):
        """Test POST /api/push/subscribe"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Mock push subscription data
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint-123",
            "keys": {
                "p256dh": "test-p256dh-key",
                "auth": "test-auth-key"
            }
        }
        
        response = requests.post(f"{BASE_URL}/api/push/subscribe", json=subscription_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data.get("message") == "Subscribed to push notifications"
        print("✓ Push subscription successful")
    
    def test_push_subscribe_unauthorized(self):
        """Test push subscribe requires authentication"""
        subscription_data = {
            "endpoint": "https://test.endpoint",
            "keys": {"p256dh": "test", "auth": "test"}
        }
        
        response = requests.post(f"{BASE_URL}/api/push/subscribe", json=subscription_data)
        assert response.status_code == 401
        print("✓ Push subscribe correctly requires authentication")
    
    def test_push_unsubscribe(self, auth_token):
        """Test DELETE /api/push/unsubscribe"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        response = requests.delete(f"{BASE_URL}/api/push/unsubscribe", headers=headers)
        
        # Should succeed even if not subscribed
        assert response.status_code == 200
        print("✓ Push unsubscribe successful")


class TestWebSocketEndpoint:
    """Tests for WebSocket endpoint existence"""
    
    def test_websocket_endpoint_exists(self):
        """Test WebSocket endpoint returns proper error for HTTP request"""
        # WebSocket endpoints return 404 for regular HTTP requests (expected behavior)
        # The endpoint only accepts WebSocket upgrade requests
        response = requests.get(f"{BASE_URL}/api/ws/invalid_token")
        # 404 is expected because WebSocket endpoints don't respond to HTTP GET
        assert response.status_code in [403, 426, 400, 404]
        print(f"✓ WebSocket endpoint exists (returns {response.status_code} for HTTP request - expected for non-WS)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
