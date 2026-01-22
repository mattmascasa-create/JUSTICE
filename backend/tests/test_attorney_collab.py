"""
Attorney Collaboration Feature Tests
Tests for attorney invitation, acceptance, dashboard, notes, and messaging.
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test data
TEST_CITIZEN_EMAIL = "attorney_test@example.com"
TEST_CITIZEN_PASSWORD = "password123"
TEST_ATTORNEY_EMAIL = "my_attorney@lawfirm.com"
TEST_ATTORNEY_PASSWORD = "attorney123"
TEST_ENCOUNTER_ID = "enc_d198bfaa9c06"


class TestHealthEndpoint:
    """Verify API is running"""
    
    def test_health_check(self):
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Health check passed - Version: {data.get('version')}")


class TestCitizenLogin:
    """Test citizen login to get auth token"""
    
    def test_citizen_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_CITIZEN_EMAIL,
            "password": TEST_CITIZEN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == TEST_CITIZEN_EMAIL
        print(f"✓ Citizen login successful - User: {data['user']['name']}")
        return data["access_token"]


class TestAttorneyLogin:
    """Test attorney login to get auth token"""
    
    def test_attorney_login(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_ATTORNEY_EMAIL,
            "password": TEST_ATTORNEY_PASSWORD
        })
        assert response.status_code == 200, f"Attorney login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "attorney"
        print(f"✓ Attorney login successful - User: {data['user']['name']}, Role: {data['user']['role']}")
        return data["access_token"]


class TestAttorneyInvitation:
    """Test attorney invitation flow"""
    
    @pytest.fixture
    def citizen_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_CITIZEN_EMAIL,
            "password": TEST_CITIZEN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Citizen login failed")
        return response.json()["access_token"]
    
    def test_invite_attorney(self, citizen_token):
        """Test POST /api/attorney/invite"""
        # Generate unique email to avoid duplicate invite error
        unique_email = f"test_attorney_{uuid.uuid4().hex[:8]}@lawfirm.com"
        
        response = requests.post(
            f"{BASE_URL}/api/attorney/invite",
            headers={"Authorization": f"Bearer {citizen_token}"},
            data={
                "email": unique_email,
                "encounter_id": TEST_ENCOUNTER_ID,
                "message": "Please review my encounter"
            }
        )
        
        # Could be 200 (success) or 404 (encounter not found for this user)
        if response.status_code == 404:
            print(f"⚠ Encounter {TEST_ENCOUNTER_ID} not found for test user - skipping invite test")
            pytest.skip("Test encounter not owned by test user")
        
        assert response.status_code == 200, f"Invite failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert "invite_url" in data
        assert "invite_id" in data
        print(f"✓ Attorney invitation sent - Invite ID: {data['invite_id']}")
        return data
    
    def test_invite_duplicate_rejected(self, citizen_token):
        """Test that duplicate invites are rejected"""
        # First invite
        response1 = requests.post(
            f"{BASE_URL}/api/attorney/invite",
            headers={"Authorization": f"Bearer {citizen_token}"},
            data={
                "email": "duplicate_test@lawfirm.com",
                "encounter_id": TEST_ENCOUNTER_ID
            }
        )
        
        if response1.status_code == 404:
            pytest.skip("Test encounter not owned by test user")
        
        # Second invite to same email
        response2 = requests.post(
            f"{BASE_URL}/api/attorney/invite",
            headers={"Authorization": f"Bearer {citizen_token}"},
            data={
                "email": "duplicate_test@lawfirm.com",
                "encounter_id": TEST_ENCOUNTER_ID
            }
        )
        
        assert response2.status_code == 400
        assert "already sent" in response2.json()["detail"].lower()
        print("✓ Duplicate invite correctly rejected")


class TestInviteDetails:
    """Test public invite details endpoint"""
    
    def test_invalid_token_returns_404(self):
        """Test GET /api/attorney/invite/{token}/details with invalid token"""
        response = requests.get(f"{BASE_URL}/api/attorney/invite/invalid_token_12345/details")
        assert response.status_code == 404
        print("✓ Invalid invite token returns 404")


class TestAttorneyDashboard:
    """Test attorney dashboard endpoints"""
    
    @pytest.fixture
    def attorney_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_ATTORNEY_EMAIL,
            "password": TEST_ATTORNEY_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Attorney login failed")
        return response.json()["access_token"]
    
    def test_get_dashboard(self, attorney_token):
        """Test GET /api/attorney/dashboard"""
        response = requests.get(
            f"{BASE_URL}/api/attorney/dashboard",
            headers={"Authorization": f"Bearer {attorney_token}"}
        )
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "attorney_id" in data
        assert "stats" in data
        assert "clients" in data
        assert "total_clients" in data["stats"]
        assert "total_encounters" in data["stats"]
        assert "unread_messages" in data["stats"]
        
        print(f"✓ Attorney dashboard loaded - Clients: {data['stats']['total_clients']}, Encounters: {data['stats']['total_encounters']}")
        return data
    
    def test_dashboard_requires_attorney_role(self):
        """Test that non-attorneys get 403"""
        # Login as citizen
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_CITIZEN_EMAIL,
            "password": TEST_CITIZEN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Citizen login failed")
        
        citizen_token = response.json()["access_token"]
        
        # Try to access attorney dashboard
        response = requests.get(
            f"{BASE_URL}/api/attorney/dashboard",
            headers={"Authorization": f"Bearer {citizen_token}"}
        )
        assert response.status_code == 403
        print("✓ Non-attorney correctly denied access to dashboard")
    
    def test_get_clients(self, attorney_token):
        """Test GET /api/attorney/clients"""
        response = requests.get(
            f"{BASE_URL}/api/attorney/clients",
            headers={"Authorization": f"Bearer {attorney_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "clients" in data
        print(f"✓ Attorney clients list loaded - Count: {len(data['clients'])}")
    
    def test_get_encounters(self, attorney_token):
        """Test GET /api/attorney/encounters"""
        response = requests.get(
            f"{BASE_URL}/api/attorney/encounters",
            headers={"Authorization": f"Bearer {attorney_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "encounters" in data
        print(f"✓ Attorney encounters list loaded - Count: {len(data['encounters'])}")


class TestAttorneyVerification:
    """Test attorney verification endpoint"""
    
    @pytest.fixture
    def attorney_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_ATTORNEY_EMAIL,
            "password": TEST_ATTORNEY_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Attorney login failed")
        return response.json()["access_token"]
    
    def test_verify_attorney(self, attorney_token):
        """Test POST /api/attorney/verify"""
        response = requests.post(
            f"{BASE_URL}/api/attorney/verify",
            headers={"Authorization": f"Bearer {attorney_token}"},
            data={
                "bar_number": "CA123456",
                "firm_name": "Test Law Firm",
                "specialization": "Civil Rights"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["verified"] == True
        print("✓ Attorney verification successful")


class TestCaseNotes:
    """Test case notes CRUD operations"""
    
    @pytest.fixture
    def attorney_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_ATTORNEY_EMAIL,
            "password": TEST_ATTORNEY_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Attorney login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def encounter_id(self, attorney_token):
        """Get an encounter the attorney has access to"""
        response = requests.get(
            f"{BASE_URL}/api/attorney/encounters",
            headers={"Authorization": f"Bearer {attorney_token}"}
        )
        if response.status_code != 200:
            pytest.skip("Failed to get encounters")
        
        encounters = response.json().get("encounters", [])
        if not encounters:
            pytest.skip("Attorney has no encounters to test with")
        
        return encounters[0]["encounter_id"]
    
    def test_create_note(self, attorney_token, encounter_id):
        """Test POST /api/attorney/notes"""
        response = requests.post(
            f"{BASE_URL}/api/attorney/notes",
            headers={"Authorization": f"Bearer {attorney_token}"},
            data={
                "encounter_id": encounter_id,
                "content": "Test legal analysis note",
                "note_type": "legal_analysis"
            }
        )
        assert response.status_code == 200, f"Create note failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert "note_id" in data
        print(f"✓ Case note created - Note ID: {data['note_id']}")
        return data["note_id"]
    
    def test_get_notes(self, attorney_token, encounter_id):
        """Test GET /api/attorney/notes/{encounter_id}"""
        response = requests.get(
            f"{BASE_URL}/api/attorney/notes/{encounter_id}",
            headers={"Authorization": f"Bearer {attorney_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "notes" in data
        print(f"✓ Case notes retrieved - Count: {len(data['notes'])}")
    
    def test_update_note(self, attorney_token, encounter_id):
        """Test PUT /api/attorney/notes/{note_id}"""
        # First create a note
        create_response = requests.post(
            f"{BASE_URL}/api/attorney/notes",
            headers={"Authorization": f"Bearer {attorney_token}"},
            data={
                "encounter_id": encounter_id,
                "content": "Original content",
                "note_type": "general"
            }
        )
        if create_response.status_code != 200:
            pytest.skip("Failed to create note for update test")
        
        note_id = create_response.json()["note_id"]
        
        # Update the note
        response = requests.put(
            f"{BASE_URL}/api/attorney/notes/{note_id}",
            headers={"Authorization": f"Bearer {attorney_token}"},
            data={
                "content": "Updated content",
                "note_type": "strategy"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✓ Case note updated - Note ID: {note_id}")
    
    def test_delete_note(self, attorney_token, encounter_id):
        """Test DELETE /api/attorney/notes/{note_id}"""
        # First create a note
        create_response = requests.post(
            f"{BASE_URL}/api/attorney/notes",
            headers={"Authorization": f"Bearer {attorney_token}"},
            data={
                "encounter_id": encounter_id,
                "content": "Note to delete",
                "note_type": "general"
            }
        )
        if create_response.status_code != 200:
            pytest.skip("Failed to create note for delete test")
        
        note_id = create_response.json()["note_id"]
        
        # Delete the note
        response = requests.delete(
            f"{BASE_URL}/api/attorney/notes/{note_id}",
            headers={"Authorization": f"Bearer {attorney_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print(f"✓ Case note deleted - Note ID: {note_id}")


class TestMessaging:
    """Test attorney-client messaging"""
    
    @pytest.fixture
    def attorney_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_ATTORNEY_EMAIL,
            "password": TEST_ATTORNEY_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Attorney login failed")
        return response.json()["access_token"]
    
    @pytest.fixture
    def client_id(self, attorney_token):
        """Get a client ID the attorney has access to"""
        response = requests.get(
            f"{BASE_URL}/api/attorney/clients",
            headers={"Authorization": f"Bearer {attorney_token}"}
        )
        if response.status_code != 200:
            pytest.skip("Failed to get clients")
        
        clients = response.json().get("clients", [])
        if not clients:
            pytest.skip("Attorney has no clients to test with")
        
        return clients[0]["client_id"]
    
    def test_send_message(self, attorney_token, client_id):
        """Test POST /api/attorney/messages"""
        response = requests.post(
            f"{BASE_URL}/api/attorney/messages",
            headers={"Authorization": f"Bearer {attorney_token}"},
            data={
                "recipient_id": client_id,
                "content": "Test message from attorney",
                "message_type": "text"
            }
        )
        assert response.status_code == 200, f"Send message failed: {response.text}"
        data = response.json()
        assert data["success"] == True
        assert "message_id" in data
        print(f"✓ Message sent - Message ID: {data['message_id']}")
    
    def test_get_inbox(self, attorney_token):
        """Test GET /api/attorney/messages/inbox"""
        response = requests.get(
            f"{BASE_URL}/api/attorney/messages/inbox",
            headers={"Authorization": f"Bearer {attorney_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        print(f"✓ Inbox retrieved - Conversations: {len(data['conversations'])}")
    
    def test_get_messages_with_contact(self, attorney_token, client_id):
        """Test GET /api/attorney/messages with contact_id"""
        response = requests.get(
            f"{BASE_URL}/api/attorney/messages",
            headers={"Authorization": f"Bearer {attorney_token}"},
            params={"contact_id": client_id}
        )
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        print(f"✓ Messages with contact retrieved - Count: {len(data['messages'])}")


class TestClientEndpoints:
    """Test client-side attorney management endpoints"""
    
    @pytest.fixture
    def citizen_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_CITIZEN_EMAIL,
            "password": TEST_CITIZEN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Citizen login failed")
        return response.json()["access_token"]
    
    def test_get_my_attorneys(self, citizen_token):
        """Test GET /api/attorney/my-attorneys"""
        response = requests.get(
            f"{BASE_URL}/api/attorney/my-attorneys",
            headers={"Authorization": f"Bearer {citizen_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "attorneys" in data
        print(f"✓ My attorneys list retrieved - Count: {len(data['attorneys'])}")


class TestAccessRevocation:
    """Test attorney access revocation"""
    
    @pytest.fixture
    def citizen_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_CITIZEN_EMAIL,
            "password": TEST_CITIZEN_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Citizen login failed")
        return response.json()["access_token"]
    
    def test_revoke_access_invalid_encounter(self, citizen_token):
        """Test DELETE /api/attorney/access/{encounter_id} with invalid encounter"""
        response = requests.delete(
            f"{BASE_URL}/api/attorney/access/invalid_encounter_id",
            headers={"Authorization": f"Bearer {citizen_token}"}
        )
        assert response.status_code == 404
        print("✓ Revoke access correctly returns 404 for invalid encounter")


class TestAcceptInviteExisting:
    """Test accept invite for existing user"""
    
    def test_accept_invite_wrong_email(self):
        """Test POST /api/attorney/accept-invite/existing with wrong email"""
        response = requests.post(
            f"{BASE_URL}/api/attorney/accept-invite/existing",
            data={
                "invite_token": "some_token",
                "email": "wrong@email.com",
                "password": "password123"
            }
        )
        # Should fail - either 404 (token not found) or 400 (email mismatch)
        assert response.status_code in [400, 404]
        print("✓ Accept invite with wrong email correctly rejected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
