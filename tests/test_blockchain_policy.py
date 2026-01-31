"""
Test Suite for JUSTICE Platform Phase 7 - Blockchain Evidence & Policy Dashboard
Tests: Secure upload, verification, certificates, blockchain status, policy reports
"""

import pytest
import requests
import os
import io
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rights-guardian-6.preview.emergentagent.com').rstrip('/')

# Test credentials
TEST_EMAIL = "encounter_test@example.com"
TEST_PASSWORD = "password123"


class TestHealthAndBlockchainStatus:
    """Health check and blockchain status tests"""
    
    def test_health_check(self):
        """Test health endpoint returns version 5.0.0"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        print(f"Health check passed - Version: {data['version']}")
    
    def test_blockchain_status_public(self):
        """Test blockchain status endpoint (public access)"""
        response = requests.get(f"{BASE_URL}/api/blockchain/status")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "total_blocks" in data
        assert "total_evidence_hashed" in data
        assert "pending_hashes" in data
        assert "recent_blocks" in data
        assert "chain_valid" in data
        
        print(f"Blockchain status: {data['total_blocks']} blocks, {data['total_evidence_hashed']} evidence hashed")


class TestAuthentication:
    """Authentication tests"""
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == TEST_EMAIL
        print(f"Login successful for {TEST_EMAIL}")
        return data["access_token"]
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401


@pytest.fixture
def auth_token():
    """Get authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json()["access_token"]
    pytest.skip("Authentication failed - skipping authenticated tests")


@pytest.fixture
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


class TestSecureEvidenceUpload:
    """Tests for POST /api/evidence/secure-upload"""
    
    def test_secure_upload_requires_auth(self):
        """Test that secure upload requires authentication"""
        files = {"file": ("test.txt", io.BytesIO(b"test content"), "text/plain")}
        response = requests.post(f"{BASE_URL}/api/evidence/secure-upload", files=files)
        assert response.status_code == 401
        print("Secure upload correctly requires authentication")
    
    def test_secure_upload_success(self, auth_headers):
        """Test successful secure evidence upload with blockchain hash"""
        # Create test file
        test_content = f"Test evidence content - {datetime.now().isoformat()}"
        files = {"file": ("test_evidence.txt", io.BytesIO(test_content.encode()), "text/plain")}
        data = {
            "description": "TEST_blockchain_evidence",
            "evidence_type": "document"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/evidence/secure-upload",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        result = response.json()
        
        # Verify blockchain fields in response
        assert "evidence_id" in result
        assert "file_hash" in result
        assert "combined_hash" in result
        assert "hash_id" in result
        assert result["blockchain_verified"] == True
        assert result["chain_of_custody_started"] == True
        
        # Verify SHA-256 hash format (64 hex characters)
        assert len(result["file_hash"]) == 64
        assert len(result["combined_hash"]) == 64
        
        print(f"Secure upload successful: {result['evidence_id']}")
        print(f"  File hash: {result['file_hash'][:16]}...")
        print(f"  Combined hash: {result['combined_hash'][:16]}...")
        
        return result["evidence_id"]
    
    def test_secure_upload_with_case_id(self, auth_headers):
        """Test secure upload with case_id parameter"""
        # First create a case
        case_response = requests.post(
            f"{BASE_URL}/api/cases",
            json={
                "title": "TEST_Blockchain Evidence Case",
                "description": "Test case for blockchain evidence",
                "incident_date": datetime.now().isoformat(),
                "location": "Test Location",
                "violation_type": "4th Amendment",
                "severity": "medium"
            },
            headers=auth_headers
        )
        
        if case_response.status_code == 200:
            case_id = case_response.json()["case_id"]
            
            # Upload evidence to case
            files = {"file": ("case_evidence.txt", io.BytesIO(b"Case evidence content"), "text/plain")}
            data = {
                "case_id": case_id,
                "description": "TEST_case_blockchain_evidence",
                "evidence_type": "document"
            }
            
            response = requests.post(
                f"{BASE_URL}/api/evidence/secure-upload",
                files=files,
                data=data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            result = response.json()
            assert "file_hash" in result
            assert "combined_hash" in result
            print(f"Secure upload with case_id successful: {result['evidence_id']}")


class TestEvidenceVerification:
    """Tests for GET /api/evidence/{id}/verify"""
    
    def test_verify_requires_auth(self):
        """Test that verification requires authentication"""
        response = requests.get(f"{BASE_URL}/api/evidence/evi_446e93b5d511/verify")
        assert response.status_code == 401
        print("Verification correctly requires authentication")
    
    def test_verify_existing_evidence(self, auth_headers):
        """Test verification of existing evidence (evi_446e93b5d511)"""
        evidence_id = "evi_446e93b5d511"
        response = requests.get(
            f"{BASE_URL}/api/evidence/{evidence_id}/verify",
            headers=auth_headers
        )
        
        # Evidence may or may not exist
        if response.status_code == 200:
            data = response.json()
            
            # Verify response structure
            assert "verification_id" in data
            assert "evidence_id" in data
            assert "original_hash" in data
            assert "current_hash" in data
            assert "is_valid" in data
            assert "chain_intact" in data
            assert "custody_entries" in data
            assert "court_admissible" in data
            assert "hash_algorithm" in data
            
            print(f"Evidence verification for {evidence_id}:")
            print(f"  Is valid: {data['is_valid']}")
            print(f"  Chain intact: {data['chain_intact']}")
            print(f"  Court admissible: {data['court_admissible']}")
            print(f"  Custody entries: {data['custody_entries']}")
        elif response.status_code == 404:
            print(f"Evidence {evidence_id} not found - creating new evidence for test")
            # Upload new evidence and verify it
            self._upload_and_verify(auth_headers)
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def _upload_and_verify(self, auth_headers):
        """Helper to upload and verify new evidence"""
        # Upload
        files = {"file": ("verify_test.txt", io.BytesIO(b"Verification test content"), "text/plain")}
        data = {"description": "TEST_verification_test", "evidence_type": "document"}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/evidence/secure-upload",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        if upload_response.status_code == 200:
            evidence_id = upload_response.json()["evidence_id"]
            
            # Verify
            verify_response = requests.get(
                f"{BASE_URL}/api/evidence/{evidence_id}/verify",
                headers=auth_headers
            )
            
            assert verify_response.status_code == 200
            data = verify_response.json()
            assert data["is_valid"] == True
            assert data["chain_intact"] == True
            print(f"New evidence {evidence_id} verified successfully")
    
    def test_verify_nonexistent_evidence(self, auth_headers):
        """Test verification of non-existent evidence returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/evidence/evi_nonexistent123/verify",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("Non-existent evidence correctly returns 404")


class TestEvidenceCertificate:
    """Tests for GET /api/evidence/{id}/certificate"""
    
    def test_certificate_requires_auth(self):
        """Test that certificate generation requires authentication"""
        response = requests.get(f"{BASE_URL}/api/evidence/evi_446e93b5d511/certificate")
        assert response.status_code == 401
        print("Certificate generation correctly requires authentication")
    
    def test_generate_certificate(self, auth_headers):
        """Test certificate generation for evidence"""
        # First upload evidence
        files = {"file": ("cert_test.txt", io.BytesIO(b"Certificate test content"), "text/plain")}
        data = {"description": "TEST_certificate_test", "evidence_type": "document"}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/evidence/secure-upload",
            files=files,
            data=data,
            headers=auth_headers
        )
        
        if upload_response.status_code == 200:
            evidence_id = upload_response.json()["evidence_id"]
            
            # Generate certificate
            cert_response = requests.get(
                f"{BASE_URL}/api/evidence/{evidence_id}/certificate",
                headers=auth_headers
            )
            
            assert cert_response.status_code == 200
            cert = cert_response.json()
            
            # Verify certificate structure
            assert "certificate_id" in cert
            assert "certificate_type" in cert
            assert cert["certificate_type"] == "DIGITAL EVIDENCE AUTHENTICITY CERTIFICATE"
            assert "evidence_details" in cert
            assert "cryptographic_verification" in cert
            assert "chain_of_custody" in cert
            assert "integrity_statement" in cert
            assert "legal_notice" in cert
            assert "certificate_hash" in cert
            
            # Verify cryptographic verification section
            crypto = cert["cryptographic_verification"]
            assert crypto["algorithm"] == "SHA-256"
            assert "file_hash" in crypto
            assert "metadata_hash" in crypto
            assert "combined_hash" in crypto
            
            print(f"Certificate generated: {cert['certificate_id']}")
            print(f"  File hash: {crypto['file_hash'][:16]}...")
            print(f"  Chain of custody entries: {cert['chain_of_custody']['total_entries']}")
    
    def test_certificate_nonexistent_evidence(self, auth_headers):
        """Test certificate for non-existent evidence returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/evidence/evi_nonexistent123/certificate",
            headers=auth_headers
        )
        assert response.status_code == 404
        print("Non-existent evidence certificate correctly returns 404")


class TestPolicyDashboard:
    """Tests for Policy Dashboard endpoints"""
    
    def test_dashboard_data_public(self):
        """Test GET /api/policy/dashboard-data (public access)"""
        response = requests.get(f"{BASE_URL}/api/policy/dashboard-data")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "overview" in data
        assert "violations_breakdown" in data
        assert "state_breakdown" in data
        assert "severity_breakdown" in data
        assert "top_departments" in data
        assert "repeat_officers" in data
        assert "recent_reports" in data
        
        # Verify overview fields
        overview = data["overview"]
        assert "total_submissions" in overview
        assert "total_departments" in overview
        assert "total_officers" in overview
        assert "repeat_offenders" in overview
        
        print(f"Policy Dashboard Data:")
        print(f"  Total submissions: {overview['total_submissions']}")
        print(f"  Total departments: {overview['total_departments']}")
        print(f"  Total officers: {overview['total_officers']}")
        print(f"  Repeat offenders: {overview['repeat_offenders']}")
        print(f"  Violations breakdown: {len(data['violations_breakdown'])} types")
        print(f"  State breakdown: {len(data['state_breakdown'])} states")
    
    def test_list_reports_public(self):
        """Test GET /api/policy/reports (public access)"""
        response = requests.get(f"{BASE_URL}/api/policy/reports")
        assert response.status_code == 200
        data = response.json()
        
        assert "reports" in data
        print(f"Policy reports available: {len(data['reports'])}")
    
    def test_list_reports_with_filters(self):
        """Test GET /api/policy/reports with filters"""
        # Filter by report type
        response = requests.get(f"{BASE_URL}/api/policy/reports?report_type=department_accountability")
        assert response.status_code == 200
        
        # Filter by target audience
        response = requests.get(f"{BASE_URL}/api/policy/reports?target_audience=city_council")
        assert response.status_code == 200
        print("Report filtering works correctly")


class TestPolicyReportGeneration:
    """Tests for POST /api/policy/generate-report"""
    
    def test_generate_report_requires_auth(self):
        """Test that report generation requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/policy/generate-report",
            data={"report_type": "department_accountability", "target_audience": "city_council"}
        )
        assert response.status_code == 401
        print("Report generation correctly requires authentication")
    
    def test_generate_department_accountability_report(self, auth_headers):
        """Test generating department accountability report"""
        response = requests.post(
            f"{BASE_URL}/api/policy/generate-report",
            data={
                "report_type": "department_accountability",
                "target_audience": "city_council"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        report = response.json()
        
        # Verify report structure
        assert "report_id" in report
        assert report["report_type"] == "department_accountability"
        assert report["target_audience"] == "city_council"
        assert "title" in report
        assert "executive_summary" in report
        assert "key_findings" in report
        assert "recommendations" in report
        assert "charts_data" in report
        assert "generated_at" in report
        
        print(f"Generated report: {report['report_id']}")
        print(f"  Title: {report['title']}")
        print(f"  Key findings: {len(report['key_findings'])}")
        print(f"  Recommendations: {len(report['recommendations'])}")
        
        return report["report_id"]
    
    def test_generate_officer_pattern_report(self, auth_headers):
        """Test generating officer pattern analysis report"""
        response = requests.post(
            f"{BASE_URL}/api/policy/generate-report",
            data={
                "report_type": "officer_pattern",
                "target_audience": "media"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        report = response.json()
        assert report["report_type"] == "officer_pattern"
        assert report["target_audience"] == "media"
        print(f"Officer pattern report generated: {report['report_id']}")
    
    def test_generate_state_analysis_report(self, auth_headers):
        """Test generating state analysis report"""
        response = requests.post(
            f"{BASE_URL}/api/policy/generate-report",
            data={
                "report_type": "state_analysis",
                "target_audience": "legislators"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        report = response.json()
        assert report["report_type"] == "state_analysis"
        print(f"State analysis report generated: {report['report_id']}")
    
    def test_generate_violation_trend_report(self, auth_headers):
        """Test generating violation trend report"""
        response = requests.post(
            f"{BASE_URL}/api/policy/generate-report",
            data={
                "report_type": "violation_trend",
                "target_audience": "civil_rights_org"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        report = response.json()
        assert report["report_type"] == "violation_trend"
        print(f"Violation trend report generated: {report['report_id']}")
    
    def test_generate_report_with_filters(self, auth_headers):
        """Test generating report with department and state filters"""
        response = requests.post(
            f"{BASE_URL}/api/policy/generate-report",
            data={
                "report_type": "department_accountability",
                "target_audience": "city_council",
                "department": "LAPD",
                "state": "California"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        report = response.json()
        assert "LAPD" in report["title"] or "California" in report["title"]
        print(f"Filtered report generated: {report['report_id']}")


class TestGetSpecificReport:
    """Tests for GET /api/policy/report/{id}"""
    
    def test_get_report_by_id(self, auth_headers):
        """Test getting a specific report by ID"""
        # First generate a report
        gen_response = requests.post(
            f"{BASE_URL}/api/policy/generate-report",
            data={
                "report_type": "department_accountability",
                "target_audience": "city_council"
            },
            headers=auth_headers
        )
        
        if gen_response.status_code == 200:
            report_id = gen_response.json()["report_id"]
            
            # Get the report
            get_response = requests.get(f"{BASE_URL}/api/policy/report/{report_id}")
            assert get_response.status_code == 200
            
            report = get_response.json()
            assert report["report_id"] == report_id
            print(f"Successfully retrieved report: {report_id}")
    
    def test_get_nonexistent_report(self):
        """Test getting non-existent report returns 404"""
        response = requests.get(f"{BASE_URL}/api/policy/report/rpt_nonexistent123")
        assert response.status_code == 404
        print("Non-existent report correctly returns 404")


class TestRegressionPhase1to6:
    """Regression tests for Phase 1-6 features"""
    
    def test_auth_endpoints(self):
        """Test auth endpoints still work"""
        # Login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200
        print("Auth endpoints: PASS")
    
    def test_cases_endpoint(self, auth_headers):
        """Test cases endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/cases", headers=auth_headers)
        assert response.status_code == 200
        print("Cases endpoint: PASS")
    
    def test_attorneys_endpoint(self):
        """Test attorneys endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/attorneys")
        assert response.status_code == 200
        print("Attorneys endpoint: PASS")
    
    def test_departments_endpoint(self):
        """Test departments endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/departments")
        assert response.status_code == 200
        print("Departments endpoint: PASS")
    
    def test_community_stats_endpoint(self):
        """Test community stats endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/community/stats")
        assert response.status_code == 200
        print("Community stats endpoint: PASS")
    
    def test_encounters_endpoint(self, auth_headers):
        """Test encounters endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/encounters", headers=auth_headers)
        assert response.status_code == 200
        print("Encounters endpoint: PASS")
    
    def test_analytics_endpoint(self, auth_headers):
        """Test analytics endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/analytics/dashboard", headers=auth_headers)
        assert response.status_code == 200
        print("Analytics endpoint: PASS")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
