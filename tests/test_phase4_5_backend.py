"""
Phase 4 & 5 Backend API Tests - JUSTICE Platform
Tests for Encounter Mode, Document Analysis, Rights Coach, Similar Cases, and Emergency Contacts
"""
import pytest
import requests
import os
import json
import io
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://police-watch-2.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "encounter_test@example.com"
TEST_PASSWORD = "password123"
TEST_NAME = "Encounter Test User"


class TestSetup:
    """Setup tests - register/login test user"""
    
    @pytest.fixture(scope="class")
    def session(self):
        return requests.Session()
    
    def test_register_or_login(self, session):
        """Register new user or login existing"""
        # Try to register
        register_response = session.post(f"{BASE_URL}/api/auth/register", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "name": TEST_NAME
        })
        
        if register_response.status_code == 400:
            # User exists, login instead
            login_response = session.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
            assert login_response.status_code == 200, f"Login failed: {login_response.text}"
            data = login_response.json()
            token = data.get("access_token")
        else:
            assert register_response.status_code == 200, f"Register failed: {register_response.text}"
            data = register_response.json()
            token = data.get("access_token")
        
        assert token is not None, "No token received"
        session.headers.update({"Authorization": f"Bearer {token}"})
        return token


class TestEncounterMode:
    """Test Encounter Mode endpoints - Phase 4"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Get authenticated session"""
        session = requests.Session()
        # Login
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if login_response.status_code != 200:
            # Register first
            session.post(f"{BASE_URL}/api/auth/register", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "name": TEST_NAME
            })
            login_response = session.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
        
        token = login_response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_start_encounter(self, auth_session):
        """POST /api/encounters/start - Create new encounter"""
        response = auth_session.post(f"{BASE_URL}/api/encounters/start", json={
            "latitude": 34.0522,
            "longitude": -118.2437,
            "address": "123 Test Street, Los Angeles, CA",
            "encounter_type": "traffic_stop",
            "broadcast_mode": "save"
        })
        
        assert response.status_code == 200, f"Start encounter failed: {response.text}"
        data = response.json()
        
        # Validate response structure
        assert "encounter_id" in data, "Missing encounter_id"
        assert "user_id" in data, "Missing user_id"
        assert "status" in data, "Missing status"
        assert data["status"] == "active", f"Expected status 'active', got '{data['status']}'"
        assert data["encounter_type"] == "traffic_stop"
        assert data["broadcast_mode"] == "save"
        assert "stream_key" in data, "Missing stream_key"
        
        # Store encounter_id for later tests
        auth_session.encounter_id = data["encounter_id"]
        return data["encounter_id"]
    
    def test_start_encounter_requires_auth(self):
        """Verify encounter start requires authentication"""
        response = requests.post(f"{BASE_URL}/api/encounters/start", json={
            "latitude": 34.0522,
            "longitude": -118.2437,
            "encounter_type": "traffic_stop",
            "broadcast_mode": "save"
        })
        assert response.status_code == 401, "Should require authentication"
    
    def test_list_encounters(self, auth_session):
        """GET /api/encounters - List user encounters"""
        response = auth_session.get(f"{BASE_URL}/api/encounters")
        
        assert response.status_code == 200, f"List encounters failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of encounters"
    
    def test_list_encounters_with_status_filter(self, auth_session):
        """GET /api/encounters?status=active - Filter by status"""
        response = auth_session.get(f"{BASE_URL}/api/encounters", params={"status": "active"})
        
        assert response.status_code == 200, f"List encounters with filter failed: {response.text}"
        data = response.json()
        assert isinstance(data, list)
        # All returned encounters should be active
        for enc in data:
            assert enc.get("status") == "active", f"Expected active status, got {enc.get('status')}"
    
    def test_get_encounter_details(self, auth_session):
        """GET /api/encounters/{id} - Get encounter details"""
        # First create an encounter
        create_response = auth_session.post(f"{BASE_URL}/api/encounters/start", json={
            "latitude": 34.0522,
            "longitude": -118.2437,
            "encounter_type": "pedestrian_stop",
            "broadcast_mode": "save"
        })
        assert create_response.status_code == 200
        encounter_id = create_response.json()["encounter_id"]
        
        # Get details
        response = auth_session.get(f"{BASE_URL}/api/encounters/{encounter_id}")
        
        assert response.status_code == 200, f"Get encounter failed: {response.text}"
        data = response.json()
        
        assert "encounter" in data, "Missing encounter data"
        assert "transcriptions" in data, "Missing transcriptions"
        assert data["encounter"]["encounter_id"] == encounter_id
    
    def test_get_nonexistent_encounter(self, auth_session):
        """GET /api/encounters/{id} - 404 for non-existent"""
        response = auth_session.get(f"{BASE_URL}/api/encounters/enc_nonexistent123")
        assert response.status_code == 404, "Should return 404 for non-existent encounter"
    
    def test_add_officer_info(self, auth_session):
        """POST /api/encounters/{id}/officer - Add officer info"""
        # Create encounter first
        create_response = auth_session.post(f"{BASE_URL}/api/encounters/start", json={
            "latitude": 34.0522,
            "longitude": -118.2437,
            "encounter_type": "traffic_stop",
            "broadcast_mode": "save"
        })
        encounter_id = create_response.json()["encounter_id"]
        
        # Add officer info using form data
        response = auth_session.post(
            f"{BASE_URL}/api/encounters/{encounter_id}/officer",
            data={
                "name": "Officer Test",
                "badge_number": "12345",
                "department": "LAPD"
            }
        )
        
        assert response.status_code == 200, f"Add officer failed: {response.text}"
        data = response.json()
        
        assert "officer_id" in data, "Missing officer_id"
        assert data["name"] == "Officer Test"
        assert data["badge_number"] == "12345"
        assert data["department"] == "LAPD"
    
    def test_end_encounter(self, auth_session):
        """POST /api/encounters/{id}/end - End encounter"""
        # Create encounter first
        create_response = auth_session.post(f"{BASE_URL}/api/encounters/start", json={
            "latitude": 34.0522,
            "longitude": -118.2437,
            "encounter_type": "traffic_stop",
            "broadcast_mode": "save"
        })
        encounter_id = create_response.json()["encounter_id"]
        
        # End encounter
        response = auth_session.post(f"{BASE_URL}/api/encounters/{encounter_id}/end")
        
        assert response.status_code == 200, f"End encounter failed: {response.text}"
        data = response.json()
        
        assert data["status"] == "ended", f"Expected status 'ended', got '{data['status']}'"
        assert "duration_seconds" in data
        assert data["encounter_id"] == encounter_id
    
    def test_end_nonexistent_encounter(self, auth_session):
        """POST /api/encounters/{id}/end - 404 for non-existent"""
        response = auth_session.post(f"{BASE_URL}/api/encounters/enc_nonexistent123/end")
        assert response.status_code == 404, "Should return 404 for non-existent encounter"


class TestDocumentAnalysis:
    """Test Document Analysis endpoints - Phase 5"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Get authenticated session"""
        session = requests.Session()
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if login_response.status_code != 200:
            session.post(f"{BASE_URL}/api/auth/register", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "name": TEST_NAME
            })
            login_response = session.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
        
        token = login_response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_analyze_document_txt(self, auth_session):
        """POST /api/analyze/document - Analyze text document"""
        # Create a test text file
        test_content = """Police Report - Incident #2024-12345
        
        On January 15, 2024, Officer Smith conducted a traffic stop on Main Street.
        The suspect was asked to exit the vehicle and was searched without consent.
        The officer stated "You people always have something to hide."
        The suspect was detained for 45 minutes without being told why.
        """
        
        files = {
            'file': ('test_report.txt', test_content, 'text/plain')
        }
        data = {
            'document_type': 'police_report',
            'analysis_focus': 'all'
        }
        
        response = auth_session.post(
            f"{BASE_URL}/api/analyze/document",
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Document analysis failed: {response.text}"
        result = response.json()
        
        assert "analysis_id" in result, "Missing analysis_id"
        assert "document_id" in result, "Missing document_id"
        assert "document_type" in result
        assert result["document_type"] == "police_report"
    
    def test_analyze_document_requires_auth(self):
        """Verify document analysis requires authentication"""
        files = {
            'file': ('test.txt', 'Test content', 'text/plain')
        }
        response = requests.post(
            f"{BASE_URL}/api/analyze/document",
            files=files,
            data={'document_type': 'other', 'analysis_focus': 'all'}
        )
        assert response.status_code == 401, "Should require authentication"
    
    def test_list_document_analyses(self, auth_session):
        """GET /api/analyze/documents - List analyses"""
        response = auth_session.get(f"{BASE_URL}/api/analyze/documents")
        
        assert response.status_code == 200, f"List analyses failed: {response.text}"
        data = response.json()
        assert isinstance(data, list), "Expected list of analyses"


class TestRightsCoach:
    """Test Rights Coach endpoint - Phase 5"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Get authenticated session"""
        session = requests.Session()
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if login_response.status_code != 200:
            session.post(f"{BASE_URL}/api/auth/register", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "name": TEST_NAME
            })
            login_response = session.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
        
        token = login_response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_rights_coach_search_situation(self, auth_session):
        """POST /api/rights-coach - Get guidance for search situation"""
        response = auth_session.post(
            f"{BASE_URL}/api/rights-coach",
            data={"situation": "Officer wants to search my car trunk"}
        )
        
        assert response.status_code == 200, f"Rights coach failed: {response.text}"
        data = response.json()
        
        # Should have guidance structure
        assert "immediate_action" in data or "your_rights" in data, "Missing guidance fields"
    
    def test_rights_coach_arrest_situation(self, auth_session):
        """POST /api/rights-coach - Get guidance for arrest situation"""
        response = auth_session.post(
            f"{BASE_URL}/api/rights-coach",
            data={"situation": "I am being arrested"}
        )
        
        assert response.status_code == 200, f"Rights coach failed: {response.text}"
        data = response.json()
        
        # Should have guidance
        assert "immediate_action" in data or "your_rights" in data
    
    def test_rights_coach_requires_auth(self):
        """Verify rights coach requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/rights-coach",
            data={"situation": "Test situation"}
        )
        assert response.status_code == 401, "Should require authentication"


class TestSimilarCases:
    """Test Similar Cases search endpoint - Phase 5"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Get authenticated session"""
        session = requests.Session()
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if login_response.status_code != 200:
            session.post(f"{BASE_URL}/api/auth/register", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "name": TEST_NAME
            })
            login_response = session.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
        
        token = login_response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_search_similar_cases_4th_amendment(self, auth_session):
        """GET /api/cases/similar - Search for 4th Amendment cases"""
        response = auth_session.get(
            f"{BASE_URL}/api/cases/similar",
            params={"violation_type": "4th Amendment"}
        )
        
        assert response.status_code == 200, f"Similar cases search failed: {response.text}"
        data = response.json()
        
        assert "landmark_cases" in data, "Missing landmark_cases"
        assert "similar_cases_in_system" in data, "Missing similar_cases_in_system"
        
        # Should include Terry v. Ohio for 4th Amendment
        landmark_names = [c.get("case_name", "") for c in data["landmark_cases"]]
        assert any("Terry" in name for name in landmark_names), "Should include Terry v. Ohio"
    
    def test_search_similar_cases_excessive_force(self, auth_session):
        """GET /api/cases/similar - Search for excessive force cases"""
        response = auth_session.get(
            f"{BASE_URL}/api/cases/similar",
            params={"violation_type": "Excessive Force"}
        )
        
        assert response.status_code == 200, f"Similar cases search failed: {response.text}"
        data = response.json()
        
        # Should include Graham v. Connor for excessive force
        landmark_names = [c.get("case_name", "") for c in data["landmark_cases"]]
        assert any("Graham" in name for name in landmark_names), "Should include Graham v. Connor"
    
    def test_search_similar_cases_requires_auth(self):
        """Verify similar cases search requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/cases/similar",
            params={"violation_type": "4th Amendment"}
        )
        assert response.status_code == 401, "Should require authentication"


class TestEmergencyContacts:
    """Test Emergency Contacts endpoints - Phase 5"""
    
    @pytest.fixture(scope="class")
    def auth_session(self):
        """Get authenticated session"""
        session = requests.Session()
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        if login_response.status_code != 200:
            session.post(f"{BASE_URL}/api/auth/register", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "name": TEST_NAME
            })
            login_response = session.post(f"{BASE_URL}/api/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
        
        token = login_response.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {token}"})
        return session
    
    def test_update_emergency_contacts(self, auth_session):
        """POST /api/settings/emergency-contacts - Update contacts"""
        contacts = [
            {
                "name": "Emergency Contact 1",
                "phone": "+1234567890",
                "email": "contact1@example.com",
                "notify_on_encounter": True
            },
            {
                "name": "Emergency Contact 2",
                "phone": "+0987654321",
                "notify_on_encounter": False
            }
        ]
        
        response = auth_session.post(
            f"{BASE_URL}/api/settings/emergency-contacts",
            json=contacts
        )
        
        assert response.status_code == 200, f"Update contacts failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert "contacts" in data
        assert len(data["contacts"]) == 2
    
    def test_get_emergency_contacts(self, auth_session):
        """GET /api/settings/emergency-contacts - Get contacts"""
        # First set some contacts
        auth_session.post(
            f"{BASE_URL}/api/settings/emergency-contacts",
            json=[{"name": "Test Contact", "phone": "+1111111111"}]
        )
        
        response = auth_session.get(f"{BASE_URL}/api/settings/emergency-contacts")
        
        assert response.status_code == 200, f"Get contacts failed: {response.text}"
        data = response.json()
        
        assert isinstance(data, list), "Expected list of contacts"
    
    def test_emergency_contacts_requires_auth(self):
        """Verify emergency contacts requires authentication"""
        response = requests.get(f"{BASE_URL}/api/settings/emergency-contacts")
        assert response.status_code == 401, "Should require authentication"
        
        response = requests.post(
            f"{BASE_URL}/api/settings/emergency-contacts",
            json=[{"name": "Test", "phone": "123"}]
        )
        assert response.status_code == 401, "Should require authentication"


class TestHealthAndRegression:
    """Health check and regression tests for Phase 1-3 features"""
    
    def test_health_check(self):
        """GET /api/health - Health check"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "4.0.0"
    
    def test_auth_endpoints_still_work(self):
        """Verify auth endpoints still work (regression)"""
        # Login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get me
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=headers)
        assert response.status_code == 200
    
    def test_cases_endpoints_still_work(self):
        """Verify cases endpoints still work (regression)"""
        session = requests.Session()
        login_response = session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = login_response.json()["access_token"]
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        # List cases
        response = session.get(f"{BASE_URL}/api/cases")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_attorneys_endpoint_still_works(self):
        """Verify attorneys endpoint still works (regression)"""
        response = requests.get(f"{BASE_URL}/api/attorneys")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_departments_endpoint_still_works(self):
        """Verify departments endpoint still works (regression)"""
        response = requests.get(f"{BASE_URL}/api/departments")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
