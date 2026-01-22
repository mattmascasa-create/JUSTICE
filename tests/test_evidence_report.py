"""
Test Evidence Report Feature
Tests the new GET /api/evidence/report/{case_id} endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://justice-civil.preview.emergentagent.com').rstrip('/')

class TestEvidenceReport:
    """Test Evidence Report API endpoint"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test - login and get token"""
        # Login with test credentials
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "ipfstest@test.com", "password": "test1234"}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.case_id = "case_bdbe479c2b25"
    
    def test_evidence_report_endpoint_exists(self):
        """Test that the evidence report endpoint exists and returns data"""
        response = requests.get(
            f"{BASE_URL}/api/evidence/report/{self.case_id}",
            headers=self.headers
        )
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text[:500] if response.text else 'Empty'}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify report structure
        assert "report_id" in data, "Missing report_id"
        assert "generated_at" in data, "Missing generated_at"
        assert "case" in data, "Missing case data"
        assert "evidence" in data, "Missing evidence list"
        assert "evidence_summary" in data, "Missing evidence_summary"
        assert "ipfs_status" in data, "Missing ipfs_status"
        assert "blockchain_status" in data, "Missing blockchain_status"
        assert "verification_instructions" in data, "Missing verification_instructions"
        assert "legal_notice" in data, "Missing legal_notice"
        
        print(f"SUCCESS: Report generated with ID: {data['report_id']}")
        return data
    
    def test_evidence_report_case_details(self):
        """Test that case details are included in the report"""
        response = requests.get(
            f"{BASE_URL}/api/evidence/report/{self.case_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        case = data["case"]
        assert case["case_id"] == self.case_id, "Case ID mismatch"
        assert "title" in case, "Missing case title"
        assert "status" in case, "Missing case status"
        assert "severity" in case, "Missing case severity"
        assert "violation_type" in case, "Missing violation_type"
        
        print(f"SUCCESS: Case details included - Title: {case.get('title')}")
    
    def test_evidence_report_evidence_summary(self):
        """Test that evidence summary is correct"""
        response = requests.get(
            f"{BASE_URL}/api/evidence/report/{self.case_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        summary = data["evidence_summary"]
        assert "total_files" in summary, "Missing total_files"
        assert "blockchain_verified" in summary, "Missing blockchain_verified"
        assert "ipfs_stored" in summary, "Missing ipfs_stored"
        assert "types" in summary, "Missing types breakdown"
        
        types = summary["types"]
        assert "document" in types, "Missing document count"
        assert "image" in types, "Missing image count"
        assert "video" in types, "Missing video count"
        assert "audio" in types, "Missing audio count"
        
        print(f"SUCCESS: Evidence summary - Total: {summary['total_files']}, IPFS: {summary['ipfs_stored']}, Blockchain: {summary['blockchain_verified']}")
    
    def test_evidence_report_evidence_details(self):
        """Test that evidence items have proper verification details"""
        response = requests.get(
            f"{BASE_URL}/api/evidence/report/{self.case_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        evidence_list = data["evidence"]
        assert len(evidence_list) > 0, "No evidence found in report"
        
        # Check first evidence item
        ev = evidence_list[0]
        assert "evidence_id" in ev, "Missing evidence_id"
        # Check for filename (could be file_name, filename, or original_filename)
        has_filename = "file_name" in ev or "filename" in ev or "original_filename" in ev
        assert has_filename, "Missing filename field"
        assert "file_type" in ev, "Missing file_type"
        # Check for timestamp (could be uploaded_at or created_at)
        has_timestamp = "uploaded_at" in ev or "created_at" in ev
        assert has_timestamp, "Missing timestamp field"
        
        # Check for IPFS fields
        if ev.get("ipfs_cid"):
            assert "ipfs_verified" in ev, "Missing ipfs_verified flag"
            assert "ipfs_gateway_url" in ev, "Missing ipfs_gateway_url"
            print(f"SUCCESS: Evidence has IPFS CID: {ev['ipfs_cid'][:20]}...")
        
        # Check for hash record
        if ev.get("hash_record"):
            hash_record = ev["hash_record"]
            assert "file_hash" in hash_record, "Missing file_hash"
            assert "metadata_hash" in hash_record, "Missing metadata_hash"
            assert "combined_hash" in hash_record, "Missing combined_hash"
            print(f"SUCCESS: Evidence has hash record with file_hash: {hash_record['file_hash'][:20]}...")
        
        # Check for chain of custody
        if ev.get("chain_of_custody"):
            custody = ev["chain_of_custody"]
            assert len(custody) > 0, "Empty chain of custody"
            first_entry = custody[0]
            assert "action" in first_entry, "Missing action in custody entry"
            assert "timestamp" in first_entry, "Missing timestamp in custody entry"
            print(f"SUCCESS: Evidence has {len(custody)} chain of custody entries")
        
        print(f"SUCCESS: Evidence details verified for {len(evidence_list)} items")
    
    def test_evidence_report_ipfs_status(self):
        """Test IPFS status in report"""
        response = requests.get(
            f"{BASE_URL}/api/evidence/report/{self.case_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        ipfs_status = data["ipfs_status"]
        assert "enabled" in ipfs_status, "Missing enabled flag"
        assert "gateway_url" in ipfs_status, "Missing gateway_url"
        assert "total_files_on_ipfs" in ipfs_status, "Missing total_files_on_ipfs"
        
        print(f"SUCCESS: IPFS Status - Enabled: {ipfs_status['enabled']}, Files on IPFS: {ipfs_status['total_files_on_ipfs']}")
    
    def test_evidence_report_blockchain_status(self):
        """Test blockchain status in report"""
        response = requests.get(
            f"{BASE_URL}/api/evidence/report/{self.case_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        blockchain_status = data["blockchain_status"]
        assert "total_verified" in blockchain_status, "Missing total_verified"
        assert "chain_intact" in blockchain_status, "Missing chain_intact"
        
        print(f"SUCCESS: Blockchain Status - Verified: {blockchain_status['total_verified']}, Chain Intact: {blockchain_status['chain_intact']}")
    
    def test_evidence_report_verification_instructions(self):
        """Test verification instructions are included"""
        response = requests.get(
            f"{BASE_URL}/api/evidence/report/{self.case_id}",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        
        instructions = data["verification_instructions"]
        assert "ipfs" in instructions, "Missing IPFS instructions"
        assert "blockchain" in instructions, "Missing blockchain instructions"
        assert "chain_of_custody" in instructions, "Missing chain of custody instructions"
        
        print("SUCCESS: Verification instructions included")
    
    def test_evidence_report_nonexistent_case(self):
        """Test that nonexistent case returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/evidence/report/nonexistent_case_123",
            headers=self.headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("SUCCESS: Nonexistent case returns 404")
    
    def test_evidence_report_unauthorized(self):
        """Test that unauthorized access is rejected"""
        response = requests.get(
            f"{BASE_URL}/api/evidence/report/{self.case_id}"
            # No auth header
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("SUCCESS: Unauthorized access rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
