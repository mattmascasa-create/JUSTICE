"""
Test Multi-Cloud Backup and Attorney Live Stream APIs
Tests for iteration 39 - new features for JUSTICE platform
"""
import pytest
import requests
import os
import io
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests to get tokens for subsequent tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token for test user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data
        return data["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get auth headers"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_login_success(self):
        """Test login with valid credentials"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "user" in data
        print(f"✓ Login successful, user_id: {data['user'].get('user_id')}")


class TestMultiCloudBackup:
    """Test Multi-Cloud Backup API endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_get_enabled_providers(self, auth_headers):
        """GET /api/backup/providers - returns enabled cloud providers"""
        response = requests.get(f"{BASE_URL}/api/backup/providers", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "providers" in data
        assert "count" in data
        
        providers = data["providers"]
        print(f"✓ Enabled providers: {providers}")
        
        # Verify expected providers are present (S3, IPFS, Local)
        # Based on config: S3_ENABLED=true, IPFS_ENABLED=true, Local always enabled
        assert "local_storage" in providers, "Local storage should always be enabled"
        
        # Check if S3 is enabled (based on env vars)
        if "aws_s3" in providers:
            print("  - AWS S3 enabled")
        
        # Check if IPFS is enabled (based on PINATA_JWT)
        if "ipfs_pinata" in providers:
            print("  - IPFS (Pinata) enabled")
        
        assert data["count"] >= 1, "At least local storage should be enabled"
        print(f"✓ Total providers: {data['count']}, redundancy_available: {data.get('redundancy_available')}")
    
    def test_get_providers_requires_auth(self):
        """GET /api/backup/providers requires authentication"""
        response = requests.get(f"{BASE_URL}/api/backup/providers")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Providers endpoint requires authentication")
    
    def test_backup_status_not_found(self, auth_headers):
        """GET /api/backup/status/{evidence_id} - returns not found for non-existent evidence"""
        fake_evidence_id = f"ev_test_{uuid.uuid4().hex[:8]}"
        response = requests.get(f"{BASE_URL}/api/backup/status/{fake_evidence_id}", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert data.get("found") == False
        print(f"✓ Backup status returns not found for non-existent evidence")
    
    def test_backup_history(self, auth_headers):
        """GET /api/backup/history - returns user's backup history"""
        response = requests.get(f"{BASE_URL}/api/backup/history", headers=auth_headers)
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "backups" in data
        assert "count" in data
        print(f"✓ Backup history returned {data['count']} records")
    
    def test_backup_evidence_requires_file(self, auth_headers):
        """POST /api/backup/evidence/{evidence_id} - requires file upload"""
        evidence_id = f"ev_test_{uuid.uuid4().hex[:8]}"
        
        # Try without file - should fail
        response = requests.post(
            f"{BASE_URL}/api/backup/evidence/{evidence_id}",
            headers=auth_headers,
            data={"encounter_id": "enc_test_123"}
        )
        # Should return 422 (validation error) because file is required
        assert response.status_code == 422, f"Expected 422, got {response.status_code}: {response.text}"
        print("✓ Backup evidence endpoint requires file upload")
    
    def test_backup_evidence_with_file(self, auth_headers):
        """POST /api/backup/evidence/{evidence_id} - uploads evidence to multiple clouds"""
        evidence_id = f"ev_test_{uuid.uuid4().hex[:8]}"
        encounter_id = f"enc_test_{uuid.uuid4().hex[:8]}"
        
        # Create a test file
        test_content = b"Test evidence file content for multi-cloud backup"
        files = {
            'file': ('test_evidence.txt', io.BytesIO(test_content), 'text/plain')
        }
        data = {
            'encounter_id': encounter_id
        }
        
        response = requests.post(
            f"{BASE_URL}/api/backup/evidence/{evidence_id}",
            headers=auth_headers,
            files=files,
            data=data
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        result = response.json()
        assert result.get("success") == True
        assert "providers" in result
        assert "total_backups" in result
        assert "redundancy_level" in result
        
        print(f"✓ Evidence backed up to {result['total_backups']} providers")
        print(f"  - Redundancy level: {result['redundancy_level']}")
        print(f"  - File hash: {result.get('file_hash', 'N/A')[:16]}...")
        
        # Check individual provider results
        for provider, status in result.get("providers", {}).items():
            if status.get("success"):
                print(f"  - {provider}: SUCCESS")
            else:
                print(f"  - {provider}: FAILED - {status.get('error', 'Unknown error')}")
    
    def test_verify_backup_integrity(self, auth_headers):
        """POST /api/backup/verify/{evidence_id} - verifies backup integrity"""
        # Use a non-existent evidence ID - should return not found
        fake_evidence_id = f"ev_verify_{uuid.uuid4().hex[:8]}"
        response = requests.post(
            f"{BASE_URL}/api/backup/verify/{fake_evidence_id}",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        # Should indicate no backup found
        assert data.get("verified") == False or data.get("error") is not None
        print("✓ Verify backup integrity endpoint working")


class TestAttorneyStream:
    """Test Attorney Live Stream API endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 200
        return response.json()["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        return {"Authorization": f"Bearer {auth_token}"}
    
    @pytest.fixture(scope="class")
    def test_encounter(self, auth_headers):
        """Create a test encounter for stream testing"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/start",
            headers=auth_headers,
            json={
                "latitude": 34.0522,
                "longitude": -118.2437,
                "address": "Test Location, Los Angeles, CA",
                "encounter_type": "traffic_stop",
                "broadcast_mode": "save"
            }
        )
        if response.status_code == 200:
            return response.json()
        return None
    
    def test_create_stream_requires_auth(self):
        """POST /api/attorney-stream/create requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/attorney-stream/create",
            json={
                "encounter_id": "enc_test_123",
                "attorney_email": "attorney@test.com"
            }
        )
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Create stream requires authentication")
    
    def test_create_stream_with_encounter(self, auth_headers, test_encounter):
        """POST /api/attorney-stream/create - creates stream session with tokens"""
        if not test_encounter:
            pytest.skip("No test encounter available")
        
        response = requests.post(
            f"{BASE_URL}/api/attorney-stream/create",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter["encounter_id"],
                "attorney_email": "my_attorney@lawfirm.com",
                "location": "Test Location, Los Angeles, CA",
                "notification_method": "email"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "session_id" in data
        assert "stream_code" in data
        assert "stream_url" in data
        assert "user_token" in data
        assert "attorney_token" in data
        assert "expires_at" in data
        
        print(f"✓ Stream session created")
        print(f"  - Session ID: {data['session_id']}")
        print(f"  - Stream code: {data['stream_code']}")
        print(f"  - Stream URL: {data['stream_url']}")
        print(f"  - Notification sent: {data.get('notification_sent', False)}")
        
        return data
    
    def test_create_stream_with_notification_methods(self, auth_headers, test_encounter):
        """POST /api/attorney-stream/create - accepts different notification methods"""
        if not test_encounter:
            pytest.skip("No test encounter available")
        
        notification_methods = ["email", "sms", "both", "in-app"]
        
        for method in notification_methods:
            response = requests.post(
                f"{BASE_URL}/api/attorney-stream/create",
                headers=auth_headers,
                json={
                    "encounter_id": test_encounter["encounter_id"],
                    "attorney_email": "test_attorney@lawfirm.com",
                    "notification_method": method
                }
            )
            assert response.status_code == 200, f"Failed for method {method}: {response.text}"
            data = response.json()
            assert data.get("success") == True
            print(f"✓ Stream created with notification_method='{method}'")
    
    def test_get_session_by_code(self, auth_headers, test_encounter):
        """GET /api/attorney-stream/session/{stream_code} - returns session status"""
        if not test_encounter:
            pytest.skip("No test encounter available")
        
        # First create a stream
        create_response = requests.post(
            f"{BASE_URL}/api/attorney-stream/create",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter["encounter_id"],
                "attorney_email": "session_test@lawfirm.com"
            }
        )
        assert create_response.status_code == 200
        stream_data = create_response.json()
        stream_code = stream_data["stream_code"]
        
        # Get session by code (no auth required)
        response = requests.get(f"{BASE_URL}/api/attorney-stream/session/{stream_code}")
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert data.get("stream_code") == stream_code
        assert "status" in data
        assert "attorney_connected" in data
        assert "user_connected" in data
        assert "created_at" in data
        assert "expires_at" in data
        
        print(f"✓ Session retrieved by code")
        print(f"  - Status: {data['status']}")
        print(f"  - Attorney connected: {data['attorney_connected']}")
        print(f"  - User connected: {data['user_connected']}")
    
    def test_get_session_not_found(self):
        """GET /api/attorney-stream/session/{stream_code} - returns 404 for invalid code"""
        response = requests.get(f"{BASE_URL}/api/attorney-stream/session/invalid_code_12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Session not found returns 404")
    
    def test_join_stream_as_attorney(self, auth_headers, test_encounter):
        """POST /api/attorney-stream/join - attorney joins with token"""
        if not test_encounter:
            pytest.skip("No test encounter available")
        
        # Create a stream
        create_response = requests.post(
            f"{BASE_URL}/api/attorney-stream/create",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter["encounter_id"],
                "attorney_email": "join_test@lawfirm.com"
            }
        )
        assert create_response.status_code == 200
        stream_data = create_response.json()
        
        # Join as attorney (no auth required - uses token)
        response = requests.post(
            f"{BASE_URL}/api/attorney-stream/join",
            json={
                "stream_code": stream_data["stream_code"],
                "token": stream_data["attorney_token"],
                "role": "attorney"
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert data.get("role") == "attorney"
        assert data.get("attorney_connected") == True
        
        print(f"✓ Attorney joined stream successfully")
        print(f"  - Status: {data.get('status')}")
    
    def test_join_stream_invalid_token(self, auth_headers, test_encounter):
        """POST /api/attorney-stream/join - rejects invalid token"""
        if not test_encounter:
            pytest.skip("No test encounter available")
        
        # Create a stream
        create_response = requests.post(
            f"{BASE_URL}/api/attorney-stream/create",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter["encounter_id"]
            }
        )
        assert create_response.status_code == 200
        stream_data = create_response.json()
        
        # Try to join with invalid token
        response = requests.post(
            f"{BASE_URL}/api/attorney-stream/join",
            json={
                "stream_code": stream_data["stream_code"],
                "token": "invalid_token_12345",
                "role": "attorney"
            }
        )
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
        print("✓ Invalid token rejected with 403")
    
    def test_send_and_get_messages(self, auth_headers, test_encounter):
        """POST /api/attorney-stream/message and GET /api/attorney-stream/messages/{stream_code}"""
        if not test_encounter:
            pytest.skip("No test encounter available")
        
        # Create a stream
        create_response = requests.post(
            f"{BASE_URL}/api/attorney-stream/create",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter["encounter_id"]
            }
        )
        assert create_response.status_code == 200
        stream_data = create_response.json()
        stream_code = stream_data["stream_code"]
        
        # Send a message
        send_response = requests.post(
            f"{BASE_URL}/api/attorney-stream/message",
            json={
                "stream_code": stream_code,
                "message": "Stay calm, I'm watching the stream",
                "sender_role": "attorney"
            }
        )
        assert send_response.status_code == 200, f"Failed: {send_response.text}"
        
        send_data = send_response.json()
        assert send_data.get("success") == True
        assert "message" in send_data
        print(f"✓ Message sent successfully")
        
        # Get messages
        get_response = requests.get(f"{BASE_URL}/api/attorney-stream/messages/{stream_code}")
        assert get_response.status_code == 200, f"Failed: {get_response.text}"
        
        get_data = get_response.json()
        assert get_data.get("success") == True
        assert "messages" in get_data
        assert len(get_data["messages"]) >= 1
        print(f"✓ Retrieved {get_data['count']} messages")
    
    def test_end_stream(self, auth_headers, test_encounter):
        """POST /api/attorney-stream/end/{stream_code} - ends stream session"""
        if not test_encounter:
            pytest.skip("No test encounter available")
        
        # Create a stream
        create_response = requests.post(
            f"{BASE_URL}/api/attorney-stream/create",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter["encounter_id"]
            }
        )
        assert create_response.status_code == 200
        stream_data = create_response.json()
        stream_code = stream_data["stream_code"]
        
        # End the stream
        response = requests.post(
            f"{BASE_URL}/api/attorney-stream/end/{stream_code}",
            params={"ended_by": "user"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert data.get("status") == "ended"
        print(f"✓ Stream ended successfully")
    
    def test_stream_history(self, auth_headers):
        """GET /api/attorney-stream/history - returns user's stream history"""
        response = requests.get(
            f"{BASE_URL}/api/attorney-stream/history",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True
        assert "streams" in data
        assert "count" in data
        print(f"✓ Stream history returned {data['count']} records")
    
    def test_signaling_endpoints(self, auth_headers, test_encounter):
        """Test WebRTC signaling endpoints"""
        if not test_encounter:
            pytest.skip("No test encounter available")
        
        # Create a stream
        create_response = requests.post(
            f"{BASE_URL}/api/attorney-stream/create",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter["encounter_id"]
            }
        )
        assert create_response.status_code == 200
        stream_data = create_response.json()
        stream_code = stream_data["stream_code"]
        
        # Send signaling data (offer)
        signal_response = requests.post(
            f"{BASE_URL}/api/attorney-stream/signal",
            json={
                "stream_code": stream_code,
                "signal_type": "offer",
                "data": {"sdp": "test_sdp_offer", "type": "offer"},
                "sender_role": "user"
            }
        )
        assert signal_response.status_code == 200, f"Failed: {signal_response.text}"
        print("✓ Signaling offer sent")
        
        # Get signaling data for attorney
        get_signal_response = requests.get(
            f"{BASE_URL}/api/attorney-stream/signal/{stream_code}/attorney"
        )
        assert get_signal_response.status_code == 200, f"Failed: {get_signal_response.text}"
        
        signal_data = get_signal_response.json()
        assert signal_data.get("success") == True
        assert "offers" in signal_data
        print(f"✓ Signaling data retrieved for attorney")


class TestFrontendIntegration:
    """Test that frontend API functions match backend endpoints"""
    
    def test_api_url_configured(self):
        """Verify API URL is properly configured"""
        assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
        assert BASE_URL.startswith("http"), "BASE_URL must be a valid URL"
        print(f"✓ API URL configured: {BASE_URL}")
    
    def test_multicloud_backup_api_endpoints_exist(self):
        """Verify all multiCloudBackupAPI endpoints exist"""
        endpoints = [
            ("GET", "/api/backup/providers"),
            ("GET", "/api/backup/status/test_id"),
            ("GET", "/api/backup/history"),
        ]
        
        # Get auth token first
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        token = login_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            else:
                response = requests.post(f"{BASE_URL}{endpoint}", headers=headers)
            
            # Should not return 404 (endpoint exists)
            assert response.status_code != 404, f"Endpoint {method} {endpoint} not found"
            print(f"✓ {method} {endpoint} exists")
    
    def test_attorney_stream_api_endpoints_exist(self):
        """Verify all attorneyStreamAPI endpoints exist"""
        # Get auth token first
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        token = login_response.json().get("token")
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test endpoints that don't require specific data
        get_endpoints = [
            "/api/attorney-stream/history",
        ]
        
        for endpoint in get_endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            assert response.status_code != 404, f"Endpoint GET {endpoint} not found"
            print(f"✓ GET {endpoint} exists")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
