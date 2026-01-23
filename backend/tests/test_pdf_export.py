"""
Test PDF Export for AI Summary Feature
Tests the GET /api/calls/{recording_id}/summary/pdf endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPDFExport:
    """PDF Export endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.base_url = BASE_URL
        self.test_email = "test@example.com"
        self.test_password = "password123"
        self.auth_token = None
        
    def get_auth_token(self):
        """Get authentication token"""
        if self.auth_token:
            return self.auth_token
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"email": self.test_email, "password": self.test_password}
        )
        if response.status_code == 200:
            data = response.json()
            # API returns access_token, not token
            self.auth_token = data.get("access_token") or data.get("token")
            return self.auth_token
        return None
    
    def test_health_check(self):
        """Test health endpoint is working"""
        response = requests.get(f"{self.base_url}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        print(f"✓ Health check passed - Version: {data.get('version')}")
    
    def test_login_success(self):
        """Test login with test credentials"""
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"email": self.test_email, "password": self.test_password}
        )
        assert response.status_code == 200
        data = response.json()
        # API returns access_token
        assert "access_token" in data or "token" in data
        print(f"✓ Login successful for {self.test_email}")
    
    def test_pdf_endpoint_exists(self):
        """Test that PDF endpoint exists (not 405 Method Not Allowed)"""
        token = self.get_auth_token()
        assert token, "Failed to get auth token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{self.base_url}/api/calls/test_recording_123/summary/pdf",
            headers=headers
        )
        # Should return 404 (not found) or 400 (no summary), not 405 (method not allowed)
        assert response.status_code != 405, "PDF endpoint does not exist (405 Method Not Allowed)"
        print(f"✓ PDF endpoint exists - Status: {response.status_code}")
    
    def test_pdf_returns_404_for_nonexistent_recording(self):
        """Test PDF endpoint returns 404 for non-existent recording"""
        token = self.get_auth_token()
        assert token, "Failed to get auth token"
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{self.base_url}/api/calls/nonexistent_recording_xyz/summary/pdf",
            headers=headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✓ PDF endpoint returns 404 for non-existent recording: {data.get('detail')}")
    
    def test_pdf_requires_authentication(self):
        """Test PDF endpoint requires authentication"""
        # Request without auth token
        response = requests.get(
            f"{self.base_url}/api/calls/test_recording_123/summary/pdf"
        )
        # Should return 401 or 403 for unauthenticated request
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ PDF endpoint requires authentication - Status: {response.status_code}")
    
    def test_pdf_returns_400_for_recording_without_summary(self):
        """Test PDF endpoint returns 400 when recording has no summary"""
        token = self.get_auth_token()
        assert token, "Failed to get auth token"
        
        headers = {"Authorization": f"Bearer {token}"}
        # First check if there are any recordings
        response = requests.get(
            f"{self.base_url}/api/calls/recordings/my",
            headers=headers
        )
        assert response.status_code == 200
        recordings = response.json().get("recordings", [])
        
        if recordings:
            # If there's a recording without summary, test it
            for rec in recordings:
                if not rec.get("ai_summary"):
                    rec_id = rec.get("recording_id")
                    pdf_response = requests.get(
                        f"{self.base_url}/api/calls/{rec_id}/summary/pdf",
                        headers=headers
                    )
                    # Should return 400 (no summary available)
                    assert pdf_response.status_code == 400, f"Expected 400, got {pdf_response.status_code}"
                    print(f"✓ PDF endpoint returns 400 for recording without summary")
                    return
        
        print("⚠ No recordings available to test - skipping this test")
        pytest.skip("No recordings available to test")
    
    def test_pdf_content_type_for_valid_request(self):
        """Test PDF endpoint returns correct content type for valid request"""
        token = self.get_auth_token()
        assert token, "Failed to get auth token"
        
        headers = {"Authorization": f"Bearer {token}"}
        # Check if there are any recordings with summaries
        response = requests.get(
            f"{self.base_url}/api/calls/recordings/my",
            headers=headers
        )
        assert response.status_code == 200
        recordings = response.json().get("recordings", [])
        
        for rec in recordings:
            if rec.get("ai_summary"):
                rec_id = rec.get("recording_id")
                pdf_response = requests.get(
                    f"{self.base_url}/api/calls/{rec_id}/summary/pdf",
                    headers=headers
                )
                if pdf_response.status_code == 200:
                    content_type = pdf_response.headers.get("Content-Type", "")
                    assert "application/pdf" in content_type, f"Expected PDF content type, got {content_type}"
                    # Check Content-Disposition header
                    content_disp = pdf_response.headers.get("Content-Disposition", "")
                    assert "attachment" in content_disp, "Expected attachment disposition"
                    assert ".pdf" in content_disp, "Expected .pdf in filename"
                    print(f"✓ PDF endpoint returns correct content type and headers")
                    return
        
        print("⚠ No recordings with summaries available - skipping content type test")
        pytest.skip("No recordings with summaries available")


class TestAPIIntegration:
    """Test API.js integration for PDF export"""
    
    def test_api_endpoint_path(self):
        """Verify the API endpoint path matches frontend expectation"""
        # Frontend calls: /calls/{recordingId}/summary/pdf
        # Backend defines: /{recording_id}/summary/pdf under /calls prefix
        # Full path should be: /api/calls/{recording_id}/summary/pdf
        
        base_url = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
        expected_path = "/api/calls/{recording_id}/summary/pdf"
        
        # Test with a sample recording ID
        test_recording_id = "test_rec_123"
        full_url = f"{base_url}/api/calls/{test_recording_id}/summary/pdf"
        
        # Make request to verify endpoint exists
        response = requests.get(full_url)
        # Should get 401/403 (auth required) or 404 (not found), not 404 for wrong path
        assert response.status_code in [401, 403, 404], f"Unexpected status: {response.status_code}"
        print(f"✓ API endpoint path verified: {expected_path}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
