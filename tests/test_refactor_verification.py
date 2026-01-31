"""
JUSTICE Platform - Backend Refactoring Verification Tests

This test file verifies that all existing endpoints still work correctly
after the modular refactoring. The original server.py is still running,
so all tests should pass.

Endpoints tested:
- Health endpoint
- User registration
- User login
- Get user profile (auth/me)
- Cases CRUD operations
- Evidence endpoints
- SOS alert creation
- Analytics endpoints
- Attorney directory
- AI chat endpoint
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://rights-shield-2.preview.emergentagent.com"

# Test credentials
TEST_EMAIL = f"test_refactor_{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "testpass123"
TEST_NAME = "Refactor Test User"


class TestHealthEndpoint:
    """Test health endpoint returns correct status"""
    
    def test_health_returns_healthy(self):
        """Health endpoint should return healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        print(f"✓ Health check passed - version: {data['version']}")


class TestUserRegistration:
    """Test user registration creates new account"""
    
    def test_register_new_user(self):
        """Registration should create new user and return token"""
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        assert data["user"]["name"] == TEST_NAME
        assert data["user"]["role"] == "citizen"
        print(f"✓ User registration passed - user_id: {data['user']['user_id']}")
        
        # Store token for later tests
        return data["access_token"]
    
    def test_register_duplicate_email_fails(self):
        """Registration with existing email should fail"""
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "already registered" in data.get("detail", "").lower()
        print("✓ Duplicate registration correctly rejected")


class TestUserLogin:
    """Test user login returns valid JWT token"""
    
    def test_login_success(self):
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
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        print(f"✓ Login passed - token received")
        
        return data["access_token"]
    
    def test_login_invalid_credentials(self):
        """Login with invalid credentials should fail"""
        payload = {
            "email": TEST_EMAIL,
            "password": "wrongpassword"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        assert response.status_code == 401
        print("✓ Invalid login correctly rejected")


class TestUserProfile:
    """Test get user profile returns authenticated user data"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for tests"""
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Login failed - skipping authenticated tests")
    
    def test_get_profile_authenticated(self, auth_token):
        """Get profile with valid token should return user data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["email"] == TEST_EMAIL
        assert data["name"] == TEST_NAME
        assert "user_id" in data
        print(f"✓ Get profile passed - user_id: {data['user_id']}")
    
    def test_get_profile_unauthenticated(self):
        """Get profile without token should fail"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code == 401
        print("✓ Unauthenticated profile request correctly rejected")


class TestCasesCRUD:
    """Test Cases CRUD operations work"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for tests"""
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Login failed - skipping authenticated tests")
    
    def test_create_case(self, auth_token):
        """Create case should return case data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        payload = {
            "title": "TEST_Refactor Verification Case",
            "description": "Test case for refactoring verification",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "location": "Test Location, CA",
            "violation_type": "4th Amendment",
            "severity": "medium"
        }
        response = requests.post(f"{BASE_URL}/api/cases", json=payload, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "case_id" in data
        assert data["title"] == payload["title"]
        assert data["status"] == "open"
        print(f"✓ Create case passed - case_id: {data['case_id']}")
        
        return data["case_id"]
    
    def test_get_cases(self, auth_token):
        """Get cases should return list of user's cases"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Get cases passed - found {len(data)} cases")
    
    def test_get_case_by_id(self, auth_token):
        """Get specific case by ID should return case data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # First create a case
        payload = {
            "title": "TEST_Get Case By ID",
            "description": "Test case for get by ID",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "location": "Test Location, CA",
            "violation_type": "5th Amendment",
            "severity": "low"
        }
        create_response = requests.post(f"{BASE_URL}/api/cases", json=payload, headers=headers)
        case_id = create_response.json()["case_id"]
        
        # Then get it
        response = requests.get(f"{BASE_URL}/api/cases/{case_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["case_id"] == case_id
        print(f"✓ Get case by ID passed - case_id: {case_id}")
    
    def test_update_case(self, auth_token):
        """Update case should modify case data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # First create a case
        payload = {
            "title": "TEST_Update Case",
            "description": "Test case for update",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "location": "Test Location, CA",
            "violation_type": "1st Amendment",
            "severity": "low"
        }
        create_response = requests.post(f"{BASE_URL}/api/cases", json=payload, headers=headers)
        case_id = create_response.json()["case_id"]
        
        # Update it
        update_payload = {"status": "under_review", "severity": "high"}
        response = requests.patch(f"{BASE_URL}/api/cases/{case_id}", json=update_payload, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "under_review"
        assert data["severity"] == "high"
        print(f"✓ Update case passed - case_id: {case_id}")
    
    def test_delete_case(self, auth_token):
        """Delete case should remove case"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # First create a case
        payload = {
            "title": "TEST_Delete Case",
            "description": "Test case for deletion",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "location": "Test Location, CA",
            "violation_type": "8th Amendment",
            "severity": "low"
        }
        create_response = requests.post(f"{BASE_URL}/api/cases", json=payload, headers=headers)
        case_id = create_response.json()["case_id"]
        
        # Delete it
        response = requests.delete(f"{BASE_URL}/api/cases/{case_id}", headers=headers)
        
        assert response.status_code == 200
        
        # Verify it's gone
        get_response = requests.get(f"{BASE_URL}/api/cases/{case_id}", headers=headers)
        assert get_response.status_code == 404
        print(f"✓ Delete case passed - case_id: {case_id}")


class TestEvidenceEndpoints:
    """Test Evidence endpoints return data"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for tests"""
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Login failed - skipping authenticated tests")
    
    def test_get_all_evidence(self, auth_token):
        """Get all evidence should return list"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/evidence", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get all evidence passed - found {len(data)} items")
    
    def test_create_evidence_for_case(self, auth_token):
        """Create evidence for a case should work"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # First create a case
        case_payload = {
            "title": "TEST_Evidence Case",
            "description": "Test case for evidence",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "location": "Test Location, CA",
            "violation_type": "4th Amendment",
            "severity": "medium"
        }
        case_response = requests.post(f"{BASE_URL}/api/cases", json=case_payload, headers=headers)
        case_id = case_response.json()["case_id"]
        
        # Create evidence
        evidence_payload = {
            "case_id": case_id,
            "file_name": "test_evidence.pdf",
            "file_url": "/api/files/test_evidence.pdf",
            "file_type": "document",
            "file_size": 1024,
            "description": "Test evidence document"
        }
        response = requests.post(f"{BASE_URL}/api/evidence", json=evidence_payload, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "evidence_id" in data
        assert "blockchain_hash" in data
        print(f"✓ Create evidence passed - evidence_id: {data['evidence_id']}")
    
    def test_get_case_evidence(self, auth_token):
        """Get evidence for specific case should work"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # First create a case with evidence
        case_payload = {
            "title": "TEST_Case Evidence List",
            "description": "Test case for evidence list",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "location": "Test Location, CA",
            "violation_type": "5th Amendment",
            "severity": "low"
        }
        case_response = requests.post(f"{BASE_URL}/api/cases", json=case_payload, headers=headers)
        case_id = case_response.json()["case_id"]
        
        # Get evidence for case
        response = requests.get(f"{BASE_URL}/api/evidence/case/{case_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get case evidence passed - case_id: {case_id}")


class TestSOSAlerts:
    """Test SOS alert creation works"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for tests"""
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Login failed - skipping authenticated tests")
    
    def test_create_sos_alert(self, auth_token):
        """Create SOS alert should work"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        payload = {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "address": "Test Address, Los Angeles, CA"
        }
        response = requests.post(f"{BASE_URL}/api/sos", json=payload, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "alert_id" in data
        assert data["status"] == "active"
        assert data["latitude"] == payload["latitude"]
        print(f"✓ Create SOS alert passed - alert_id: {data['alert_id']}")
        
        # Resolve the alert
        alert_id = data["alert_id"]
        resolve_response = requests.post(f"{BASE_URL}/api/sos/{alert_id}/resolve", headers=headers)
        assert resolve_response.status_code == 200
        print(f"✓ Resolve SOS alert passed - alert_id: {alert_id}")
    
    def test_get_active_alert(self, auth_token):
        """Get active SOS alert should work"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/sos/active", headers=headers)
        
        # Should return 200 (either with alert or null)
        assert response.status_code == 200
        print("✓ Get active SOS alert passed")


class TestAnalyticsEndpoints:
    """Test Analytics endpoints return valid data"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for tests"""
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Login failed - skipping authenticated tests")
    
    def test_analytics_summary(self, auth_token):
        """Analytics summary should return data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/encounters/summary", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "risk_score" in data
        assert "total_encounters" in data
        print(f"✓ Analytics summary passed - risk_score: {data['risk_score']}")
    
    def test_analytics_patterns(self, auth_token):
        """Analytics patterns should return data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/encounters/patterns", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "by_hour" in data
        assert "by_day" in data
        print(f"✓ Analytics patterns passed")
    
    def test_analytics_hotspots(self, auth_token):
        """Analytics hotspots should return data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/encounters/hotspots", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "hotspots" in data
        assert "total_mapped" in data
        print(f"✓ Analytics hotspots passed - total_mapped: {data['total_mapped']}")
    
    def test_analytics_trends(self, auth_token):
        """Analytics trends should return data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/encounters/trends?days=30", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "period_days" in data
        assert "total_encounters" in data
        print(f"✓ Analytics trends passed - period: {data['period_days']} days")


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
            assert "specializations" in attorney
        print(f"✓ Get attorneys passed - found {len(data)} attorneys")
    
    def test_get_attorneys_by_state(self):
        """Get attorneys filtered by state should work"""
        response = requests.get(f"{BASE_URL}/api/attorneys?state=California")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get attorneys by state passed - found {len(data)} in California")
    
    def test_get_emergency_attorneys(self):
        """Get emergency-available attorneys should work"""
        response = requests.get(f"{BASE_URL}/api/attorneys?available_emergency=true")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ Get emergency attorneys passed - found {len(data)} available")


class TestAIChatEndpoint:
    """Test AI chat endpoint responds"""
    
    @pytest.fixture
    def auth_token(self):
        """Get auth token for tests"""
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        if response.status_code == 200:
            return response.json()["access_token"]
        pytest.skip("Login failed - skipping authenticated tests")
    
    def test_ai_chat_responds(self, auth_token):
        """AI chat should respond to messages"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        payload = {
            "message": "What are my rights during a traffic stop?"
        }
        response = requests.post(f"{BASE_URL}/api/ai/chat", json=payload, headers=headers, timeout=60)
        
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
            assert "risk_score" in dept
        print(f"✓ Get departments passed - found {len(data)} departments")


# Cleanup function to remove test data
def cleanup_test_data():
    """Clean up test data created during tests"""
    # Login to get token
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
