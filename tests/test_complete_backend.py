"""
JUSTICE Platform - Complete Backend Testing
Tests all major endpoints after backend refactoring.

Endpoints tested:
- Health endpoint
- User registration and login
- Cases CRUD operations
- Evidence endpoints
- SOS alert creation
- Encounter start/end operations
- Encounter audio upload
- AI Analysis endpoint
- Community vault submissions
- Know Your Rights endpoint
- Analytics endpoints
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://justice-rights.preview.emergentagent.com"

# Test credentials - unique per test run
TEST_EMAIL = f"test_complete_{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "testpass123"
TEST_NAME = "Complete Test User"


# ============== FIXTURES ==============

@pytest.fixture(scope="module")
def auth_token():
    """Register and login to get auth token for all tests"""
    # First register
    register_payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "name": TEST_NAME
    }
    register_response = requests.post(f"{BASE_URL}/api/auth/register", json=register_payload)
    
    if register_response.status_code == 200:
        return register_response.json()["access_token"]
    
    # If registration fails (user exists), try login
    login_payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    login_response = requests.post(f"{BASE_URL}/api/auth/login", json=login_payload)
    
    if login_response.status_code == 200:
        return login_response.json()["access_token"]
    
    pytest.skip("Could not authenticate - skipping tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Return headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="module")
def test_case_id(auth_headers):
    """Create a test case and return its ID"""
    payload = {
        "title": "TEST_Complete Backend Case",
        "description": "Test case for complete backend testing",
        "incident_date": datetime.now(timezone.utc).isoformat(),
        "location": "Test Location, CA",
        "violation_type": "4th Amendment",
        "severity": "medium"
    }
    response = requests.post(f"{BASE_URL}/api/cases", json=payload, headers=auth_headers)
    if response.status_code == 200:
        return response.json()["case_id"]
    pytest.skip("Could not create test case")


# ============== HEALTH ENDPOINT ==============

class TestHealthEndpoint:
    """Test health endpoint returns healthy status"""
    
    def test_health_returns_healthy(self):
        """Health endpoint should return healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        print(f"✓ Health check passed - version: {data['version']}")


# ============== AUTH ENDPOINTS ==============

class TestUserAuth:
    """Test user registration and login work"""
    
    def test_register_new_user(self):
        """Registration should create new user and return token"""
        unique_email = f"test_auth_{uuid.uuid4().hex[:8]}@example.com"
        payload = {
            "email": unique_email,
            "password": "testpass123",
            "name": "Auth Test User"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == unique_email
        assert data["user"]["role"] == "citizen"
        print(f"✓ User registration passed - user_id: {data['user']['user_id']}")
    
    def test_login_success(self, auth_token):
        """Login with valid credentials should return token"""
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        print("✓ Login passed - token received")
    
    def test_login_invalid_credentials(self):
        """Login with invalid credentials should fail"""
        payload = {
            "email": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        assert response.status_code == 401
        print("✓ Invalid login correctly rejected")


# ============== CASES CRUD ==============

class TestCasesCRUD:
    """Test Cases CRUD operations work"""
    
    def test_create_case(self, auth_headers):
        """Create case should return case data"""
        payload = {
            "title": "TEST_CRUD Case",
            "description": "Test case for CRUD operations",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "location": "Test Location, CA",
            "violation_type": "4th Amendment",
            "severity": "medium"
        }
        response = requests.post(f"{BASE_URL}/api/cases", json=payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "case_id" in data
        assert data["title"] == payload["title"]
        assert data["status"] == "open"
        print(f"✓ Create case passed - case_id: {data['case_id']}")
    
    def test_get_cases(self, auth_headers):
        """Get cases should return list of user's cases"""
        response = requests.get(f"{BASE_URL}/api/cases", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Get cases passed - found {len(data)} cases")
    
    def test_get_case_by_id(self, auth_headers, test_case_id):
        """Get specific case by ID should return case data"""
        response = requests.get(f"{BASE_URL}/api/cases/{test_case_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["case_id"] == test_case_id
        print(f"✓ Get case by ID passed - case_id: {test_case_id}")
    
    def test_update_case(self, auth_headers, test_case_id):
        """Update case should modify case data"""
        update_payload = {"status": "under_review", "severity": "high"}
        response = requests.patch(f"{BASE_URL}/api/cases/{test_case_id}", json=update_payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "under_review"
        print(f"✓ Update case passed - case_id: {test_case_id}")


# ============== EVIDENCE ENDPOINTS ==============

class TestEvidenceEndpoints:
    """Test Evidence endpoints return data"""
    
    def test_get_all_evidence(self, auth_headers):
        """Get all evidence should return list"""
        response = requests.get(f"{BASE_URL}/api/evidence", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get all evidence passed - found {len(data)} items")
    
    def test_create_evidence_for_case(self, auth_headers, test_case_id):
        """Create evidence for a case should work"""
        evidence_payload = {
            "case_id": test_case_id,
            "file_name": "test_evidence.pdf",
            "file_url": "/api/files/test_evidence.pdf",
            "file_type": "document",
            "file_size": 1024,
            "description": "Test evidence document"
        }
        response = requests.post(f"{BASE_URL}/api/evidence", json=evidence_payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "evidence_id" in data
        assert "blockchain_hash" in data
        print(f"✓ Create evidence passed - evidence_id: {data['evidence_id']}")
    
    def test_get_case_evidence(self, auth_headers, test_case_id):
        """Get evidence for specific case should work"""
        response = requests.get(f"{BASE_URL}/api/evidence/case/{test_case_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get case evidence passed - found {len(data)} items")


# ============== SOS ALERTS ==============

class TestSOSAlerts:
    """Test SOS alert creation works"""
    
    def test_create_sos_alert(self, auth_headers):
        """Create SOS alert should work"""
        payload = {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "address": "Test Address, Los Angeles, CA"
        }
        response = requests.post(f"{BASE_URL}/api/sos", json=payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "alert_id" in data
        assert data["status"] == "active"
        print(f"✓ Create SOS alert passed - alert_id: {data['alert_id']}")
        
        # Resolve the alert
        alert_id = data["alert_id"]
        resolve_response = requests.post(f"{BASE_URL}/api/sos/{alert_id}/resolve", headers=auth_headers)
        assert resolve_response.status_code == 200
        print(f"✓ Resolve SOS alert passed")
    
    def test_get_active_alert(self, auth_headers):
        """Get active SOS alert should work"""
        response = requests.get(f"{BASE_URL}/api/sos/active", headers=auth_headers)
        
        assert response.status_code == 200
        print("✓ Get active SOS alert passed")


# ============== ENCOUNTER OPERATIONS ==============

class TestEncounterOperations:
    """Test Encounter start/end operations work"""
    
    def test_start_encounter(self, auth_headers):
        """Start encounter should create new encounter"""
        payload = {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "address": "Test Encounter Location, CA",
            "encounter_type": "traffic_stop",
            "broadcast_mode": "save"
        }
        response = requests.post(f"{BASE_URL}/api/encounters/start", json=payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "encounter_id" in data
        assert data["status"] == "active"
        assert data["encounter_type"] == "traffic_stop"
        print(f"✓ Start encounter passed - encounter_id: {data['encounter_id']}")
        
        return data["encounter_id"]
    
    def test_get_encounters(self, auth_headers):
        """Get encounters should return list"""
        response = requests.get(f"{BASE_URL}/api/encounters", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get encounters passed - found {len(data)} encounters")
    
    def test_end_encounter(self, auth_headers):
        """End encounter should update status"""
        # First start an encounter
        start_payload = {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "encounter_type": "pedestrian_stop",
            "broadcast_mode": "save"
        }
        start_response = requests.post(f"{BASE_URL}/api/encounters/start", json=start_payload, headers=auth_headers)
        
        if start_response.status_code != 200:
            pytest.skip("Could not start encounter")
        
        encounter_id = start_response.json()["encounter_id"]
        
        # End the encounter
        end_response = requests.post(f"{BASE_URL}/api/encounters/{encounter_id}/end", headers=auth_headers)
        
        assert end_response.status_code == 200
        data = end_response.json()
        assert data["status"] == "ended"
        print(f"✓ End encounter passed - encounter_id: {encounter_id}")
    
    def test_get_encounter_by_id(self, auth_headers):
        """Get specific encounter by ID should work"""
        # First start an encounter
        start_payload = {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "encounter_type": "traffic_stop",
            "broadcast_mode": "save"
        }
        start_response = requests.post(f"{BASE_URL}/api/encounters/start", json=start_payload, headers=auth_headers)
        
        if start_response.status_code != 200:
            pytest.skip("Could not start encounter")
        
        encounter_id = start_response.json()["encounter_id"]
        
        # Get the encounter
        response = requests.get(f"{BASE_URL}/api/encounters/{encounter_id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["encounter_id"] == encounter_id
        print(f"✓ Get encounter by ID passed - encounter_id: {encounter_id}")


# ============== AI ANALYSIS ==============

class TestAIAnalysis:
    """Test AI Analysis endpoint returns violations"""
    
    def test_ai_chat_responds(self, auth_headers):
        """AI chat should respond to messages"""
        payload = {
            "message": "What are my rights during a traffic stop?"
        }
        response = requests.post(f"{BASE_URL}/api/ai/chat", json=payload, headers=auth_headers, timeout=60)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "response" in data
        assert "session_id" in data
        assert len(data["response"]) > 0
        print(f"✓ AI chat passed - session_id: {data['session_id']}")
    
    def test_ai_chat_requires_auth(self):
        """AI chat without auth should fail"""
        payload = {
            "message": "What are my rights?"
        }
        response = requests.post(f"{BASE_URL}/api/ai/chat", json=payload)
        
        assert response.status_code == 401
        print("✓ AI chat auth requirement passed")
    
    def test_encounter_analyze(self, auth_headers):
        """Encounter analyze endpoint should work"""
        # First start an encounter
        start_payload = {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "encounter_type": "traffic_stop",
            "broadcast_mode": "save"
        }
        start_response = requests.post(f"{BASE_URL}/api/encounters/start", json=start_payload, headers=auth_headers)
        
        if start_response.status_code != 200:
            pytest.skip("Could not start encounter")
        
        encounter_id = start_response.json()["encounter_id"]
        
        # Analyze the encounter
        response = requests.post(f"{BASE_URL}/api/encounters/{encounter_id}/analyze", headers=auth_headers, timeout=60)
        
        # Should return 200 (analysis may be empty if no audio)
        assert response.status_code == 200
        data = response.json()
        assert "violations" in data or "message" in data
        print(f"✓ Encounter analyze passed - encounter_id: {encounter_id}")
    
    def test_get_encounter_violations(self, auth_headers):
        """Get encounter violations should work"""
        # First start an encounter
        start_payload = {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "encounter_type": "traffic_stop",
            "broadcast_mode": "save"
        }
        start_response = requests.post(f"{BASE_URL}/api/encounters/start", json=start_payload, headers=auth_headers)
        
        if start_response.status_code != 200:
            pytest.skip("Could not start encounter")
        
        encounter_id = start_response.json()["encounter_id"]
        
        # Get violations
        response = requests.get(f"{BASE_URL}/api/encounters/{encounter_id}/violations", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get encounter violations passed - encounter_id: {encounter_id}")


# ============== COMMUNITY VAULT ==============

class TestCommunityVault:
    """Test Community vault submissions work"""
    
    def test_submit_to_community(self, auth_headers):
        """Submit to community vault should work"""
        payload = {
            "encounter_type": "traffic_stop",
            "location_city": "Los Angeles",
            "location_state": "California",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "violations": ["4th Amendment", "Excessive Force"],
            "department": "LAPD",
            "officer_badge": "12345",
            "severity": "high",
            "outcome": "Citation issued",
            "summary": "TEST_Community submission for testing purposes"
        }
        response = requests.post(f"{BASE_URL}/api/community/submit", json=payload, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "submission_id" in data
        print(f"✓ Community submit passed - submission_id: {data['submission_id']}")
    
    def test_get_community_submissions(self, auth_headers):
        """Get community submissions should return list"""
        response = requests.get(f"{BASE_URL}/api/community/submissions", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get community submissions passed - found {len(data)} submissions")
    
    def test_get_community_stats(self, auth_headers):
        """Get community stats should return statistics"""
        response = requests.get(f"{BASE_URL}/api/community/stats", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_submissions" in data or isinstance(data, dict)
        print(f"✓ Get community stats passed")
    
    def test_get_community_departments(self, auth_headers):
        """Get community departments should return list"""
        response = requests.get(f"{BASE_URL}/api/community/departments", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get community departments passed - found {len(data)} departments")


# ============== KNOW YOUR RIGHTS ==============

class TestKnowYourRights:
    """Test Know Your Rights endpoint returns info"""
    
    def test_get_rights(self):
        """Get rights should return rights information"""
        response = requests.get(f"{BASE_URL}/api/rights")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return rights information
        assert isinstance(data, (list, dict))
        if isinstance(data, list):
            assert len(data) > 0
        print(f"✓ Get rights passed")
    
    def test_rights_coach(self, auth_headers):
        """Rights coach should provide guidance"""
        payload = {
            "situation": "traffic_stop",
            "question": "Can the officer search my car without consent?"
        }
        response = requests.post(f"{BASE_URL}/api/rights-coach", json=payload, headers=auth_headers, timeout=60)
        
        # Should return 200 with guidance
        assert response.status_code == 200
        data = response.json()
        assert "response" in data or "guidance" in data or "advice" in data or isinstance(data, dict)
        print(f"✓ Rights coach passed")


# ============== ANALYTICS ENDPOINTS ==============

class TestAnalyticsEndpoints:
    """Test Analytics endpoints return valid data"""
    
    def test_analytics_summary(self, auth_headers):
        """Analytics summary should return data"""
        response = requests.get(f"{BASE_URL}/api/analytics/encounters/summary", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "risk_score" in data
        assert "total_encounters" in data
        print(f"✓ Analytics summary passed - risk_score: {data['risk_score']}")
    
    def test_analytics_patterns(self, auth_headers):
        """Analytics patterns should return data"""
        response = requests.get(f"{BASE_URL}/api/analytics/encounters/patterns", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "by_hour" in data
        assert "by_day" in data
        print(f"✓ Analytics patterns passed")
    
    def test_analytics_hotspots(self, auth_headers):
        """Analytics hotspots should return data"""
        response = requests.get(f"{BASE_URL}/api/analytics/encounters/hotspots", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "hotspots" in data
        assert "total_mapped" in data
        print(f"✓ Analytics hotspots passed - total_mapped: {data['total_mapped']}")
    
    def test_analytics_trends(self, auth_headers):
        """Analytics trends should return data"""
        response = requests.get(f"{BASE_URL}/api/analytics/encounters/trends?days=30", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "period_days" in data
        assert "total_encounters" in data
        print(f"✓ Analytics trends passed - period: {data['period_days']} days")


# ============== ATTORNEY DIRECTORY ==============

class TestAttorneyDirectory:
    """Test Attorney directory returns attorneys"""
    
    def test_get_attorneys(self):
        """Get attorneys should return list"""
        response = requests.get(f"{BASE_URL}/api/attorneys")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        if len(data) > 0:
            attorney = data[0]
            assert "attorney_id" in attorney
            assert "name" in attorney
        print(f"✓ Get attorneys passed - found {len(data)} attorneys")
    
    def test_get_attorneys_by_state(self):
        """Get attorneys filtered by state should work"""
        response = requests.get(f"{BASE_URL}/api/attorneys?state=California")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get attorneys by state passed - found {len(data)} in California")


# ============== DEPARTMENTS ==============

class TestDepartmentsEndpoint:
    """Test Departments endpoint for transparency portal"""
    
    def test_get_departments(self):
        """Get departments should return list"""
        response = requests.get(f"{BASE_URL}/api/departments")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        if len(data) > 0:
            dept = data[0]
            assert "department_id" in dept
            assert "name" in dept
        print(f"✓ Get departments passed - found {len(data)} departments")


# ============== CLEANUP ==============

def cleanup_test_data():
    """Clean up test data created during tests"""
    payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
    if response.status_code != 200:
        return
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get and delete all test cases
    cases_response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
    if cases_response.status_code == 200:
        cases = cases_response.json()
        for case in cases:
            if case["title"].startswith("TEST_"):
                requests.delete(f"{BASE_URL}/api/cases/{case['case_id']}", headers=headers)
    
    print("✓ Test data cleanup completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
