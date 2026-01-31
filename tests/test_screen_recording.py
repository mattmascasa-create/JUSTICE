"""
Screen Recording Feature Tests (v5.5.0)
Tests for screen recording upload and shared screen endpoints
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rights-shield-2.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "modtest2@test.com"
TEST_PASSWORD = "Test123!"
TEST_ENCOUNTER_ID = "enc_e6692f1e966b"
TEST_SHARE_TOKEN = "adbe232a15954e11"


class TestHealthEndpoint:
    """Test health endpoint shows screen_recording feature"""
    
    def test_health_shows_screen_recording_feature(self):
        """Health endpoint should show version 5.5.0 with screen_recording enabled"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["version"] == "5.5.0"
        assert data["features"]["screen_recording"] == True
        assert data["features"]["video_streaming"] == True
        assert data["features"]["real_time_sharing"] == True


class TestSharedEncounterScreenRecordingField:
    """Test shared encounter endpoint returns has_screen_recording field"""
    
    def test_shared_encounter_has_screen_recording_field(self):
        """Shared encounter should include has_screen_recording field"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "has_screen_recording" in data
        # Currently no screen recordings exist
        assert data["has_screen_recording"] == False


class TestScreenChunksEndpoint:
    """Test GET /api/encounters/shared/{id}/screen/chunks endpoint"""
    
    def test_get_screen_chunks_with_valid_token(self):
        """Should return screen chunk list with valid token"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/screen/chunks",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["encounter_id"] == TEST_ENCOUNTER_ID
        assert "total_chunks" in data
        assert "chunk_duration_seconds" in data
        assert data["chunk_duration_seconds"] == 15
        assert "chunks" in data
        assert isinstance(data["chunks"], list)
        assert "has_screen_recording" in data
        assert "status" in data
        assert "started_at" in data
    
    def test_get_screen_chunks_with_invalid_token(self):
        """Should return 403 with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/screen/chunks",
            params={"token": "invalid_token"}
        )
        assert response.status_code == 403
        assert "Invalid or expired share link" in response.json()["detail"]
    
    def test_get_screen_chunks_for_nonexistent_encounter(self):
        """Should return 404 for non-existent encounter"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/enc_nonexistent/screen/chunks",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 404
        assert "Encounter not found" in response.json()["detail"]
    
    def test_get_screen_chunks_without_token(self):
        """Should return 422 without token parameter"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/screen/chunks"
        )
        assert response.status_code == 422


class TestScreenChunkFileEndpoint:
    """Test GET /api/encounters/shared/{id}/screen/{filename} endpoint"""
    
    def test_get_screen_chunk_file_with_invalid_token(self):
        """Should return 403 with invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/screen/screen_chunk_0.webm",
            params={"token": "invalid_token"}
        )
        assert response.status_code == 403
        assert "Invalid or expired share link" in response.json()["detail"]
    
    def test_get_screen_chunk_file_not_found(self):
        """Should return 404 for non-existent screen chunk"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/screen/screen_chunk_0.webm",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 404
        assert "Screen recording chunk not found" in response.json()["detail"]
    
    def test_get_screen_chunk_file_for_nonexistent_encounter(self):
        """Should return 404 for non-existent encounter"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/enc_nonexistent/screen/screen_chunk_0.webm",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 404


class TestScreenUploadEndpoint:
    """Test POST /api/encounters/{id}/screen endpoint (requires auth)"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("token")
        pytest.skip("Authentication failed - skipping authenticated tests")
    
    def test_screen_upload_without_auth(self):
        """Should return 401 or 403 without authentication"""
        files = {"screen": ("screen_chunk_0.webm", b"test content", "video/webm")}
        data = {"chunk_index": 0}
        
        response = requests.post(
            f"{BASE_URL}/api/encounters/{TEST_ENCOUNTER_ID}/screen",
            files=files,
            data=data
        )
        # API returns 403 for unauthorized access
        assert response.status_code in [401, 403]
    
    def test_screen_upload_for_nonexistent_encounter(self, auth_token):
        """Should return 404 for non-existent encounter"""
        if not auth_token:
            pytest.skip("Auth token not available")
            
        files = {"screen": ("screen_chunk_0.webm", b"test content", "video/webm")}
        data = {"chunk_index": 0}
        
        response = requests.post(
            f"{BASE_URL}/api/encounters/enc_nonexistent/screen",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        # Should return 404 for non-existent encounter or 401 if token invalid
        assert response.status_code in [404, 401]


class TestVideoChunksStillWork:
    """Verify video chunks endpoint still works alongside screen recording"""
    
    def test_video_chunks_endpoint_still_works(self):
        """Video chunks endpoint should still work"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/video/chunks",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "chunks" in data
        assert "total_chunks" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
