"""
IPFS Integration Tests for JUSTICE Platform
Tests Pinata IPFS integration for evidence storage
"""
import pytest
import requests
import os
import tempfile

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestIPFSIntegration:
    """Test IPFS/Pinata integration endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get auth token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "ipfstest@test.com",
            "password": "test1234"
        })
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.auth_token = token
        else:
            pytest.skip("Authentication failed - skipping authenticated tests")
    
    def test_ipfs_status_endpoint(self):
        """Test GET /api/ipfs/status returns correct IPFS status"""
        response = requests.get(f"{BASE_URL}/api/ipfs/status")
        assert response.status_code == 200
        
        data = response.json()
        # Verify required fields
        assert "ipfs_enabled" in data
        assert "pinata_connected" in data
        assert "gateway_url" in data
        assert "total_evidence_on_ipfs" in data
        
        # Verify IPFS is enabled and Pinata is connected
        assert data["ipfs_enabled"] == True, "IPFS should be enabled"
        assert data["pinata_connected"] == True, "Pinata should be connected"
        assert data["gateway_url"] == "https://gateway.pinata.cloud/ipfs"
        
        print(f"IPFS Status: enabled={data['ipfs_enabled']}, pinata_connected={data['pinata_connected']}")
        print(f"Total evidence on IPFS: {data['total_evidence_on_ipfs']}")
    
    def test_health_endpoint_shows_ipfs_enabled(self):
        """Test GET /api/health includes ipfs_enabled flag"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "ipfs_enabled" in data
        assert data["ipfs_enabled"] == True
        print(f"Health check: ipfs_enabled={data['ipfs_enabled']}")
    
    def test_secure_upload_with_ipfs(self):
        """Test POST /api/evidence/secure-upload uploads to IPFS"""
        # Create a test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(f"Test IPFS evidence content - pytest test")
            temp_file_path = f.name
        
        try:
            # Upload file
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('test_ipfs_evidence.txt', f, 'text/plain')}
                # Remove Content-Type header for multipart upload
                headers = {"Authorization": f"Bearer {self.auth_token}"}
                response = requests.post(
                    f"{BASE_URL}/api/evidence/secure-upload",
                    files=files,
                    data={"case_id": "case_bdbe479c2b25", "description": "IPFS test upload"},
                    headers=headers
                )
            
            assert response.status_code == 200, f"Upload failed: {response.text}"
            
            data = response.json()
            # Verify blockchain hashing
            assert "evidence_id" in data
            assert "file_hash" in data
            assert "combined_hash" in data
            assert "blockchain_verified" in data
            assert data["blockchain_verified"] == True
            
            # Verify IPFS upload
            assert "ipfs" in data
            ipfs_data = data["ipfs"]
            assert ipfs_data["enabled"] == True, "IPFS should be enabled"
            assert ipfs_data["cid"] is not None, "IPFS CID should be returned"
            assert ipfs_data["url"].startswith("ipfs://"), "IPFS URL should start with ipfs://"
            assert "gateway.pinata.cloud" in ipfs_data["gateway_url"], "Gateway URL should be Pinata"
            assert ipfs_data["error"] is None, f"IPFS upload error: {ipfs_data['error']}"
            
            print(f"Evidence uploaded: {data['evidence_id']}")
            print(f"File hash: {data['file_hash'][:32]}...")
            print(f"IPFS CID: {ipfs_data['cid']}")
            print(f"Gateway URL: {ipfs_data['gateway_url']}")
            
            # Store evidence_id for verification test
            self.uploaded_evidence_id = data['evidence_id']
            self.ipfs_cid = ipfs_data['cid']
            
            return data['evidence_id']
            
        finally:
            os.unlink(temp_file_path)
    
    def test_evidence_verification_with_ipfs(self):
        """Test GET /api/evidence/{id}/verify includes IPFS verification"""
        # First upload evidence
        evidence_id = self.test_secure_upload_with_ipfs()
        
        # Verify the evidence
        response = self.session.get(f"{BASE_URL}/api/evidence/{evidence_id}/verify")
        assert response.status_code == 200
        
        data = response.json()
        # Verify basic verification fields
        assert data["is_valid"] == True
        assert data["chain_intact"] == True
        assert data["court_admissible"] == True
        
        # Verify IPFS verification
        assert "ipfs" in data
        ipfs_data = data["ipfs"]
        assert ipfs_data["enabled"] == True
        assert ipfs_data["cid"] is not None
        
        # Check IPFS content verification
        if "verification" in ipfs_data and ipfs_data["verification"]:
            verification = ipfs_data["verification"]
            assert verification["verified"] == True, "IPFS content should be verified"
            assert verification["ipfs_accessible"] == True, "IPFS content should be accessible"
            assert verification["hash_matches"] == True, "IPFS hash should match"
            print(f"IPFS verification: verified={verification['verified']}, hash_matches={verification['hash_matches']}")
        
        print(f"Evidence verification: is_valid={data['is_valid']}, chain_intact={data['chain_intact']}")
    
    def test_evidence_certificate_includes_ipfs(self):
        """Test GET /api/evidence/{id}/certificate includes IPFS info"""
        # First upload evidence
        evidence_id = self.test_secure_upload_with_ipfs()
        
        # Get certificate
        response = self.session.get(f"{BASE_URL}/api/evidence/{evidence_id}/certificate")
        assert response.status_code == 200
        
        data = response.json()
        # Verify certificate fields
        assert "certificate_id" in data
        assert "file_hash" in data
        assert "integrity_statement" in data
        assert "legal_notice" in data
        
        # Check for IPFS storage info
        if "ipfs_storage" in data and data["ipfs_storage"]:
            ipfs_storage = data["ipfs_storage"]
            assert ipfs_storage["stored"] == True
            assert ipfs_storage["cid"] is not None
            print(f"Certificate IPFS storage: cid={ipfs_storage['cid']}")
        
        # Verify IPFS mentioned in legal notice
        if data.get("ipfs_storage"):
            assert "IPFS" in data["integrity_statement"] or "IPFS" in data["legal_notice"], \
                "Certificate should mention IPFS storage"
        
        print(f"Certificate generated: {data['certificate_id']}")
    
    def test_existing_evidence_verification(self):
        """Test verification of existing evidence (evi_573bdc595c7e)"""
        response = self.session.get(f"{BASE_URL}/api/evidence/evi_573bdc595c7e/verify")
        
        if response.status_code == 404:
            pytest.skip("Existing evidence not found - may have been deleted")
        
        assert response.status_code == 200
        data = response.json()
        
        print(f"Existing evidence verification: is_valid={data.get('is_valid')}")
        if "ipfs" in data and data["ipfs"]:
            print(f"IPFS info: {data['ipfs']}")


class TestBlockchainStatus:
    """Test blockchain status endpoints"""
    
    def test_blockchain_status(self):
        """Test GET /api/blockchain/status"""
        response = requests.get(f"{BASE_URL}/api/blockchain/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_blocks" in data
        assert "total_evidence_hashed" in data
        assert "chain_valid" in data
        
        print(f"Blockchain status: blocks={data['total_blocks']}, evidence_hashed={data['total_evidence_hashed']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
