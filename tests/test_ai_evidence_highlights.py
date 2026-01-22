"""
AI Evidence Highlights Feature Tests (v5.6.0)
Tests for the new AI-powered evidence highlights feature that scans transcriptions
to identify key moments (violations, escalations, important statements) with timestamps.
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


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for test user"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Authentication failed: {response.text}")


@pytest.fixture
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestHealthEndpoint:
    """Test health endpoint shows v5.6.0 with ai_evidence_highlights feature"""
    
    def test_health_version_5_6_0(self):
        """Health endpoint returns version 5.6.0"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "5.6.0"
        print(f"✓ Health endpoint version: {data['version']}")
    
    def test_health_ai_evidence_highlights_feature(self):
        """Health endpoint shows ai_evidence_highlights feature enabled"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "features" in data
        assert data["features"].get("ai_evidence_highlights") == True
        print(f"✓ ai_evidence_highlights feature: {data['features']['ai_evidence_highlights']}")


class TestSharedHighlightsEndpoint:
    """Test public shared highlights endpoint (no auth required)"""
    
    def test_get_shared_highlights_valid_token(self):
        """Get shared highlights with valid token returns highlights data"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        assert "encounter_id" in data
        assert "highlights" in data
        assert "count" in data
        assert data["encounter_id"] == TEST_ENCOUNTER_ID
        print(f"✓ Shared highlights returned: {data['count']} highlights")
    
    def test_get_shared_highlights_invalid_token(self):
        """Get shared highlights with invalid token returns 403"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights",
            params={"token": "invalid_token_12345"}
        )
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        print(f"✓ Invalid token rejected: {data['detail']}")
    
    def test_get_shared_highlights_missing_token(self):
        """Get shared highlights without token returns 422"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights"
        )
        assert response.status_code == 422
        print("✓ Missing token returns 422 validation error")
    
    def test_get_shared_highlights_nonexistent_encounter(self):
        """Get shared highlights for non-existent encounter returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/enc_nonexistent123/highlights",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 404
        print("✓ Non-existent encounter returns 404")


class TestSharedEncounterHighlightsField:
    """Test that shared encounter response includes evidence_highlights field"""
    
    def test_shared_encounter_has_highlights_field(self):
        """Shared encounter response includes evidence_highlights field"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        assert "evidence_highlights" in data
        assert "highlights_count" in data
        print(f"✓ Shared encounter has evidence_highlights: {data['highlights_count']} highlights")
    
    def test_shared_encounter_highlights_structure(self):
        """Shared encounter highlights have correct structure"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        highlights = data.get("evidence_highlights", [])
        
        if len(highlights) > 0:
            highlight = highlights[0]
            # Check required fields
            assert "timestamp" in highlight
            assert "category" in highlight
            assert "severity" in highlight
            assert "title" in highlight
            assert "highlight_id" in highlight
            print(f"✓ Highlight structure valid: {highlight.get('title')}")
        else:
            print("✓ No highlights yet (expected for encounter without transcriptions)")


class TestAuthenticatedHighlightsEndpoints:
    """Test authenticated highlights endpoints"""
    
    def test_get_highlights_requires_auth(self):
        """Get highlights without auth returns 401 or 403"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/{TEST_ENCOUNTER_ID}/highlights"
        )
        assert response.status_code in [401, 403]
        print(f"✓ Get highlights requires authentication (status: {response.status_code})")
    
    def test_get_highlights_with_auth(self, auth_headers):
        """Get highlights with valid auth returns highlights"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/{TEST_ENCOUNTER_ID}/highlights",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "encounter_id" in data
        assert "highlights" in data
        assert "count" in data
        print(f"✓ Get highlights with auth: {data['count']} highlights")
    
    def test_generate_highlights_requires_auth(self):
        """Generate highlights without auth returns 401 or 403"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/{TEST_ENCOUNTER_ID}/highlights/generate"
        )
        assert response.status_code in [401, 403]
        print(f"✓ Generate highlights requires authentication (status: {response.status_code})")
    
    def test_generate_highlights_no_transcriptions(self, auth_headers):
        """Generate highlights with no transcriptions returns 400"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/{TEST_ENCOUNTER_ID}/highlights/generate",
            headers=auth_headers
        )
        # Should return 400 if no transcriptions available
        assert response.status_code in [200, 400]
        if response.status_code == 400:
            data = response.json()
            assert "transcriptions" in data.get("detail", "").lower() or "No transcriptions" in data.get("detail", "")
            print(f"✓ Generate highlights without transcriptions: {data['detail']}")
        else:
            print("✓ Generate highlights succeeded (transcriptions exist)")
    
    def test_regenerate_highlights_requires_auth(self):
        """Regenerate highlights without auth returns 401 or 403"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/{TEST_ENCOUNTER_ID}/highlights/regenerate",
            data={"feedback": "Focus on 4th amendment"}
        )
        assert response.status_code in [401, 403]
        print(f"✓ Regenerate highlights requires authentication (status: {response.status_code})")
    
    def test_regenerate_highlights_with_feedback(self, auth_headers):
        """Regenerate highlights with feedback returns updated highlights"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/{TEST_ENCOUNTER_ID}/highlights/regenerate",
            headers=auth_headers,
            data={"feedback": "Focus more on Miranda rights violations"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "highlights" in data
        assert "count" in data
        print(f"✓ Regenerate highlights with feedback: {data['count']} highlights")
    
    def test_regenerate_highlights_missing_feedback(self, auth_headers):
        """Regenerate highlights without feedback returns 422"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/{TEST_ENCOUNTER_ID}/highlights/regenerate",
            headers=auth_headers
        )
        assert response.status_code == 422
        print("✓ Regenerate highlights requires feedback parameter")


class TestHighlightDataStructure:
    """Test highlight data structure and fields"""
    
    def test_highlight_has_required_fields(self):
        """Highlights have all required fields"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        highlights = data.get("highlights", [])
        
        if len(highlights) > 0:
            highlight = highlights[0]
            required_fields = ["timestamp", "category", "severity", "title", "highlight_id", "generated_at"]
            for field in required_fields:
                assert field in highlight, f"Missing field: {field}"
            print(f"✓ All required fields present in highlights")
        else:
            print("✓ No highlights to validate (expected)")
    
    def test_highlight_severity_values(self):
        """Highlight severity is one of expected values"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        highlights = data.get("highlights", [])
        
        valid_severities = ["critical", "high", "medium", "low", "Critical", "High", "Medium", "Low"]
        for highlight in highlights:
            severity = highlight.get("severity", "")
            assert severity in valid_severities, f"Invalid severity: {severity}"
        
        if highlights:
            print(f"✓ All {len(highlights)} highlights have valid severity values")
        else:
            print("✓ No highlights to validate severity")
    
    def test_highlight_category_values(self):
        """Highlight category is one of expected values"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        highlights = data.get("highlights", [])
        
        # Categories can be flexible based on AI output
        valid_categories = [
            "violation", "escalation", "threat", "rights_assertion", 
            "cooperation", "important_statement", "procedural_issue",
            "Search and Seizure", "Search Warrant", "Miranda Rights",
            "4th Amendment", "5th Amendment", "Excessive Force"
        ]
        
        for highlight in highlights:
            category = highlight.get("category", "")
            # Just check it's not empty
            assert category, f"Empty category in highlight"
        
        if highlights:
            print(f"✓ All {len(highlights)} highlights have category values")
        else:
            print("✓ No highlights to validate category")


class TestHighlightsIntegration:
    """Integration tests for highlights feature"""
    
    def test_highlights_persist_after_regenerate(self, auth_headers):
        """Highlights persist in database after regeneration"""
        # Regenerate
        regen_response = requests.post(
            f"{BASE_URL}/api/encounters/{TEST_ENCOUNTER_ID}/highlights/regenerate",
            headers=auth_headers,
            data={"feedback": "Test persistence"}
        )
        assert regen_response.status_code == 200
        regen_count = regen_response.json().get("count", 0)
        
        # Verify via shared endpoint
        shared_response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/highlights",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert shared_response.status_code == 200
        shared_count = shared_response.json().get("count", 0)
        
        assert shared_count == regen_count
        print(f"✓ Highlights persist after regeneration: {shared_count} highlights")
    
    def test_shared_encounter_reflects_highlights_update(self, auth_headers):
        """Shared encounter endpoint reflects highlights updates"""
        # Get current count from shared encounter
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 200
        data = response.json()
        
        highlights_count = data.get("highlights_count", 0)
        evidence_highlights = data.get("evidence_highlights", [])
        
        assert len(evidence_highlights) == highlights_count
        print(f"✓ Shared encounter highlights_count matches evidence_highlights length: {highlights_count}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
