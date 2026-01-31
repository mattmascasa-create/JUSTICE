"""
Test Suite for Evidence Chain of Custody Portal
Tests the secure public-facing portal for attorneys and courts to view evidence with complete audit trail.
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rights-shield-2.preview.emergentagent.com').rstrip('/')


class TestCustodyPortalAuthenticated:
    """Tests for authenticated custody portal endpoints (token creation, management)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login and get auth token"""
        # Login to get auth token
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.auth_token = login_response.json()["access_token"]
        self.user_id = login_response.json()["user"]["user_id"]
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        # Get or create evidence for testing
        self.evidence_id = None
        self.encounter_id = None
        self._setup_test_evidence()
    
    def _setup_test_evidence(self):
        """Get existing evidence or create test evidence"""
        # First try to get existing evidence
        evidence_response = requests.get(
            f"{BASE_URL}/api/evidence",
            headers=self.headers
        )
        if evidence_response.status_code == 200:
            evidence_list = evidence_response.json()
            if evidence_list and len(evidence_list) > 0:
                self.evidence_id = evidence_list[0].get("evidence_id")
                self.encounter_id = evidence_list[0].get("encounter_id") or evidence_list[0].get("case_id")
                return
        
        # If no evidence exists, try to get encounters
        encounters_response = requests.get(
            f"{BASE_URL}/api/encounters",
            headers=self.headers
        )
        if encounters_response.status_code == 200:
            encounters = encounters_response.json()
            if encounters and len(encounters) > 0:
                self.encounter_id = encounters[0].get("encounter_id")
        
        # Generate test IDs if nothing exists
        if not self.evidence_id:
            self.evidence_id = f"TEST_evidence_{uuid.uuid4().hex[:8]}"
        if not self.encounter_id:
            self.encounter_id = f"TEST_encounter_{uuid.uuid4().hex[:8]}"
    
    def test_create_access_requires_auth(self):
        """POST /api/custody-portal/create-access requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/custody-portal/create-access",
            json={
                "evidence_id": "test_evidence",
                "encounter_id": "test_encounter",
                "recipient_email": "attorney@lawfirm.com",
                "recipient_name": "John Attorney",
                "recipient_role": "attorney"
            }
        )
        # Should return 401 or 403 without auth
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ POST /api/custody-portal/create-access requires authentication")
    
    def test_create_access_token_success(self):
        """POST /api/custody-portal/create-access creates access token with portal_url"""
        response = requests.post(
            f"{BASE_URL}/api/custody-portal/create-access",
            headers=self.headers,
            json={
                "evidence_id": self.evidence_id,
                "encounter_id": self.encounter_id,
                "recipient_email": "test_attorney@lawfirm.com",
                "recipient_name": "Test Attorney",
                "recipient_role": "attorney",
                "access_level": "view",
                "expires_hours": 72,
                "notes": "Test access for custody portal testing"
            }
        )
        
        # May return 404 if evidence doesn't exist, which is expected behavior
        if response.status_code == 404:
            print(f"✓ POST /api/custody-portal/create-access returns 404 for non-existent evidence (expected)")
            pytest.skip("No evidence available for testing - evidence not found")
            return
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True, "Response should have success=True"
        assert "access_token" in data, "Response should contain access_token"
        assert "portal_url" in data, "Response should contain portal_url"
        assert "expires_at" in data, "Response should contain expires_at"
        assert "recipient" in data, "Response should contain recipient info"
        
        # Verify portal URL format
        assert "custody-portal" in data["portal_url"], "Portal URL should contain custody-portal path"
        assert "token=" in data["portal_url"], "Portal URL should contain token parameter"
        
        # Store for later tests
        self.access_token = data["access_token"]
        print(f"✓ POST /api/custody-portal/create-access creates access token with portal_url")
        print(f"  - Access token: {self.access_token[:20]}...")
        print(f"  - Portal URL: {data['portal_url'][:60]}...")
    
    def test_create_access_with_different_roles(self):
        """POST /api/custody-portal/create-access supports different recipient roles"""
        roles = ["attorney", "court", "expert_witness", "insurance"]
        
        for role in roles:
            response = requests.post(
                f"{BASE_URL}/api/custody-portal/create-access",
                headers=self.headers,
                json={
                    "evidence_id": self.evidence_id,
                    "encounter_id": self.encounter_id,
                    "recipient_email": f"test_{role}@example.com",
                    "recipient_name": f"Test {role.title()}",
                    "recipient_role": role,
                    "access_level": "view"
                }
            )
            
            if response.status_code == 404:
                pytest.skip("No evidence available for testing")
                return
            
            assert response.status_code == 200, f"Failed for role {role}: {response.text}"
        
        print(f"✓ POST /api/custody-portal/create-access supports roles: {roles}")
    
    def test_create_access_with_different_access_levels(self):
        """POST /api/custody-portal/create-access supports different access levels"""
        access_levels = ["view", "download", "full"]
        
        for level in access_levels:
            response = requests.post(
                f"{BASE_URL}/api/custody-portal/create-access",
                headers=self.headers,
                json={
                    "evidence_id": self.evidence_id,
                    "encounter_id": self.encounter_id,
                    "recipient_email": f"test_{level}@example.com",
                    "recipient_name": f"Test {level.title()} User",
                    "recipient_role": "attorney",
                    "access_level": level
                }
            )
            
            if response.status_code == 404:
                pytest.skip("No evidence available for testing")
                return
            
            assert response.status_code == 200, f"Failed for access level {level}: {response.text}"
        
        print(f"✓ POST /api/custody-portal/create-access supports access levels: {access_levels}")
    
    def test_get_my_tokens(self):
        """GET /api/custody-portal/my-tokens returns user's created tokens"""
        response = requests.get(
            f"{BASE_URL}/api/custody-portal/my-tokens",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True, "Response should have success=True"
        assert "tokens" in data, "Response should contain tokens array"
        assert "count" in data, "Response should contain count"
        assert isinstance(data["tokens"], list), "Tokens should be a list"
        
        print(f"✓ GET /api/custody-portal/my-tokens returns {data['count']} tokens")
    
    def test_get_my_tokens_requires_auth(self):
        """GET /api/custody-portal/my-tokens requires authentication"""
        response = requests.get(f"{BASE_URL}/api/custody-portal/my-tokens")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ GET /api/custody-portal/my-tokens requires authentication")


class TestCustodyPortalPublic:
    """Tests for public custody portal endpoints (no auth required)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup - create an access token for testing public endpoints"""
        # Login to create access token
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        assert login_response.status_code == 200
        self.auth_token = login_response.json()["access_token"]
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        # Get evidence for testing
        self.access_token = None
        self._create_test_access_token()
    
    def _create_test_access_token(self):
        """Create an access token for testing public endpoints"""
        # Get existing evidence
        evidence_response = requests.get(
            f"{BASE_URL}/api/evidence",
            headers=self.headers
        )
        
        if evidence_response.status_code != 200:
            return
        
        evidence_list = evidence_response.json()
        if not evidence_list or len(evidence_list) == 0:
            return
        
        evidence = evidence_list[0]
        evidence_id = evidence.get("evidence_id")
        encounter_id = evidence.get("encounter_id") or evidence.get("case_id")
        
        if not evidence_id or not encounter_id:
            return
        
        # Create access token
        response = requests.post(
            f"{BASE_URL}/api/custody-portal/create-access",
            headers=self.headers,
            json={
                "evidence_id": evidence_id,
                "encounter_id": encounter_id,
                "recipient_email": "public_test@example.com",
                "recipient_name": "Public Test User",
                "recipient_role": "attorney",
                "access_level": "full",
                "expires_hours": 24
            }
        )
        
        if response.status_code == 200:
            self.access_token = response.json().get("access_token")
            self.evidence_id = evidence_id
    
    def test_verify_access_invalid_token(self):
        """POST /api/custody-portal/verify-access returns 404 for invalid token"""
        response = requests.post(
            f"{BASE_URL}/api/custody-portal/verify-access",
            json={"access_token": "invalid_token_12345"}
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ POST /api/custody-portal/verify-access returns 404 for invalid token")
    
    def test_verify_access_valid_token(self):
        """POST /api/custody-portal/verify-access validates token and returns evidence info"""
        if not self.access_token:
            pytest.skip("No access token available - no evidence exists")
            return
        
        response = requests.post(
            f"{BASE_URL}/api/custody-portal/verify-access",
            json={"access_token": self.access_token}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("valid") == True, "Response should have valid=True"
        assert "evidence_id" in data, "Response should contain evidence_id"
        assert "recipient_name" in data, "Response should contain recipient_name"
        assert "recipient_role" in data, "Response should contain recipient_role"
        assert "access_level" in data, "Response should contain access_level"
        assert "expires_at" in data, "Response should contain expires_at"
        
        print(f"✓ POST /api/custody-portal/verify-access validates token successfully")
        print(f"  - Evidence ID: {data['evidence_id']}")
        print(f"  - Access Level: {data['access_level']}")
    
    def test_get_evidence_invalid_token(self):
        """GET /api/custody-portal/evidence returns 404 for invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/custody-portal/evidence?token=invalid_token_12345"
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET /api/custody-portal/evidence returns 404 for invalid token")
    
    def test_get_evidence_valid_token(self):
        """GET /api/custody-portal/evidence returns evidence details"""
        if not self.access_token:
            pytest.skip("No access token available - no evidence exists")
            return
        
        response = requests.get(
            f"{BASE_URL}/api/custody-portal/evidence?token={self.access_token}"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True, "Response should have success=True"
        assert "evidence" in data, "Response should contain evidence object"
        assert "access_info" in data, "Response should contain access_info"
        
        evidence = data["evidence"]
        assert "evidence_id" in evidence, "Evidence should have evidence_id"
        
        print(f"✓ GET /api/custody-portal/evidence returns evidence details")
        print(f"  - Evidence ID: {evidence.get('evidence_id')}")
        print(f"  - Filename: {evidence.get('filename')}")
    
    def test_get_chain_of_custody_invalid_token(self):
        """GET /api/custody-portal/chain-of-custody returns 404 for invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/custody-portal/chain-of-custody?token=invalid_token_12345"
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET /api/custody-portal/chain-of-custody returns 404 for invalid token")
    
    def test_get_chain_of_custody_valid_token(self):
        """GET /api/custody-portal/chain-of-custody returns custody chain"""
        if not self.access_token:
            pytest.skip("No access token available - no evidence exists")
            return
        
        response = requests.get(
            f"{BASE_URL}/api/custody-portal/chain-of-custody?token={self.access_token}"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True, "Response should have success=True"
        assert "evidence_id" in data, "Response should contain evidence_id"
        assert "chain_of_custody" in data, "Response should contain chain_of_custody"
        assert "total_events" in data, "Response should contain total_events"
        
        print(f"✓ GET /api/custody-portal/chain-of-custody returns custody chain")
        print(f"  - Total events: {data['total_events']}")
    
    def test_get_integrity_report_invalid_token(self):
        """GET /api/custody-portal/integrity-report returns 404 for invalid token"""
        response = requests.get(
            f"{BASE_URL}/api/custody-portal/integrity-report?token=invalid_token_12345"
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ GET /api/custody-portal/integrity-report returns 404 for invalid token")
    
    def test_get_integrity_report_valid_token(self):
        """GET /api/custody-portal/integrity-report returns full integrity report"""
        if not self.access_token:
            pytest.skip("No access token available - no evidence exists")
            return
        
        response = requests.get(
            f"{BASE_URL}/api/custody-portal/integrity-report?token={self.access_token}"
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") == True, "Response should have success=True"
        assert "report_generated_at" in data, "Response should contain report_generated_at"
        assert "evidence" in data, "Response should contain evidence"
        assert "chain_of_custody" in data, "Response should contain chain_of_custody"
        assert "legal_notice" in data, "Response should contain legal_notice"
        
        # Verify legal notice
        legal_notice = data["legal_notice"]
        assert "disclaimer" in legal_notice, "Legal notice should have disclaimer"
        assert "standard" in legal_notice, "Legal notice should have standard"
        
        print(f"✓ GET /api/custody-portal/integrity-report returns full integrity report")
        print(f"  - Standard: {legal_notice.get('standard')}")


class TestCustodyPortalEndpointValidation:
    """Tests for endpoint validation and error handling"""
    
    def test_create_access_missing_required_fields(self):
        """POST /api/custody-portal/create-access validates required fields"""
        # Login first
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        auth_token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        # Test with missing fields
        response = requests.post(
            f"{BASE_URL}/api/custody-portal/create-access",
            headers=headers,
            json={}  # Empty body
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ POST /api/custody-portal/create-access validates required fields")
    
    def test_verify_access_missing_token(self):
        """POST /api/custody-portal/verify-access requires access_token in body"""
        response = requests.post(
            f"{BASE_URL}/api/custody-portal/verify-access",
            json={}  # Empty body
        )
        
        # Should return 422 for validation error
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ POST /api/custody-portal/verify-access requires access_token in body")
    
    def test_get_evidence_missing_token_param(self):
        """GET /api/custody-portal/evidence requires token query parameter"""
        response = requests.get(f"{BASE_URL}/api/custody-portal/evidence")
        
        # Should return 422 for missing required query param
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ GET /api/custody-portal/evidence requires token query parameter")
    
    def test_get_chain_of_custody_missing_token_param(self):
        """GET /api/custody-portal/chain-of-custody requires token query parameter"""
        response = requests.get(f"{BASE_URL}/api/custody-portal/chain-of-custody")
        
        # Should return 422 for missing required query param
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ GET /api/custody-portal/chain-of-custody requires token query parameter")
    
    def test_get_integrity_report_missing_token_param(self):
        """GET /api/custody-portal/integrity-report requires token query parameter"""
        response = requests.get(f"{BASE_URL}/api/custody-portal/integrity-report")
        
        # Should return 422 for missing required query param
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        print("✓ GET /api/custody-portal/integrity-report requires token query parameter")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
