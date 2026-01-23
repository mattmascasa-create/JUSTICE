"""
Test Template Integration with PDF and Email Endpoints
Tests: 
- GET /api/calls/{recording_id}/summary/pdf?template_id=xxx (single PDF with template)
- POST /api/calls/batch-summary/pdf with template_id (batch PDF with template)
- POST /api/calls/email-summary with template_id (email with template)
- GET /api/templates/my (templates list for selector)
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Authentication failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}", "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def test_template(auth_headers):
    """Create a test template for PDF/email tests"""
    unique_name = f"TEST_PDFEmail_{uuid.uuid4().hex[:8]}"
    payload = {
        "template_name": unique_name,
        "branding": {
            "firm_name": "Test Law Firm",
            "primary_color": "#1e40af",
            "secondary_color": "#3b82f6",
            "accent_color": "#0ea5e9"
        },
        "sections": {
            "show_overview": True,
            "show_key_points": True,
            "show_action_items": True,
            "show_legal_concerns": True,
            "show_recommendations": True,
            "show_follow_up": True,
            "show_call_info": True,
            "show_timestamps": True
        },
        "header_text": "Test Report Header",
        "footer_text": "Test Report Footer",
        "confidentiality_notice": "Test confidentiality notice"
    }
    response = requests.post(
        f"{BASE_URL}/api/templates/create",
        headers=auth_headers,
        json=payload
    )
    if response.status_code == 200:
        template = response.json()["template"]
        yield template
        # Cleanup
        requests.delete(f"{BASE_URL}/api/templates/{template['template_id']}", headers=auth_headers)
    else:
        pytest.skip(f"Failed to create test template: {response.status_code}")


class TestTemplatesListForSelector:
    """Test GET /api/templates/my for template selector dropdown"""
    
    def test_templates_list_returns_array(self, auth_headers):
        """GET /api/templates/my should return templates array for selector"""
        response = requests.get(f"{BASE_URL}/api/templates/my", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "templates" in data, "Response should contain 'templates' key"
        assert isinstance(data["templates"], list), "templates should be a list"
        print(f"✓ GET /api/templates/my returns templates array (count: {len(data['templates'])})")
    
    def test_templates_list_has_required_fields(self, auth_headers, test_template):
        """Templates should have fields needed for selector (template_id, name, is_default)"""
        response = requests.get(f"{BASE_URL}/api/templates/my", headers=auth_headers)
        assert response.status_code == 200
        templates = response.json()["templates"]
        
        # Find our test template
        test_tmpl = next((t for t in templates if t["template_id"] == test_template["template_id"]), None)
        assert test_tmpl is not None, "Test template should be in list"
        
        # Check required fields for selector
        assert "template_id" in test_tmpl, "Template should have template_id"
        assert "template_name" in test_tmpl, "Template should have template_name"
        assert "is_default" in test_tmpl, "Template should have is_default"
        print(f"✓ Template has required fields for selector: template_id, template_name, is_default")


class TestSinglePDFWithTemplate:
    """Test GET /api/calls/{recording_id}/summary/pdf?template_id=xxx"""
    
    def test_pdf_endpoint_accepts_template_id_param(self, auth_headers, test_template):
        """GET /api/calls/{recording_id}/summary/pdf should accept template_id query param"""
        # Use a fake recording_id - we expect 404 but want to verify param is accepted
        fake_recording_id = "rec_nonexistent123"
        template_id = test_template["template_id"]
        
        response = requests.get(
            f"{BASE_URL}/api/calls/{fake_recording_id}/summary/pdf",
            headers=auth_headers,
            params={"template_id": template_id}
        )
        # Should return 404 (recording not found) not 422 (invalid param)
        assert response.status_code == 404, f"Expected 404 (not found), got {response.status_code}"
        print(f"✓ PDF endpoint accepts template_id param (returns 404 for missing recording)")
    
    def test_pdf_endpoint_accepts_system_default(self, auth_headers):
        """GET /api/calls/{recording_id}/summary/pdf should accept system_default as template_id"""
        fake_recording_id = "rec_nonexistent456"
        
        response = requests.get(
            f"{BASE_URL}/api/calls/{fake_recording_id}/summary/pdf",
            headers=auth_headers,
            params={"template_id": "system_default"}
        )
        # Should return 404 (recording not found) not 422 (invalid param)
        assert response.status_code == 404, f"Expected 404 (not found), got {response.status_code}"
        print(f"✓ PDF endpoint accepts 'system_default' as template_id")
    
    def test_pdf_endpoint_works_without_template_id(self, auth_headers):
        """GET /api/calls/{recording_id}/summary/pdf should work without template_id (uses default)"""
        fake_recording_id = "rec_nonexistent789"
        
        response = requests.get(
            f"{BASE_URL}/api/calls/{fake_recording_id}/summary/pdf",
            headers=auth_headers
        )
        # Should return 404 (recording not found) not 422 (missing param)
        assert response.status_code == 404, f"Expected 404 (not found), got {response.status_code}"
        print(f"✓ PDF endpoint works without template_id (uses default)")


class TestBatchPDFWithTemplate:
    """Test POST /api/calls/batch-summary/pdf with template_id"""
    
    def test_batch_pdf_accepts_template_id_in_body(self, auth_headers, test_template):
        """POST /api/calls/batch-summary/pdf should accept template_id in request body"""
        template_id = test_template["template_id"]
        
        payload = {
            "recording_ids": ["rec_fake1", "rec_fake2"],
            "template_id": template_id
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calls/batch-summary/pdf",
            headers=auth_headers,
            json=payload
        )
        # Should return 400 (no recordings with summaries found) not 422 (invalid body)
        assert response.status_code == 400, f"Expected 400 (no recordings), got {response.status_code}"
        assert "No recordings with summaries found" in response.text or "summaries" in response.text.lower()
        print(f"✓ Batch PDF endpoint accepts template_id in body")
    
    def test_batch_pdf_accepts_system_default(self, auth_headers):
        """POST /api/calls/batch-summary/pdf should accept system_default as template_id"""
        payload = {
            "recording_ids": ["rec_fake3"],
            "template_id": "system_default"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calls/batch-summary/pdf",
            headers=auth_headers,
            json=payload
        )
        # Should return 400 (no recordings) not 422 (invalid body)
        assert response.status_code == 400, f"Expected 400 (no recordings), got {response.status_code}"
        print(f"✓ Batch PDF endpoint accepts 'system_default' as template_id")
    
    def test_batch_pdf_works_without_template_id(self, auth_headers):
        """POST /api/calls/batch-summary/pdf should work without template_id (uses default)"""
        payload = {
            "recording_ids": ["rec_fake4"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calls/batch-summary/pdf",
            headers=auth_headers,
            json=payload
        )
        # Should return 400 (no recordings) not 422 (missing field)
        assert response.status_code == 400, f"Expected 400 (no recordings), got {response.status_code}"
        print(f"✓ Batch PDF endpoint works without template_id (uses default)")
    
    def test_batch_pdf_validates_recording_ids_required(self, auth_headers):
        """POST /api/calls/batch-summary/pdf should require recording_ids"""
        payload = {
            "template_id": "system_default"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calls/batch-summary/pdf",
            headers=auth_headers,
            json=payload
        )
        # Should return 422 (validation error) or 400 (no recording IDs)
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print(f"✓ Batch PDF endpoint validates recording_ids required")


class TestEmailSummaryWithTemplate:
    """Test POST /api/calls/email-summary with template_id"""
    
    def test_email_summary_accepts_template_id(self, auth_headers, test_template):
        """POST /api/calls/email-summary should accept template_id in request body"""
        template_id = test_template["template_id"]
        
        payload = {
            "recording_ids": ["rec_email_fake1"],
            "recipient_emails": ["test@example.com"],
            "template_id": template_id
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calls/email-summary",
            headers=auth_headers,
            json=payload
        )
        # Should return 400 (no recordings with summaries) not 422 (invalid body)
        assert response.status_code == 400, f"Expected 400 (no recordings), got {response.status_code}"
        assert "No recordings with summaries found" in response.text or "summaries" in response.text.lower()
        print(f"✓ Email summary endpoint accepts template_id in body")
    
    def test_email_summary_accepts_system_default(self, auth_headers):
        """POST /api/calls/email-summary should accept system_default as template_id"""
        payload = {
            "recording_ids": ["rec_email_fake2"],
            "recipient_emails": ["test@example.com"],
            "template_id": "system_default"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calls/email-summary",
            headers=auth_headers,
            json=payload
        )
        # Should return 400 (no recordings) not 422 (invalid body)
        assert response.status_code == 400, f"Expected 400 (no recordings), got {response.status_code}"
        print(f"✓ Email summary endpoint accepts 'system_default' as template_id")
    
    def test_email_summary_works_without_template_id(self, auth_headers):
        """POST /api/calls/email-summary should work without template_id (uses default)"""
        payload = {
            "recording_ids": ["rec_email_fake3"],
            "recipient_emails": ["test@example.com"]
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calls/email-summary",
            headers=auth_headers,
            json=payload
        )
        # Should return 400 (no recordings) not 422 (missing field)
        assert response.status_code == 400, f"Expected 400 (no recordings), got {response.status_code}"
        print(f"✓ Email summary endpoint works without template_id (uses default)")
    
    def test_email_summary_validates_recipients_required(self, auth_headers):
        """POST /api/calls/email-summary should require recipient_emails"""
        payload = {
            "recording_ids": ["rec_email_fake4"],
            "template_id": "system_default"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calls/email-summary",
            headers=auth_headers,
            json=payload
        )
        # Should return 422 (validation error) or 400 (no recipients)
        assert response.status_code in [400, 422], f"Expected 400/422, got {response.status_code}"
        print(f"✓ Email summary endpoint validates recipient_emails required")
    
    def test_email_summary_validates_email_format(self, auth_headers):
        """POST /api/calls/email-summary should validate email format"""
        payload = {
            "recording_ids": ["rec_email_fake5"],
            "recipient_emails": ["not-an-email"],
            "template_id": "system_default"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calls/email-summary",
            headers=auth_headers,
            json=payload
        )
        # Should return 422 (validation error for invalid email)
        assert response.status_code == 422, f"Expected 422 (invalid email), got {response.status_code}"
        print(f"✓ Email summary endpoint validates email format")
    
    def test_email_summary_accepts_optional_fields(self, auth_headers, test_template):
        """POST /api/calls/email-summary should accept all optional fields"""
        template_id = test_template["template_id"]
        
        payload = {
            "recording_ids": ["rec_email_fake6"],
            "recipient_emails": ["test@example.com"],
            "cc_emails": ["cc@example.com"],
            "custom_message": "Test custom message",
            "recipient_name": "Test Recipient",
            "template_id": template_id
        }
        
        response = requests.post(
            f"{BASE_URL}/api/calls/email-summary",
            headers=auth_headers,
            json=payload
        )
        # Should return 400 (no recordings) not 422 (invalid body)
        assert response.status_code == 400, f"Expected 400 (no recordings), got {response.status_code}"
        print(f"✓ Email summary endpoint accepts all optional fields (cc, message, name, template)")


class TestTemplateDefaultFallback:
    """Test that endpoints fall back to user's default template when no template_id provided"""
    
    def test_set_default_template(self, auth_headers, test_template):
        """Set test template as default for fallback tests"""
        template_id = test_template["template_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/templates/{template_id}/set-default",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.json().get("is_default") == True
        print(f"✓ Set template {template_id} as default")
    
    def test_get_default_returns_user_template(self, auth_headers, test_template):
        """GET /api/templates/default should return user's default template"""
        response = requests.get(f"{BASE_URL}/api/templates/default", headers=auth_headers)
        assert response.status_code == 200
        
        default_template = response.json()["template"]
        # Should be our test template (set as default above)
        assert default_template["template_id"] == test_template["template_id"]
        print(f"✓ Default template returns user's default: {default_template['template_id']}")


class TestAPIIntegrationWithFrontend:
    """Test that API matches frontend api.js expectations"""
    
    def test_download_summary_pdf_signature(self, auth_headers):
        """Verify downloadSummaryPDF API signature matches frontend"""
        # Frontend: downloadSummaryPDF: (recordingId, templateId = null) => api.get(`/calls/${recordingId}/summary/pdf`, { params: templateId ? { template_id: templateId } : {} })
        
        # Test with template_id
        response = requests.get(
            f"{BASE_URL}/api/calls/rec_test/summary/pdf",
            headers=auth_headers,
            params={"template_id": "tmpl_test"}
        )
        assert response.status_code == 404  # Recording not found, but param accepted
        
        # Test without template_id
        response = requests.get(
            f"{BASE_URL}/api/calls/rec_test/summary/pdf",
            headers=auth_headers
        )
        assert response.status_code == 404  # Recording not found, but works without param
        print(f"✓ downloadSummaryPDF API signature matches frontend")
    
    def test_download_batch_summary_pdf_signature(self, auth_headers):
        """Verify downloadBatchSummaryPDF API signature matches frontend"""
        # Frontend: downloadBatchSummaryPDF: (recordingIds, templateId = null) => api.post('/calls/batch-summary/pdf', { recording_ids: recordingIds, template_id: templateId })
        
        # Test with template_id
        response = requests.post(
            f"{BASE_URL}/api/calls/batch-summary/pdf",
            headers=auth_headers,
            json={"recording_ids": ["rec_test"], "template_id": "tmpl_test"}
        )
        assert response.status_code == 400  # No recordings, but body accepted
        
        # Test without template_id (null in frontend becomes missing key)
        response = requests.post(
            f"{BASE_URL}/api/calls/batch-summary/pdf",
            headers=auth_headers,
            json={"recording_ids": ["rec_test"]}
        )
        assert response.status_code == 400  # No recordings, but works without template_id
        print(f"✓ downloadBatchSummaryPDF API signature matches frontend")
    
    def test_email_summary_signature(self, auth_headers):
        """Verify emailSummary API signature matches frontend"""
        # Frontend: emailSummary: (recordingIds, recipientEmails, ccEmails = null, customMessage = null, recipientName = null, templateId = null) => 
        #   api.post('/calls/email-summary', { recording_ids, recipient_emails, cc_emails, custom_message, recipient_name, template_id })
        
        # Test with all fields
        response = requests.post(
            f"{BASE_URL}/api/calls/email-summary",
            headers=auth_headers,
            json={
                "recording_ids": ["rec_test"],
                "recipient_emails": ["test@example.com"],
                "cc_emails": ["cc@example.com"],
                "custom_message": "Test message",
                "recipient_name": "Test Name",
                "template_id": "tmpl_test"
            }
        )
        assert response.status_code == 400  # No recordings, but body accepted
        
        # Test with minimal fields
        response = requests.post(
            f"{BASE_URL}/api/calls/email-summary",
            headers=auth_headers,
            json={
                "recording_ids": ["rec_test"],
                "recipient_emails": ["test@example.com"]
            }
        )
        assert response.status_code == 400  # No recordings, but works with minimal fields
        print(f"✓ emailSummary API signature matches frontend")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
