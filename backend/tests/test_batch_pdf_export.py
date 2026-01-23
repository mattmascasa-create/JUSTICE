"""
Test Batch PDF Export Feature
Tests for POST /api/calls/batch-summary/pdf endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://justice-rights.preview.emergentagent.com')

class TestBatchPDFExport:
    """Tests for batch PDF export endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get auth token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        
        if login_response.status_code == 200:
            data = login_response.json()
            token = data.get("access_token") or data.get("token")
            if token:
                self.session.headers.update({"Authorization": f"Bearer {token}"})
                self.authenticated = True
            else:
                self.authenticated = False
        else:
            self.authenticated = False
            
        yield
        self.session.close()
    
    def test_health_endpoint(self):
        """Test health endpoint is working"""
        response = self.session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data or "status" in data
        print(f"Health check passed: {data}")
    
    def test_login_success(self):
        """Test login with test credentials"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data or "token" in data
        print(f"Login successful, token received")
    
    def test_batch_pdf_endpoint_exists(self):
        """Test that batch PDF endpoint exists (not 404 or 405)"""
        if not self.authenticated:
            pytest.skip("Authentication failed")
        
        # Send with empty list to test endpoint exists
        response = self.session.post(
            f"{BASE_URL}/api/calls/batch-summary/pdf",
            json={"recording_ids": []}
        )
        
        # Should return 400 for empty list, not 404 or 405
        assert response.status_code != 404, "Endpoint not found (404)"
        assert response.status_code != 405, "Method not allowed (405)"
        print(f"Endpoint exists, returned status: {response.status_code}")
    
    def test_batch_pdf_empty_list_returns_400(self):
        """Test that empty recording_ids list returns 400"""
        if not self.authenticated:
            pytest.skip("Authentication failed")
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/batch-summary/pdf",
            json={"recording_ids": []}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "no recording" in data["detail"].lower() or "empty" in data["detail"].lower() or "provided" in data["detail"].lower()
        print(f"Empty list correctly returns 400: {data['detail']}")
    
    def test_batch_pdf_invalid_recording_ids_returns_400(self):
        """Test that invalid/non-existent recording IDs return 400"""
        if not self.authenticated:
            pytest.skip("Authentication failed")
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/batch-summary/pdf",
            json={"recording_ids": ["invalid_id_1", "invalid_id_2"]}
        )
        
        # Should return 400 because no valid recordings with summaries found
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        print(f"Invalid IDs correctly returns 400: {data['detail']}")
    
    def test_batch_pdf_requires_authentication(self):
        """Test that batch PDF endpoint requires authentication"""
        # Create new session without auth
        unauthenticated_session = requests.Session()
        unauthenticated_session.headers.update({"Content-Type": "application/json"})
        
        response = unauthenticated_session.post(
            f"{BASE_URL}/api/calls/batch-summary/pdf",
            json={"recording_ids": ["test_id"]}
        )
        
        # Should return 401 or 403 for unauthenticated request
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"Authentication required, returned: {response.status_code}")
        unauthenticated_session.close()
    
    def test_batch_pdf_max_limit(self):
        """Test that batch PDF enforces maximum 20 recordings limit"""
        if not self.authenticated:
            pytest.skip("Authentication failed")
        
        # Create list of 21 fake IDs
        recording_ids = [f"fake_id_{i}" for i in range(21)]
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/batch-summary/pdf",
            json={"recording_ids": recording_ids}
        )
        
        # Should return 400 for exceeding limit
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "20" in data["detail"] or "maximum" in data["detail"].lower()
        print(f"Max limit enforced: {data['detail']}")
    
    def test_batch_pdf_missing_recording_ids_field(self):
        """Test that missing recording_ids field returns error"""
        if not self.authenticated:
            pytest.skip("Authentication failed")
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/batch-summary/pdf",
            json={}
        )
        
        # Should return 422 (validation error) or 400
        assert response.status_code in [400, 422]
        print(f"Missing field correctly returns error: {response.status_code}")


class TestFrontendAPIIntegration:
    """Tests to verify frontend API integration exists"""
    
    def test_api_js_has_batch_export_method(self):
        """Verify api.js contains downloadBatchSummaryPDF method"""
        api_file_path = "/app/frontend/src/lib/api.js"
        
        with open(api_file_path, 'r') as f:
            content = f.read()
        
        assert "downloadBatchSummaryPDF" in content, "downloadBatchSummaryPDF method not found in api.js"
        assert "batch-summary/pdf" in content, "batch-summary/pdf endpoint not found in api.js"
        print("API integration verified: downloadBatchSummaryPDF method exists")
    
    def test_recordings_page_has_batch_export_button(self):
        """Verify RecordingsPage.jsx has batch export button"""
        page_file_path = "/app/frontend/src/pages/RecordingsPage.jsx"
        
        with open(page_file_path, 'r') as f:
            content = f.read()
        
        # Check for batch export button
        assert "Batch Export" in content, "Batch Export button text not found"
        assert "isSelectionMode" in content, "Selection mode state not found"
        assert "selectedIds" in content, "Selected IDs state not found"
        assert "handleBatchExport" in content, "handleBatchExport handler not found"
        print("Frontend batch export UI components verified")
    
    def test_recordings_page_has_selection_checkboxes(self):
        """Verify RecordingsPage.jsx has selection checkboxes"""
        page_file_path = "/app/frontend/src/pages/RecordingsPage.jsx"
        
        with open(page_file_path, 'r') as f:
            content = f.read()
        
        assert "Checkbox" in content, "Checkbox component not imported"
        assert "toggleSelection" in content, "toggleSelection handler not found"
        assert "select-recording" in content, "Selection checkbox data-testid not found"
        print("Selection checkboxes verified in RecordingsPage")
    
    def test_recordings_page_has_select_all_button(self):
        """Verify RecordingsPage.jsx has Select All button"""
        page_file_path = "/app/frontend/src/pages/RecordingsPage.jsx"
        
        with open(page_file_path, 'r') as f:
            content = f.read()
        
        assert "Select All" in content, "Select All button text not found"
        assert "selectAll" in content, "selectAll handler not found"
        print("Select All button verified")
    
    def test_recordings_page_has_cancel_button(self):
        """Verify RecordingsPage.jsx has Cancel button in selection mode"""
        page_file_path = "/app/frontend/src/pages/RecordingsPage.jsx"
        
        with open(page_file_path, 'r') as f:
            content = f.read()
        
        assert "clearSelection" in content, "clearSelection handler not found"
        assert "Cancel" in content, "Cancel button text not found"
        print("Cancel button verified")
    
    def test_recordings_page_has_export_pdf_button(self):
        """Verify RecordingsPage.jsx has Export PDF button"""
        page_file_path = "/app/frontend/src/pages/RecordingsPage.jsx"
        
        with open(page_file_path, 'r') as f:
            content = f.read()
        
        assert "Export PDF" in content, "Export PDF button text not found"
        assert "batch-export-btn" in content, "batch-export-btn data-testid not found"
        print("Export PDF button verified")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
