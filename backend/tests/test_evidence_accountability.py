"""
Test Suite for Evidence Integrity and Accountability Portal APIs
Tests Court-Grade Evidence System and Police Accountability Portal
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"


class TestPublicAccountabilityAPIs:
    """Test public accountability endpoints (no auth required)"""
    
    def test_public_stats(self):
        """GET /api/accountability/public/stats - Get public statistics"""
        response = requests.get(f"{BASE_URL}/api/accountability/public/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "total_departments" in data
        assert "total_officers_tracked" in data
        assert "total_violations" in data
        assert "sustained_violations" in data
        assert "pending_violations" in data
        assert "total_settlements" in data
        assert "violations_by_type" in data
        assert "violations_by_severity" in data
        
        # Verify data values (seeded data)
        assert data["total_departments"] >= 12
        assert data["total_officers_tracked"] >= 98
        assert data["total_violations"] >= 139
        print(f"✓ Public stats: {data['total_departments']} departments, {data['total_officers_tracked']} officers, {data['total_violations']} violations")
    
    def test_public_departments(self):
        """GET /api/accountability/public/departments - Get departments list"""
        response = requests.get(f"{BASE_URL}/api/accountability/public/departments")
        assert response.status_code == 200
        data = response.json()
        
        assert "departments" in data
        assert len(data["departments"]) > 0
        
        # Verify department structure
        dept = data["departments"][0]
        assert "department_id" in dept
        assert "name" in dept
        assert "city" in dept
        assert "state" in dept
        assert "accountability_score" in dept
        assert "total_violations" in dept
        print(f"✓ Public departments: {len(data['departments'])} departments returned")
    
    def test_public_officers(self):
        """GET /api/accountability/public/officers - Get officers list"""
        response = requests.get(f"{BASE_URL}/api/accountability/public/officers")
        assert response.status_code == 200
        data = response.json()
        
        assert "officers" in data
        assert len(data["officers"]) > 0
        
        # Verify officer structure
        officer = data["officers"][0]
        assert "officer_id" in officer
        assert "badge_number" in officer
        assert "department_name" in officer
        assert "accountability_score" in officer
        assert "total_violations" in officer
        print(f"✓ Public officers: {len(data['officers'])} officers returned")
    
    def test_public_leaderboard(self):
        """GET /api/accountability/public/leaderboard - Get department leaderboard"""
        response = requests.get(f"{BASE_URL}/api/accountability/public/leaderboard")
        assert response.status_code == 200
        data = response.json()
        
        assert "best_departments" in data
        assert "worst_departments" in data
        assert len(data["best_departments"]) > 0
        assert len(data["worst_departments"]) > 0
        
        # Verify best departments are sorted by score (highest first)
        best = data["best_departments"]
        for i in range(len(best) - 1):
            assert best[i]["accountability_score"] >= best[i+1]["accountability_score"]
        
        print(f"✓ Leaderboard: {len(data['best_departments'])} best, {len(data['worst_departments'])} worst departments")


class TestAuthenticatedAPIs:
    """Test authenticated endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Authentication failed - skipping authenticated tests")
        
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_evidence_integrity_stats(self):
        """GET /api/evidence-integrity/stats - Get evidence integrity statistics"""
        response = requests.get(
            f"{BASE_URL}/api/evidence-integrity/stats",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert "total_evidence_tracked" in data
        assert "verified" in data
        assert "blockchain_anchored" in data
        assert "tamper_detected" in data
        assert "total_custody_events" in data
        print(f"✓ Evidence stats: {data['total_evidence_tracked']} tracked, {data['total_custody_events']} custody events")
    
    def test_evidence_register_and_verify(self):
        """POST /api/evidence-integrity/register - Register new evidence"""
        evidence_id = f"test_evidence_{uuid.uuid4().hex[:8]}"
        file_hash = f"sha256_{uuid.uuid4().hex}"
        
        # Register evidence
        response = requests.post(
            f"{BASE_URL}/api/evidence-integrity/register",
            params={"file_hash": file_hash},
            json={
                "evidence_id": evidence_id,
                "original_filename": "test_video.mp4",
                "file_size_bytes": 1024000,
                "mime_type": "video/mp4",
                "capture_timestamp": "2026-01-20T10:30:00Z",
                "blockchain_tier": "local"
            },
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert data["evidence_id"] == evidence_id
        assert data["hash_sha256"] == file_hash
        assert "integrity_signature" in data
        print(f"✓ Evidence registered: {evidence_id}")
        
        # Verify evidence
        response = requests.get(
            f"{BASE_URL}/api/evidence-integrity/{evidence_id}/verify",
            headers=self.headers
        )
        assert response.status_code == 200
        verify_data = response.json()
        
        assert verify_data["is_valid"] == True
        assert verify_data["hash_match"] == True
        assert verify_data["chain_of_custody_intact"] == True
        print(f"✓ Evidence verified: is_valid={verify_data['is_valid']}")
    
    def test_evidence_custody_chain(self):
        """GET /api/evidence-integrity/{id}/custody-chain - Get chain of custody"""
        evidence_id = f"test_custody_{uuid.uuid4().hex[:8]}"
        file_hash = f"sha256_{uuid.uuid4().hex}"
        
        # First register evidence
        requests.post(
            f"{BASE_URL}/api/evidence-integrity/register",
            params={"file_hash": file_hash},
            json={
                "evidence_id": evidence_id,
                "original_filename": "custody_test.mp4",
                "file_size_bytes": 512000,
                "mime_type": "video/mp4",
                "capture_timestamp": "2026-01-20T11:00:00Z",
                "blockchain_tier": "local"
            },
            headers=self.headers
        )
        
        # Get custody chain
        response = requests.get(
            f"{BASE_URL}/api/evidence-integrity/{evidence_id}/custody-chain",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["evidence_id"] == evidence_id
        assert "chain" in data
        assert "verification" in data
        assert len(data["chain"]) >= 1  # At least the creation event
        
        # Verify chain structure
        event = data["chain"][0]
        assert "event_id" in event
        assert "action" in event
        assert "timestamp" in event
        assert "event_hash" in event
        assert event["previous_hash"] == "GENESIS"  # First event
        
        print(f"✓ Custody chain: {len(data['chain'])} events, valid={data['verification']['valid']}")
    
    def test_evidence_court_package(self):
        """GET /api/evidence-integrity/{id}/court-package - Generate court package"""
        evidence_id = f"test_court_{uuid.uuid4().hex[:8]}"
        file_hash = f"sha256_{uuid.uuid4().hex}"
        
        # First register evidence
        requests.post(
            f"{BASE_URL}/api/evidence-integrity/register",
            params={"file_hash": file_hash},
            json={
                "evidence_id": evidence_id,
                "original_filename": "court_evidence.mp4",
                "file_size_bytes": 2048000,
                "mime_type": "video/mp4",
                "capture_timestamp": "2026-01-20T12:00:00Z",
                "blockchain_tier": "local"
            },
            headers=self.headers
        )
        
        # Get court package
        response = requests.get(
            f"{BASE_URL}/api/evidence-integrity/{evidence_id}/court-package",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "package" in data
        
        package = data["package"]
        assert package["evidence_id"] == evidence_id
        assert "forensic_metadata" in package
        assert "cryptographic_verification" in package
        assert "chain_of_custody" in package
        assert "verification_status" in package
        assert "legal_notice" in package
        
        # Verify forensic metadata
        assert package["forensic_metadata"]["original_filename"] == "court_evidence.mp4"
        assert package["forensic_metadata"]["file_size_bytes"] == 2048000
        
        print(f"✓ Court package generated: {evidence_id}")
    
    def test_report_violation(self):
        """POST /api/accountability/violations/report - Report a violation"""
        badge_number = f"TEST{uuid.uuid4().hex[:6].upper()}"
        
        response = requests.post(
            f"{BASE_URL}/api/accountability/violations/report",
            json={
                "badge_number": badge_number,
                "department_name": "Test Police Department",
                "department_state": "CA",
                "violation_type": "excessive_force",
                "severity": "moderate",
                "description": "Test violation report for automated testing",
                "incident_date": "2026-01-20"
            },
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "violation_id" in data
        assert "officer_id" in data
        assert "message" in data
        assert badge_number in data["message"]
        
        print(f"✓ Violation reported: {data['violation_id']} for badge {badge_number}")
    
    def test_report_violation_different_types(self):
        """Test reporting different violation types"""
        violation_types = [
            ("unlawful_search", "serious"),
            ("false_arrest", "critical"),
            ("miranda_violation", "moderate"),
            ("recording_interference", "minor")
        ]
        
        for vtype, severity in violation_types:
            badge_number = f"TEST{uuid.uuid4().hex[:6].upper()}"
            
            response = requests.post(
                f"{BASE_URL}/api/accountability/violations/report",
                json={
                    "badge_number": badge_number,
                    "department_name": "Multi-Type Test PD",
                    "department_state": "NY",
                    "violation_type": vtype,
                    "severity": severity,
                    "description": f"Test {vtype} violation",
                    "incident_date": "2026-01-21"
                },
                headers=self.headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] == True
            print(f"✓ Violation type '{vtype}' with severity '{severity}' reported successfully")


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip("Authentication failed")
        
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_verify_nonexistent_evidence(self):
        """Verify non-existent evidence returns proper response"""
        response = requests.get(
            f"{BASE_URL}/api/evidence-integrity/nonexistent_evidence_123/verify",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        # Should return invalid with warning
        assert data["is_valid"] == False
        assert "Evidence not found" in str(data.get("warnings", []))
        print("✓ Non-existent evidence handled correctly")
    
    def test_court_package_nonexistent(self):
        """Court package for non-existent evidence returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/evidence-integrity/nonexistent_123/court-package",
            headers=self.headers
        )
        assert response.status_code == 404
        print("✓ Non-existent court package returns 404")
    
    def test_unauthenticated_evidence_stats(self):
        """Evidence stats without auth returns 401 or 403"""
        response = requests.get(f"{BASE_URL}/api/evidence-integrity/stats")
        assert response.status_code in [401, 403]
        print(f"✓ Unauthenticated evidence stats returns {response.status_code}")
    
    def test_unauthenticated_violation_report(self):
        """Violation report without auth returns 401 or 403"""
        response = requests.post(
            f"{BASE_URL}/api/accountability/violations/report",
            json={
                "badge_number": "TEST123",
                "department_name": "Test PD",
                "department_state": "CA",
                "violation_type": "excessive_force",
                "severity": "moderate",
                "description": "Test",
                "incident_date": "2026-01-20"
            }
        )
        assert response.status_code in [401, 403]
        print(f"✓ Unauthenticated violation report returns {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
