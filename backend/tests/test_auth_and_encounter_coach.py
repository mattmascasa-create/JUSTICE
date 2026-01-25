"""
Test Auth Flow and Encounter Coach APIs
Tests for P0 auth bug fix and AI-Powered Encounter Coaching feature
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER_EMAIL = "test@example.com"
TEST_USER_PASSWORD = "password123"
ATTORNEY_EMAIL = "my_attorney@lawfirm.com"
ATTORNEY_PASSWORD = "attorney123"


class TestAuthFlow:
    """Test authentication flow - P0 bug fix verification"""
    
    def test_login_success(self):
        """Test login with valid credentials returns 200 and token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "access_token" in data, "Missing access_token"
        assert "user" in data, "Missing user data"
        assert data["user"]["email"] == TEST_USER_EMAIL
        assert len(data["access_token"]) > 0
        print(f"✓ Login successful - Token: {data['access_token'][:50]}...")
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "wrong@example.com", "password": "wrongpass"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Invalid credentials correctly rejected with 401")
    
    def test_auth_me_with_valid_token(self):
        """Test /auth/me returns user data with valid token"""
        # Login first
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        token = login_response.json()["access_token"]
        
        # Test /auth/me
        response = requests.get(
            f"{BASE_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200, f"Auth/me failed: {response.text}"
        data = response.json()
        
        assert data["email"] == TEST_USER_EMAIL
        assert "user_id" in data
        print(f"✓ Auth/me returned user: {data['email']}")
    
    def test_auth_me_without_token(self):
        """Test /auth/me returns 401 or 403 without token"""
        response = requests.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Auth/me correctly requires authentication (returns {response.status_code})")
    
    def test_attorney_login(self):
        """Test attorney login works"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ATTORNEY_EMAIL, "password": ATTORNEY_PASSWORD}
        )
        assert response.status_code == 200, f"Attorney login failed: {response.text}"
        data = response.json()
        
        assert data["user"]["role"] == "attorney"
        print(f"✓ Attorney login successful - Role: {data['user']['role']}")


class TestEncounterCoachQuickResponses:
    """Test Encounter Coach quick response endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_quick_responses(self):
        """Test GET /encounter-coach/quick-responses returns scenarios list"""
        response = requests.get(
            f"{BASE_URL}/api/encounter-coach/quick-responses",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert "scenarios" in data
        assert len(data["scenarios"]) > 0
        
        # Verify expected scenarios exist
        expected_scenarios = ["refuse_search", "invoke_silence", "request_attorney"]
        for scenario in expected_scenarios:
            assert scenario in data["scenarios"], f"Missing scenario: {scenario}"
        
        print(f"✓ Quick responses list returned {len(data['scenarios'])} scenarios")
    
    def test_get_quick_response_refuse_search(self):
        """Test GET /encounter-coach/quick-response/refuse_search"""
        response = requests.get(
            f"{BASE_URL}/api/encounter-coach/quick-response/refuse_search",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert data["scenario"] == "refuse_search"
        assert "response" in data
        assert "say" in data["response"]
        print(f"✓ Refuse search response: '{data['response']['say'][:50]}...'")
    
    def test_get_quick_response_invoke_silence(self):
        """Test GET /encounter-coach/quick-response/invoke_silence"""
        response = requests.get(
            f"{BASE_URL}/api/encounter-coach/quick-response/invoke_silence",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert data["scenario"] == "invoke_silence"
        print(f"✓ Invoke silence response received")
    
    def test_get_quick_response_request_attorney(self):
        """Test GET /encounter-coach/quick-response/request_attorney"""
        response = requests.get(
            f"{BASE_URL}/api/encounter-coach/quick-response/request_attorney",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert data["scenario"] == "request_attorney"
        print(f"✓ Request attorney response received")
    
    def test_quick_response_requires_auth(self):
        """Test quick response requires authentication"""
        response = requests.get(
            f"{BASE_URL}/api/encounter-coach/quick-response/refuse_search"
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Quick response correctly requires authentication (returns {response.status_code})")


class TestEncounterCoachEncounterTypes:
    """Test Encounter Coach encounter types endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_encounter_types(self):
        """Test GET /encounter-coach/encounter-types returns types list"""
        response = requests.get(
            f"{BASE_URL}/api/encounter-coach/encounter-types",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert "encounter_types" in data
        
        # Verify expected types exist
        expected_types = ["traffic_stop", "pedestrian_stop", "home_encounter", "arrest"]
        for etype in expected_types:
            assert etype in data["encounter_types"], f"Missing type: {etype}"
        
        # Verify structure
        traffic_stop = data["encounter_types"]["traffic_stop"]
        assert "situations" in traffic_stop
        assert "initial_coaching" in traffic_stop
        
        print(f"✓ Encounter types returned {len(data['encounter_types'])} types")


class TestEncounterCoachAnalyze:
    """Test Encounter Coach analyze endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_analyze_search_request(self):
        """Test analyze detects search request and provides coaching"""
        response = requests.post(
            f"{BASE_URL}/api/encounter-coach/analyze",
            headers=self.headers,
            json={
                "transcript_chunk": "Officer: I need to search your car.",
                "encounter_type": "traffic_stop"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert "coaching" in data
        assert data["coaching_count"] > 0
        
        # Verify coaching structure
        coaching = data["coaching"][0]
        assert "message" in coaching
        assert "category" in coaching
        assert "tone" in coaching
        
        print(f"✓ Analyze returned {data['coaching_count']} coaching messages")
        print(f"  First coaching: {coaching['message'][:60]}...")
    
    def test_analyze_miranda_rights(self):
        """Test analyze detects Miranda rights situation"""
        response = requests.post(
            f"{BASE_URL}/api/encounter-coach/analyze",
            headers=self.headers,
            json={
                "transcript_chunk": "Officer: You have the right to remain silent.",
                "encounter_type": "arrest"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        print(f"✓ Miranda rights analysis returned {data['coaching_count']} coaching messages")
    
    def test_analyze_short_chunk(self):
        """Test analyze handles short chunks gracefully"""
        response = requests.post(
            f"{BASE_URL}/api/encounter-coach/analyze",
            headers=self.headers,
            json={
                "transcript_chunk": "Hi",
                "encounter_type": "general"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert data["message"] == "Chunk too short"
        print("✓ Short chunk handled gracefully")
    
    def test_analyze_requires_auth(self):
        """Test analyze requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/encounter-coach/analyze",
            json={
                "transcript_chunk": "Test transcript",
                "encounter_type": "general"
            }
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Analyze correctly requires authentication (returns {response.status_code})")


class TestEncounterCoachSituations:
    """Test Encounter Coach situation-specific coaching"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_traffic_stop_initial_situation(self):
        """Test GET /encounter-coach/situation/traffic_stop/initial"""
        response = requests.get(
            f"{BASE_URL}/api/encounter-coach/situation/traffic_stop/initial",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert data["encounter_type"] == "traffic_stop"
        assert data["situation"] == "initial"
        assert "coaching" in data
        print(f"✓ Traffic stop initial coaching received")
    
    def test_invalid_encounter_type(self):
        """Test invalid encounter type returns 400"""
        response = requests.get(
            f"{BASE_URL}/api/encounter-coach/situation/invalid_type/initial",
            headers=self.headers
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Invalid encounter type correctly rejected")
    
    def test_invalid_situation(self):
        """Test invalid situation returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/encounter-coach/situation/traffic_stop/invalid_situation",
            headers=self.headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Invalid situation correctly returns 404")


class TestEncounterCoachTriggers:
    """Test Encounter Coach triggers endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_list_triggers(self):
        """Test GET /encounter-coach/triggers returns trigger list"""
        response = requests.get(
            f"{BASE_URL}/api/encounter-coach/triggers",
            headers=self.headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert "categories" in data
        assert "triggers_by_category" in data
        assert "total_triggers" in data
        assert data["total_triggers"] > 0
        
        print(f"✓ Triggers list returned {data['total_triggers']} total triggers")
        print(f"  Categories: {data['categories']}")


class TestEncounterCoachAskEndpoint:
    """Test Encounter Coach ask endpoint for complex questions"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
        )
        self.token = response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_ask_coach_question(self):
        """Test POST /encounter-coach/ask with a question"""
        response = requests.post(
            f"{BASE_URL}/api/encounter-coach/ask",
            headers=self.headers,
            json={
                "question": "Can they search my car without my consent?",
                "transcript_context": "Officer asked to search my vehicle",
                "encounter_type": "traffic_stop"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        assert data["success"] == True
        assert "coaching" in data
        assert "tone" in data
        print(f"✓ Ask coach returned coaching with tone: {data['tone']}")
    
    def test_ask_short_question_rejected(self):
        """Test short questions are rejected"""
        response = requests.post(
            f"{BASE_URL}/api/encounter-coach/ask",
            headers=self.headers,
            json={
                "question": "Hi",
                "encounter_type": "general"
            }
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Short question correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
