"""
Test Email Summary Feature - POST /api/calls/email-summary endpoint
Tests validation, authentication, and error handling for email delivery of PDF summaries
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestEmailSummaryEndpoint:
    """Tests for POST /api/calls/email-summary endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.auth_token = None
        
    def get_auth_token(self):
        """Get authentication token"""
        if self.auth_token:
            return self.auth_token
            
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        if response.status_code == 200:
            data = response.json()
            # Handle both 'token' and 'access_token' response formats
            self.auth_token = data.get("token") or data.get("access_token")
            return self.auth_token
        return None
    
    def test_health_endpoint(self):
        """Test health endpoint is accessible"""
        response = self.session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data or "status" in data
        print("✓ Health endpoint accessible")
    
    def test_login_success(self):
        """Test user login works"""
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 200
        data = response.json()
        # Handle both 'token' and 'access_token' response formats
        assert "token" in data or "access_token" in data
        print("✓ Login successful")
    
    def test_email_summary_endpoint_exists(self):
        """Test that POST /api/calls/email-summary endpoint exists (not 404 or 405)"""
        token = self.get_auth_token()
        assert token, "Failed to get auth token"
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/email-summary",
            json={
                "recording_ids": ["test_id"],
                "recipient_emails": ["test@test.com"]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should not be 404 (not found) or 405 (method not allowed)
        assert response.status_code not in [404, 405], f"Endpoint not found or method not allowed: {response.status_code}"
        print(f"✓ Email summary endpoint exists (status: {response.status_code})")
    
    def test_email_summary_requires_authentication(self):
        """Test that endpoint requires authentication"""
        response = self.session.post(
            f"{BASE_URL}/api/calls/email-summary",
            json={
                "recording_ids": ["test_id"],
                "recipient_emails": ["test@test.com"]
            }
        )
        # Should return 401 or 403 for unauthenticated requests
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print(f"✓ Endpoint requires authentication (status: {response.status_code})")
    
    def test_email_summary_returns_400_for_empty_recording_ids(self):
        """Test that empty recording_ids returns 400"""
        token = self.get_auth_token()
        assert token, "Failed to get auth token"
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/email-summary",
            json={
                "recording_ids": [],
                "recipient_emails": ["test@test.com"]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✓ Empty recording_ids returns 400: {data.get('detail')}")
    
    def test_email_summary_returns_400_for_empty_recipient_emails(self):
        """Test that empty recipient_emails returns 400"""
        token = self.get_auth_token()
        assert token, "Failed to get auth token"
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/email-summary",
            json={
                "recording_ids": ["test_id"],
                "recipient_emails": []
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        print(f"✓ Empty recipient_emails returns 400: {data.get('detail')}")
    
    def test_email_summary_returns_400_for_invalid_recording_ids(self):
        """Test that invalid/non-existent recording IDs return 400"""
        token = self.get_auth_token()
        assert token, "Failed to get auth token"
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/email-summary",
            json={
                "recording_ids": ["nonexistent_recording_id_12345"],
                "recipient_emails": ["test@test.com"]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should return 400 because no recordings with summaries found
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert "no recordings" in data.get("detail", "").lower() or "not found" in data.get("detail", "").lower()
        print(f"✓ Invalid recording IDs returns 400: {data.get('detail')}")
    
    def test_email_summary_enforces_max_10_recipients(self):
        """Test that maximum 10 recipients limit is enforced"""
        token = self.get_auth_token()
        assert token, "Failed to get auth token"
        
        # Create 11 email addresses
        too_many_emails = [f"test{i}@test.com" for i in range(11)]
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/email-summary",
            json={
                "recording_ids": ["test_id"],
                "recipient_emails": too_many_emails
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert "10" in data.get("detail", "") or "maximum" in data.get("detail", "").lower()
        print(f"✓ Max 10 recipients enforced: {data.get('detail')}")
    
    def test_email_summary_enforces_max_20_recordings(self):
        """Test that maximum 20 recordings limit is enforced"""
        token = self.get_auth_token()
        assert token, "Failed to get auth token"
        
        # Create 21 recording IDs
        too_many_recordings = [f"rec_{i}" for i in range(21)]
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/email-summary",
            json={
                "recording_ids": too_many_recordings,
                "recipient_emails": ["test@test.com"]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "detail" in data
        assert "20" in data.get("detail", "") or "maximum" in data.get("detail", "").lower()
        print(f"✓ Max 20 recordings enforced: {data.get('detail')}")
    
    def test_email_summary_accepts_optional_fields(self):
        """Test that optional fields (cc_emails, custom_message, recipient_name) are accepted"""
        token = self.get_auth_token()
        assert token, "Failed to get auth token"
        
        # This should not fail due to schema validation - it will fail because recording doesn't exist
        response = self.session.post(
            f"{BASE_URL}/api/calls/email-summary",
            json={
                "recording_ids": ["test_id"],
                "recipient_emails": ["test@test.com"],
                "cc_emails": ["cc@test.com"],
                "custom_message": "Test message",
                "recipient_name": "Test Recipient"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should not be 422 (validation error) - should be 400 (no recordings found)
        assert response.status_code != 422, f"Schema validation failed: {response.json()}"
        print(f"✓ Optional fields accepted (status: {response.status_code})")
    
    def test_email_summary_validates_email_format(self):
        """Test that invalid email format is rejected"""
        token = self.get_auth_token()
        assert token, "Failed to get auth token"
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/email-summary",
            json={
                "recording_ids": ["test_id"],
                "recipient_emails": ["not-an-email"]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should return 422 for invalid email format (Pydantic validation)
        assert response.status_code == 422, f"Expected 422 for invalid email, got {response.status_code}"
        print(f"✓ Invalid email format rejected (status: {response.status_code})")


class TestFrontendEmailIntegration:
    """Tests for frontend email integration"""
    
    def test_api_js_has_email_summary_method(self):
        """Test that api.js contains emailSummary method"""
        api_file_path = "/app/frontend/src/lib/api.js"
        with open(api_file_path, 'r') as f:
            content = f.read()
        
        assert "emailSummary" in content, "emailSummary method not found in api.js"
        assert "email-summary" in content, "email-summary endpoint not found in api.js"
        print("✓ api.js contains emailSummary method")
    
    def test_recordings_page_has_email_button_in_selection_mode(self):
        """Test that RecordingsPage.jsx has Email button in selection mode header"""
        recordings_page_path = "/app/frontend/src/pages/RecordingsPage.jsx"
        with open(recordings_page_path, 'r') as f:
            content = f.read()
        
        # Check for email button with data-testid
        assert 'data-testid="email-summary-btn"' in content, "Email button with data-testid not found in selection mode"
        print("✓ RecordingsPage.jsx has Email button in selection mode header")
    
    def test_recordings_page_has_email_button_in_summary_tab(self):
        """Test that RecordingsPage.jsx has Email button in AI Summary tab"""
        recordings_page_path = "/app/frontend/src/pages/RecordingsPage.jsx"
        with open(recordings_page_path, 'r') as f:
            content = f.read()
        
        # Check for email button in summary tab
        assert 'data-testid="email-single-summary-btn"' in content, "Email button in summary tab not found"
        print("✓ RecordingsPage.jsx has Email button in AI Summary tab")
    
    def test_recordings_page_has_email_dialog(self):
        """Test that RecordingsPage.jsx has email dialog with required fields"""
        recordings_page_path = "/app/frontend/src/pages/RecordingsPage.jsx"
        with open(recordings_page_path, 'r') as f:
            content = f.read()
        
        # Check for email dialog
        assert 'data-testid="email-dialog"' in content, "Email dialog not found"
        assert 'data-testid="email-recipients-input"' in content, "Recipients input not found"
        assert 'data-testid="email-cc-input"' in content, "CC input not found"
        assert 'data-testid="email-message-input"' in content, "Message input not found"
        assert 'data-testid="send-email-btn"' in content, "Send email button not found"
        print("✓ RecordingsPage.jsx has email dialog with all required fields")
    
    def test_recordings_page_has_email_state_variables(self):
        """Test that RecordingsPage.jsx has email-related state variables"""
        recordings_page_path = "/app/frontend/src/pages/RecordingsPage.jsx"
        with open(recordings_page_path, 'r') as f:
            content = f.read()
        
        # Check for email state variables
        assert "showEmailDialog" in content, "showEmailDialog state not found"
        assert "emailRecipients" in content, "emailRecipients state not found"
        assert "emailCc" in content, "emailCc state not found"
        assert "emailMessage" in content, "emailMessage state not found"
        assert "sendingEmail" in content, "sendingEmail state not found"
        print("✓ RecordingsPage.jsx has all email-related state variables")
    
    def test_recordings_page_has_email_handlers(self):
        """Test that RecordingsPage.jsx has email handler functions"""
        recordings_page_path = "/app/frontend/src/pages/RecordingsPage.jsx"
        with open(recordings_page_path, 'r') as f:
            content = f.read()
        
        # Check for email handler functions
        assert "openEmailDialog" in content, "openEmailDialog function not found"
        assert "closeEmailDialog" in content, "closeEmailDialog function not found"
        assert "handleSendEmail" in content, "handleSendEmail function not found"
        print("✓ RecordingsPage.jsx has all email handler functions")


class TestEmailServiceModule:
    """Tests for email service module"""
    
    def test_email_service_exists(self):
        """Test that email_service.py exists"""
        import os
        service_path = "/app/backend/app/services/email_service.py"
        assert os.path.exists(service_path), "email_service.py not found"
        print("✓ email_service.py exists")
    
    def test_email_service_has_required_functions(self):
        """Test that email_service.py has required functions"""
        service_path = "/app/backend/app/services/email_service.py"
        with open(service_path, 'r') as f:
            content = f.read()
        
        assert "send_pdf_email" in content, "send_pdf_email function not found"
        assert "generate_summary_email_html" in content, "generate_summary_email_html function not found"
        assert "EmailDeliveryError" in content, "EmailDeliveryError class not found"
        print("✓ email_service.py has all required functions")
    
    def test_email_service_uses_sendgrid(self):
        """Test that email_service.py uses SendGrid"""
        service_path = "/app/backend/app/services/email_service.py"
        with open(service_path, 'r') as f:
            content = f.read()
        
        assert "SendGridAPIClient" in content, "SendGrid client not found"
        assert "SENDGRID_API_KEY" in content, "SENDGRID_API_KEY reference not found"
        print("✓ email_service.py uses SendGrid")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
