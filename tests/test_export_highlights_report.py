"""
Test Export Highlights Report Feature (v5.7.0)
Tests PDF generation for evidence highlights - both formal and simple styles.
Endpoints tested:
- GET /api/encounters/shared/{id}/highlights/export?token=xxx&style=formal
- GET /api/encounters/shared/{id}/highlights/export?token=xxx&style=simple
- GET /api/health (version and feature flag)
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "modtest2@test.com"
TEST_PASSWORD = "Test123!"
TEST_ENCOUNTER_ID = "enc_e6692f1e966b"
TEST_SHARE_TOKEN = "adbe232a15954e11"


class TestHealthEndpoint:
    """Health endpoint tests for v5.7.0 feature flag"""
    
    def test_health_returns_version_5_7_0(self):
        """Health endpoint should return version 5.7.0"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("version") == "5.7.0", f"Expected version 5.7.0, got {data.get('version')}"
    
    def test_health_shows_export_highlights_report_feature(self):
        """Health endpoint should show export_highlights_report feature enabled"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        features = data.get("features", {})
        assert features.get("export_highlights_report") == True, f"export_highlights_report feature not enabled: {features}"


class TestExportSharedHighlightsReport:
    """Tests for shared highlights export endpoint"""
    
    def test_export_formal_style_returns_pdf(self):
        """Export with formal style should return valid PDF"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights/export",
            params={"token": TEST_SHARE_TOKEN, "style": "formal"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("content-type") == "application/pdf"
        assert response.content.startswith(b"%PDF"), "Response should start with PDF header"
        assert len(response.content) > 1000, f"PDF too small: {len(response.content)} bytes"
    
    def test_export_simple_style_returns_pdf(self):
        """Export with simple style should return valid PDF"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights/export",
            params={"token": TEST_SHARE_TOKEN, "style": "simple"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("content-type") == "application/pdf"
        assert response.content.startswith(b"%PDF"), "Response should start with PDF header"
    
    def test_export_formal_has_more_pages_than_simple(self):
        """Formal style should have more pages (includes legal disclaimer)"""
        formal_response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights/export",
            params={"token": TEST_SHARE_TOKEN, "style": "formal"}
        )
        simple_response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights/export",
            params={"token": TEST_SHARE_TOKEN, "style": "simple"}
        )
        # Formal should be larger due to legal disclaimer page
        assert len(formal_response.content) > len(simple_response.content), \
            f"Formal ({len(formal_response.content)}) should be larger than simple ({len(simple_response.content)})"
    
    def test_export_has_content_disposition_header(self):
        """Export should have Content-Disposition header for download"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights/export",
            params={"token": TEST_SHARE_TOKEN, "style": "formal"}
        )
        assert response.status_code == 200
        content_disposition = response.headers.get("content-disposition", "")
        assert "attachment" in content_disposition, f"Missing attachment in Content-Disposition: {content_disposition}"
        assert "JUSTICE_Report" in content_disposition, f"Missing JUSTICE_Report in filename: {content_disposition}"
        assert ".pdf" in content_disposition, f"Missing .pdf extension: {content_disposition}"
    
    def test_export_with_invalid_token_returns_403(self):
        """Export with invalid token should return 403"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights/export",
            params={"token": "invalid_token_12345", "style": "formal"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_export_without_token_returns_422(self):
        """Export without token should return 422 validation error"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights/export",
            params={"style": "formal"}
        )
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
    
    def test_export_nonexistent_encounter_returns_404(self):
        """Export for non-existent encounter should return 404"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/enc_nonexistent123/highlights/export",
            params={"token": TEST_SHARE_TOKEN, "style": "formal"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_export_default_style_is_formal(self):
        """Export without style parameter should default to formal"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights/export",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"
        # Check filename contains 'formal'
        content_disposition = response.headers.get("content-disposition", "")
        assert "formal" in content_disposition.lower(), f"Default should be formal: {content_disposition}"
    
    def test_export_invalid_style_defaults_to_formal(self):
        """Export with invalid style should default to formal"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights/export",
            params={"token": TEST_SHARE_TOKEN, "style": "invalid_style"}
        )
        assert response.status_code == 200
        content_disposition = response.headers.get("content-disposition", "")
        assert "formal" in content_disposition.lower(), f"Invalid style should default to formal: {content_disposition}"


class TestExportAuthenticatedHighlightsReport:
    """Tests for authenticated highlights export endpoint"""
    
    @pytest.fixture
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            # API returns access_token, not token
            return response.json().get("access_token")
        pytest.skip("Authentication failed - skipping authenticated tests")
    
    def test_authenticated_export_formal_returns_pdf(self, auth_token):
        """Authenticated export with formal style should return PDF"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/{TEST_ENCOUNTER_ID}/highlights/export",
            params={"style": "formal"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("content-type") == "application/pdf"
        assert response.content.startswith(b"%PDF")
    
    def test_authenticated_export_simple_returns_pdf(self, auth_token):
        """Authenticated export with simple style should return PDF"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/{TEST_ENCOUNTER_ID}/highlights/export",
            params={"style": "simple"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        assert response.headers.get("content-type") == "application/pdf"
    
    def test_authenticated_export_without_auth_returns_403(self):
        """Export without authentication should return 403"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/{TEST_ENCOUNTER_ID}/highlights/export",
            params={"style": "formal"}
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"


class TestPDFContent:
    """Tests for PDF content structure"""
    
    def test_pdf_contains_encounter_id(self):
        """PDF should contain encounter ID"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights/export",
            params={"token": TEST_SHARE_TOKEN, "style": "formal"}
        )
        assert response.status_code == 200
        # PDF content is binary, but encounter ID should be in there
        # We can check the raw bytes for the encounter ID string
        assert TEST_ENCOUNTER_ID.encode() in response.content or \
               TEST_ENCOUNTER_ID.replace("_", " ").encode() in response.content, \
               "PDF should contain encounter ID"
    
    def test_pdf_is_valid_pdf_format(self):
        """PDF should be valid PDF 1.3+ format"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights/export",
            params={"token": TEST_SHARE_TOKEN, "style": "formal"}
        )
        assert response.status_code == 200
        content = response.content
        # Check PDF header
        assert content.startswith(b"%PDF-1."), f"Invalid PDF header: {content[:20]}"
        # Check PDF has EOF marker
        assert b"%%EOF" in content[-100:], "PDF should end with %%EOF marker"


class TestAPIURLConstruction:
    """Tests for frontend API URL construction"""
    
    def test_shared_export_url_format(self):
        """Verify the shared export URL format works"""
        # This tests the URL format used by frontend: /api/encounters/shared/{id}/highlights/export?token=xxx&style=formal
        url = f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights/export"
        response = requests.get(url, params={"token": TEST_SHARE_TOKEN, "style": "formal"})
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/pdf"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
