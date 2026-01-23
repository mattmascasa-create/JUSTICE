"""
JUSTICE Platform - Modular Architecture Regression Tests (v5.2.0)

This test file verifies all endpoints work correctly after switching
from the monolithic server.py to the new modular app/main.py architecture.

Endpoints tested:
- Health endpoint (/api/health)
- User registration (/api/auth/register)
- User login (/api/auth/login)
- Get current user (/api/auth/me)
- Cases CRUD operations (/api/cases)
- Rights articles (/api/rights)
- Community submissions (/api/community/submissions)
- Analytics endpoints (/api/analytics/encounters/summary)
"""

import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

# Get BASE_URL from environment
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    BASE_URL = "https://rightguardian.preview.emergentagent.com"

# Test credentials - use provided test user
TEST_EMAIL = "modtest2@test.com"
TEST_PASSWORD = "Test123!"
TEST_NAME = "Module Test User"

# Unique test email for registration test
UNIQUE_TEST_EMAIL = f"modtest_{uuid.uuid4().hex[:8]}@test.com"


class TestHealthEndpoint:
    """Test health endpoint returns correct status with version 5.2.0"""
    
    def test_health_returns_healthy(self):
        """Health endpoint should return healthy status with version 5.2.0"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "5.2.0", f"Expected version 5.2.0, got {data['version']}"
        print(f"✓ Health check passed - version: {data['version']}")


class TestUserRegistration:
    """Test user registration API (/api/auth/register)"""
    
    def test_register_new_user(self):
        """Registration should create new user and return token"""
        payload = {
            "email": UNIQUE_TEST_EMAIL,
            "password": TEST_PASSWORD,
            "name": "New Test User"
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        
        assert response.status_code == 200, f"Registration failed: {response.text}"
        data = response.json()
        
        assert "access_token" in data, "No access_token in response"
        assert "user" in data, "No user in response"
        assert data["user"]["email"] == UNIQUE_TEST_EMAIL
        assert data["user"]["role"] == "citizen"
        print(f"✓ User registration passed - user_id: {data['user']['user_id']}")
    
    def test_register_duplicate_email_fails(self):
        """Registration with existing email should fail with 400"""
        payload = {
            "email": TEST_EMAIL,  # Use existing test user email
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        }
        response = requests.post(f"{BASE_URL}/api/auth/register", json=payload)
        
        # Should fail with 400 for duplicate email
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "already registered" in data.get("detail", "").lower()
        print("✓ Duplicate registration correctly rejected (400)")


class TestUserLogin:
    """Test user login API (/api/auth/login)"""
    
    def test_login_success(self):
        """Login with valid credentials should return token"""
        payload = {
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        assert "access_token" in data, "No access_token in response"
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        print(f"✓ Login passed - token received")
    
    def test_login_invalid_credentials(self):
        """Login with invalid credentials should fail with 401"""
        payload = {
            "email": TEST_EMAIL,
            "password": "wrongpassword123"
        }
        response = requests.post(f"{BASE_URL}/api/auth/login", json=payload)
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid login correctly rejected (401)")


class TestGetCurrentUser:
    """Test get current user API (/api/auth/me)"""
    
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
    
    def test_get_me_authenticated(self, auth_token):
        """Get /api/auth/me with valid token should return user data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        
        assert response.status_code == 200, f"Get me failed: {response.text}"
        data = response.json()
        
        assert data["email"] == TEST_EMAIL
        assert "user_id" in data
        assert "name" in data
        assert "role" in data
        print(f"✓ Get current user passed - user_id: {data['user_id']}")
    
    def test_get_me_unauthenticated(self):
        """Get /api/auth/me without token should fail with 401 or 403"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Unauthenticated request correctly rejected ({response.status_code})")


class TestRightsEndpoint:
    """Test rights articles endpoint (/api/rights)"""
    
    def test_get_all_rights_categories(self):
        """Get /api/rights should return all rights categories"""
        response = requests.get(f"{BASE_URL}/api/rights")
        
        assert response.status_code == 200, f"Get rights failed: {response.text}"
        data = response.json()
        
        assert "categories" in data
        assert "count" in data
        assert data["count"] > 0
        assert "traffic_stop" in data["categories"]
        assert "arrest" in data["categories"]
        print(f"✓ Get rights categories passed - {data['count']} categories")
    
    def test_get_rights_by_category(self):
        """Get /api/rights/{category} should return detailed rights info"""
        response = requests.get(f"{BASE_URL}/api/rights/traffic_stop")
        
        assert response.status_code == 200, f"Get rights category failed: {response.text}"
        data = response.json()
        
        assert "title" in data
        assert "key_rights" in data
        assert "dos" in data
        assert "donts" in data
        assert len(data["key_rights"]) > 0
        print(f"✓ Get rights by category passed - {data['title']}")
    
    def test_get_quick_rights_reminder(self):
        """Get /api/rights/quick/{situation} should return quick reminder"""
        response = requests.get(f"{BASE_URL}/api/rights/quick/traffic_stop")
        
        assert response.status_code == 200, f"Get quick rights failed: {response.text}"
        data = response.json()
        
        assert "situation" in data
        assert "reminder" in data
        assert data["situation"] == "traffic_stop"
        print(f"✓ Get quick rights reminder passed")


class TestCommunitySubmissions:
    """Test community submissions endpoint (/api/community/submissions)"""
    
    def test_get_community_submissions(self):
        """Get /api/community/submissions should return submissions list"""
        response = requests.get(f"{BASE_URL}/api/community/submissions")
        
        assert response.status_code == 200, f"Get submissions failed: {response.text}"
        data = response.json()
        
        assert "submissions" in data
        assert "total" in data
        assert "limit" in data
        assert "skip" in data
        assert isinstance(data["submissions"], list)
        print(f"✓ Get community submissions passed - {data['total']} total")
    
    def test_get_community_stats(self):
        """Get /api/community/stats should return aggregated stats"""
        response = requests.get(f"{BASE_URL}/api/community/stats")
        
        assert response.status_code == 200, f"Get stats failed: {response.text}"
        data = response.json()
        
        assert "total_submissions" in data
        assert "by_state" in data
        assert "by_violation_type" in data
        print(f"✓ Get community stats passed - {data['total_submissions']} submissions")
    
    def test_search_community_vault(self):
        """Get /api/community/search should search submissions"""
        response = requests.get(f"{BASE_URL}/api/community/search?query=test")
        
        assert response.status_code == 200, f"Search failed: {response.text}"
        data = response.json()
        
        assert "query" in data
        assert "results" in data
        assert "count" in data
        print(f"✓ Search community vault passed - {data['count']} results")


class TestCasesCRUD:
    """Test Cases CRUD operations (/api/cases)"""
    
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
        """POST /api/cases should create a new case"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        payload = {
            "title": "TEST_Modular Regression Case",
            "description": "Test case for modular architecture regression",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "location": "Test Location, CA",
            "violation_type": "4th Amendment",
            "severity": "medium"
        }
        response = requests.post(f"{BASE_URL}/api/cases", json=payload, headers=headers)
        
        assert response.status_code == 200, f"Create case failed: {response.text}"
        data = response.json()
        
        assert "case_id" in data
        assert data["title"] == payload["title"]
        assert data["status"] == "open"
        print(f"✓ Create case passed - case_id: {data['case_id']}")
        
        return data["case_id"]
    
    def test_get_cases(self, auth_token):
        """GET /api/cases should return list of user's cases"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/cases", headers=headers)
        
        assert response.status_code == 200, f"Get cases failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list)
        print(f"✓ Get cases passed - found {len(data)} cases")
    
    def test_case_crud_flow(self, auth_token):
        """Test complete CRUD flow: Create -> Read -> Update -> Delete"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # CREATE
        payload = {
            "title": "TEST_CRUD Flow Case",
            "description": "Test case for CRUD flow",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "location": "CRUD Test Location, CA",
            "violation_type": "5th Amendment",
            "severity": "low"
        }
        create_response = requests.post(f"{BASE_URL}/api/cases", json=payload, headers=headers)
        assert create_response.status_code == 200
        case_id = create_response.json()["case_id"]
        print(f"  ✓ CREATE passed - case_id: {case_id}")
        
        # READ
        read_response = requests.get(f"{BASE_URL}/api/cases/{case_id}", headers=headers)
        assert read_response.status_code == 200
        assert read_response.json()["case_id"] == case_id
        print(f"  ✓ READ passed - case_id: {case_id}")
        
        # UPDATE
        update_payload = {"status": "under_review", "severity": "high"}
        update_response = requests.patch(f"{BASE_URL}/api/cases/{case_id}", json=update_payload, headers=headers)
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "under_review"
        print(f"  ✓ UPDATE passed - case_id: {case_id}")
        
        # Verify update persisted
        verify_response = requests.get(f"{BASE_URL}/api/cases/{case_id}", headers=headers)
        assert verify_response.json()["status"] == "under_review"
        assert verify_response.json()["severity"] == "high"
        print(f"  ✓ UPDATE VERIFIED - case_id: {case_id}")
        
        # DELETE
        delete_response = requests.delete(f"{BASE_URL}/api/cases/{case_id}", headers=headers)
        assert delete_response.status_code == 200
        print(f"  ✓ DELETE passed - case_id: {case_id}")
        
        # Verify deletion
        verify_delete = requests.get(f"{BASE_URL}/api/cases/{case_id}", headers=headers)
        assert verify_delete.status_code == 404
        print(f"  ✓ DELETE VERIFIED - case returns 404")
        
        print(f"✓ Complete CRUD flow passed")


class TestAnalyticsEndpoints:
    """Test Analytics endpoints (/api/analytics/encounters/summary)"""
    
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
        """GET /api/analytics/encounters/summary should return analytics data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/encounters/summary", headers=headers)
        
        assert response.status_code == 200, f"Analytics summary failed: {response.text}"
        data = response.json()
        
        assert "risk_score" in data
        assert "total_encounters" in data
        assert "officer_demeanor" in data
        assert "tone_distribution" in data
        print(f"✓ Analytics summary passed - risk_score: {data['risk_score']}")
    
    def test_analytics_patterns(self, auth_token):
        """GET /api/analytics/encounters/patterns should return pattern data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/encounters/patterns", headers=headers)
        
        assert response.status_code == 200, f"Analytics patterns failed: {response.text}"
        data = response.json()
        
        assert "by_hour" in data
        assert "by_day" in data
        assert "by_type" in data
        print(f"✓ Analytics patterns passed")
    
    def test_analytics_hotspots(self, auth_token):
        """GET /api/analytics/encounters/hotspots should return hotspot data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/encounters/hotspots", headers=headers)
        
        assert response.status_code == 200, f"Analytics hotspots failed: {response.text}"
        data = response.json()
        
        assert "hotspots" in data
        assert "all_locations" in data
        assert "total_mapped" in data
        print(f"✓ Analytics hotspots passed - total_mapped: {data['total_mapped']}")
    
    def test_analytics_trends(self, auth_token):
        """GET /api/analytics/encounters/trends should return trend data"""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{BASE_URL}/api/analytics/encounters/trends?days=30", headers=headers)
        
        assert response.status_code == 200, f"Analytics trends failed: {response.text}"
        data = response.json()
        
        assert "period_days" in data
        assert "total_encounters" in data
        assert "daily_data" in data
        print(f"✓ Analytics trends passed - period: {data['period_days']} days")


# Cleanup function
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
