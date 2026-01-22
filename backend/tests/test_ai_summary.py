"""
Test AI Transcript Summary Feature
Tests for POST /api/calls/{recording_id}/summarize and GET /api/calls/{recording_id}/summary endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAISummaryEndpoints:
    """Test AI Summary endpoints for call recordings"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.test_user_email = "test@example.com"
        self.test_user_password = "password123"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_auth_token(self, email, password):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        return None
    
    # ============== Health Check ==============
    def test_health_endpoint(self):
        """Test health endpoint returns healthy status"""
        response = self.session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Health check passed - version {data.get('version')}")
    
    # ============== Authentication ==============
    def test_user_login(self):
        """Test user can login"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.test_user_email,
            "password": self.test_user_password
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data or "token" in data
        print(f"✓ User login successful")
    
    # ============== POST /api/calls/{recording_id}/summarize ==============
    def test_summarize_nonexistent_recording_returns_404(self):
        """Test POST /api/calls/{recording_id}/summarize returns 404 for non-existent recording"""
        token = self.get_auth_token(self.test_user_email, self.test_user_password)
        assert token is not None, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Use a fake recording ID
        fake_recording_id = "rec_nonexistent123"
        response = self.session.post(f"{BASE_URL}/api/calls/{fake_recording_id}/summarize")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✓ POST /api/calls/{fake_recording_id}/summarize returns 404 for non-existent recording")
        print(f"  Response: {data}")
    
    # ============== GET /api/calls/{recording_id}/summary ==============
    def test_get_summary_nonexistent_recording_returns_404(self):
        """Test GET /api/calls/{recording_id}/summary returns 404 for non-existent recording"""
        token = self.get_auth_token(self.test_user_email, self.test_user_password)
        assert token is not None, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Use a fake recording ID
        fake_recording_id = "rec_nonexistent456"
        response = self.session.get(f"{BASE_URL}/api/calls/{fake_recording_id}/summary")
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✓ GET /api/calls/{fake_recording_id}/summary returns 404 for non-existent recording")
        print(f"  Response: {data}")
    
    # ============== Endpoint Existence Tests ==============
    def test_summarize_endpoint_exists(self):
        """Test that POST /api/calls/{recording_id}/summarize endpoint exists (not 405 Method Not Allowed)"""
        token = self.get_auth_token(self.test_user_email, self.test_user_password)
        assert token is not None, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Use a fake recording ID - we expect 404 (not found) not 405 (method not allowed)
        fake_recording_id = "rec_test123"
        response = self.session.post(f"{BASE_URL}/api/calls/{fake_recording_id}/summarize")
        
        # Should be 404 (recording not found) not 405 (method not allowed)
        assert response.status_code != 405, "Endpoint does not exist (405 Method Not Allowed)"
        print(f"✓ POST /api/calls/{{recording_id}}/summarize endpoint exists (status: {response.status_code})")
    
    def test_get_summary_endpoint_exists(self):
        """Test that GET /api/calls/{recording_id}/summary endpoint exists (not 405 Method Not Allowed)"""
        token = self.get_auth_token(self.test_user_email, self.test_user_password)
        assert token is not None, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Use a fake recording ID - we expect 404 (not found) not 405 (method not allowed)
        fake_recording_id = "rec_test456"
        response = self.session.get(f"{BASE_URL}/api/calls/{fake_recording_id}/summary")
        
        # Should be 404 (recording not found) not 405 (method not allowed)
        assert response.status_code != 405, "Endpoint does not exist (405 Method Not Allowed)"
        print(f"✓ GET /api/calls/{{recording_id}}/summary endpoint exists (status: {response.status_code})")
    
    # ============== Authorization Tests ==============
    def test_summarize_requires_auth(self):
        """Test POST /api/calls/{recording_id}/summarize requires authentication"""
        # Clear any existing auth
        self.session.headers.pop("Authorization", None)
        
        fake_recording_id = "rec_test789"
        response = self.session.post(f"{BASE_URL}/api/calls/{fake_recording_id}/summarize")
        
        # 401 or 403 both indicate auth is required
        assert response.status_code in [401, 403], f"Expected 401 or 403, got {response.status_code}"
        print(f"✓ POST /api/calls/{{recording_id}}/summarize requires authentication (status: {response.status_code})")
    
    def test_get_summary_requires_auth(self):
        """Test GET /api/calls/{recording_id}/summary requires authentication"""
        # Clear any existing auth
        self.session.headers.pop("Authorization", None)
        
        fake_recording_id = "rec_test101"
        response = self.session.get(f"{BASE_URL}/api/calls/{fake_recording_id}/summary")
        
        # 401 or 403 both indicate auth is required
        assert response.status_code in [401, 403], f"Expected 401 or 403, got {response.status_code}"
        print(f"✓ GET /api/calls/{{recording_id}}/summary requires authentication (status: {response.status_code})")


class TestRecordingsPageAPI:
    """Test API methods used by RecordingsPage for AI Summary feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.test_user_email = "test@example.com"
        self.test_user_password = "password123"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def get_auth_token(self, email, password):
        """Get authentication token"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": email,
            "password": password
        })
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token") or data.get("token")
        return None
    
    def test_get_my_recordings(self):
        """Test GET /api/calls/recordings/my returns user's recordings"""
        token = self.get_auth_token(self.test_user_email, self.test_user_password)
        assert token is not None, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/calls/recordings/my")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "recordings" in data
        print(f"✓ GET /api/calls/recordings/my returns {len(data['recordings'])} recordings")
    
    def test_search_transcripts(self):
        """Test GET /api/calls/transcripts/search works"""
        token = self.get_auth_token(self.test_user_email, self.test_user_password)
        assert token is not None, "Failed to get auth token"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        response = self.session.get(f"{BASE_URL}/api/calls/transcripts/search", params={"query": "test"})
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "results" in data
        print(f"✓ GET /api/calls/transcripts/search returns {len(data['results'])} results")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
