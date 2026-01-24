"""
Real-time Encounter Sharing Tests
Tests for the new real-time sharing feature (v5.3.0)
- Create share link API
- Get shared encounter data
- Send guidance message API
- Revoke share link API
- Get shared updates polling endpoint
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://legal-shield-11.preview.emergentagent.com')

class TestHealthEndpoint:
    """Test health endpoint shows new features"""
    
    def test_health_shows_new_features(self):
        """Health endpoint should show real_time_sharing and live_guidance features"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "5.3.0"
        assert "features" in data
        assert data["features"]["real_time_sharing"] == True
        assert data["features"]["live_guidance"] == True
        print("✓ Health endpoint shows new features (real_time_sharing, live_guidance)")


class TestSharedEncounterPublicEndpoints:
    """Test public endpoints for shared encounter viewing"""
    
    # Using the pre-existing test encounter
    TEST_ENCOUNTER_ID = "enc_e6692f1e966b"
    TEST_SHARE_TOKEN = "adbe232a15954e11"
    
    def test_get_shared_encounter_valid_token(self):
        """Get shared encounter data with valid token"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{self.TEST_ENCOUNTER_ID}?token={self.TEST_SHARE_TOKEN}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["encounter_id"] == self.TEST_ENCOUNTER_ID
        assert "owner_name" in data
        assert "status" in data
        assert "location" in data
        assert "transcriptions" in data
        assert "guidance_messages" in data
        assert data["share_active"] == True
        print(f"✓ Get shared encounter works - owner: {data['owner_name']}, status: {data['status']}")
    
    def test_get_shared_encounter_invalid_token(self):
        """Get shared encounter with invalid token should return 403"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{self.TEST_ENCOUNTER_ID}?token=invalid_token_12345"
        )
        assert response.status_code == 403
        
        data = response.json()
        assert "Invalid or expired share link" in data["detail"]
        print("✓ Invalid token correctly rejected with 403")
    
    def test_get_shared_encounter_nonexistent(self):
        """Get shared encounter for non-existent encounter should return 404"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/enc_nonexistent123?token=sometoken"
        )
        assert response.status_code == 404
        print("✓ Non-existent encounter correctly returns 404")
    
    def test_get_shared_updates(self):
        """Get shared updates polling endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{self.TEST_ENCOUNTER_ID}/updates?token={self.TEST_SHARE_TOKEN}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "transcriptions" in data
        assert "messages" in data
        assert "timestamp" in data
        print(f"✓ Get shared updates works - status: {data['status']}, messages: {len(data['messages'])}")
    
    def test_send_guidance_message(self):
        """Send guidance message to shared encounter"""
        test_message = f"Test guidance message {uuid.uuid4().hex[:8]}"
        sender_name = "Test Sender"
        
        response = requests.post(
            f"{BASE_URL}/api/encounters/shared/{self.TEST_ENCOUNTER_ID}/message",
            params={
                "token": self.TEST_SHARE_TOKEN,
                "message": test_message,
                "sender_name": sender_name
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "message_id" in data
        assert "timestamp" in data
        print(f"✓ Send guidance message works - message_id: {data['message_id']}")
    
    def test_send_guidance_message_too_long(self):
        """Send guidance message that exceeds 200 characters should fail"""
        long_message = "x" * 250  # 250 characters
        
        response = requests.post(
            f"{BASE_URL}/api/encounters/shared/{self.TEST_ENCOUNTER_ID}/message",
            params={
                "token": self.TEST_SHARE_TOKEN,
                "message": long_message,
                "sender_name": "Test"
            }
        )
        assert response.status_code == 400
        
        data = response.json()
        assert "too long" in data["detail"].lower()
        print("✓ Long message correctly rejected with 400")
    
    def test_send_guidance_message_invalid_token(self):
        """Send guidance message with invalid token should fail"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/shared/{self.TEST_ENCOUNTER_ID}/message",
            params={
                "token": "invalid_token",
                "message": "Test message",
                "sender_name": "Test"
            }
        )
        assert response.status_code == 403
        print("✓ Guidance message with invalid token correctly rejected")


class TestShareLinkManagement:
    """Test authenticated share link management endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login and get auth token"""
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "modtest2@test.com", "password": "Test123!"}
        )
        if login_response.status_code != 200:
            pytest.skip("Could not authenticate - skipping authenticated tests")
        
        self.token = login_response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create a test encounter
        encounter_response = requests.post(
            f"{BASE_URL}/api/encounters/start",
            headers=self.headers,
            json={
                "latitude": 40.7128,
                "longitude": -74.006,
                "address": f"Test Location {uuid.uuid4().hex[:8]}",
                "encounter_type": "traffic_stop",
                "broadcast_mode": "save"
            }
        )
        if encounter_response.status_code == 200:
            self.test_encounter_id = encounter_response.json()["encounter_id"]
        else:
            pytest.skip("Could not create test encounter")
    
    def test_create_share_link(self):
        """Create a share link for an encounter"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/{self.test_encounter_id}/share?auto_notify=false",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "share_token" in data
        assert "share_url" in data
        assert "expires_at" in data
        assert len(data["share_token"]) == 16
        print(f"✓ Create share link works - token: {data['share_token'][:8]}...")
        
        # Store for later tests
        self.share_token = data["share_token"]
    
    def test_create_share_link_with_auto_notify(self):
        """Create a share link with auto-notify enabled"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/{self.test_encounter_id}/share?auto_notify=true",
            headers=self.headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] == True
        assert "notified_contacts" in data
        print(f"✓ Create share link with auto_notify works - notified: {len(data['notified_contacts'])} contacts")
    
    def test_revoke_share_link(self):
        """Revoke a share link"""
        # First create a share link
        create_response = requests.post(
            f"{BASE_URL}/api/encounters/{self.test_encounter_id}/share?auto_notify=false",
            headers=self.headers
        )
        assert create_response.status_code == 200
        share_token = create_response.json()["share_token"]
        
        # Verify it works
        verify_response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{self.test_encounter_id}?token={share_token}"
        )
        assert verify_response.status_code == 200
        
        # Revoke it
        revoke_response = requests.delete(
            f"{BASE_URL}/api/encounters/{self.test_encounter_id}/share",
            headers=self.headers
        )
        assert revoke_response.status_code == 200
        
        data = revoke_response.json()
        assert data["success"] == True
        assert "revoked" in data["message"].lower()
        print("✓ Revoke share link works")
        
        # Verify it no longer works
        verify_after_response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{self.test_encounter_id}?token={share_token}"
        )
        assert verify_after_response.status_code == 403
        print("✓ Share link correctly invalid after revocation")
    
    def test_create_share_link_unauthorized(self):
        """Create share link without auth should fail"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/{self.test_encounter_id}/share?auto_notify=false"
        )
        assert response.status_code in [401, 403]
        print("✓ Unauthorized share link creation correctly rejected")
    
    def test_create_share_link_nonexistent_encounter(self):
        """Create share link for non-existent encounter should fail"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/enc_nonexistent123/share?auto_notify=false",
            headers=self.headers
        )
        assert response.status_code == 404
        print("✓ Share link for non-existent encounter correctly returns 404")


class TestGuidanceMessageFlow:
    """Test the complete guidance message flow"""
    
    TEST_ENCOUNTER_ID = "enc_e6692f1e966b"
    TEST_SHARE_TOKEN = "adbe232a15954e11"
    
    def test_guidance_message_appears_in_updates(self):
        """Send a message and verify it appears in updates"""
        # Send a unique message
        unique_id = uuid.uuid4().hex[:8]
        test_message = f"Guidance test {unique_id}"
        
        # Send the message
        send_response = requests.post(
            f"{BASE_URL}/api/encounters/shared/{self.TEST_ENCOUNTER_ID}/message",
            params={
                "token": self.TEST_SHARE_TOKEN,
                "message": test_message,
                "sender_name": "Test Flow"
            }
        )
        assert send_response.status_code == 200
        message_id = send_response.json()["message_id"]
        
        # Get updates and verify message is there
        updates_response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{self.TEST_ENCOUNTER_ID}/updates?token={self.TEST_SHARE_TOKEN}"
        )
        assert updates_response.status_code == 200
        
        messages = updates_response.json()["messages"]
        message_ids = [m["message_id"] for m in messages]
        assert message_id in message_ids
        print(f"✓ Guidance message flow works - message {message_id} found in updates")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
