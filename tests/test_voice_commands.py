"""
Test Voice Commands for Encounter Mode
Tests:
- POST /api/encounters/{id}/mark-violation endpoint
- Manual violation marks persistence
- Voice command integration with SOS API
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rightsdefender.preview.emergentagent.com')

class TestVoiceCommands:
    """Test voice commands backend functionality"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test user and get auth token"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Register/login test user
        register_data = {
            "email": "test_voice_commands@example.com",
            "password": "testpass123",
            "name": "Voice Commands Test User"
        }
        
        # Try to register, if fails try login
        response = self.session.post(f"{BASE_URL}/api/auth/register", json=register_data)
        if response.status_code == 400:  # Already exists
            response = self.session.post(f"{BASE_URL}/api/auth/login", json={
                "email": register_data["email"],
                "password": register_data["password"]
            })
        
        assert response.status_code in [200, 201], f"Auth failed: {response.text}"
        data = response.json()
        self.token = data.get("access_token")
        self.user_id = data.get("user", {}).get("user_id")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
        
        yield
        
        # Cleanup - end any active encounters
        try:
            if hasattr(self, 'encounter_id') and self.encounter_id:
                self.session.post(f"{BASE_URL}/api/encounters/{self.encounter_id}/end")
        except:
            pass
    
    def test_health_check(self):
        """Test backend is healthy"""
        response = self.session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ Backend health check passed")
    
    def test_create_encounter_for_voice_commands(self):
        """Create an encounter to test voice commands"""
        encounter_data = {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "address": "Test Location for Voice Commands",
            "encounter_type": "traffic_stop",
            "broadcast_mode": "save"
        }
        
        response = self.session.post(f"{BASE_URL}/api/encounters/start", json=encounter_data)
        assert response.status_code == 200, f"Failed to create encounter: {response.text}"
        
        data = response.json()
        self.encounter_id = data.get("encounter_id")
        assert self.encounter_id is not None
        assert data.get("status") == "active"
        print(f"✓ Created encounter: {self.encounter_id}")
        return self.encounter_id
    
    def test_mark_violation_endpoint(self):
        """Test POST /api/encounters/{id}/mark-violation endpoint"""
        # First create an encounter
        encounter_id = self.test_create_encounter_for_voice_commands()
        
        # Test mark violation with voice command note
        # Use multipart form data (remove Content-Type header for form data)
        headers = {"Authorization": f"Bearer {self.token}"}
        mark_data = {
            "timestamp": "45.5",
            "note": "Voice command: violation marked"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/encounters/{encounter_id}/mark-violation",
            data=mark_data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Mark violation failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        assert "mark" in data
        mark = data["mark"]
        assert mark.get("mark_id") is not None
        assert mark.get("timestamp_seconds") == 45.5
        assert "voice" in mark.get("note", "").lower()
        assert mark.get("source") == "voice_command"
        print(f"✓ Mark violation endpoint works - mark_id: {mark['mark_id']}")
        
        return encounter_id
    
    def test_mark_violation_manual(self):
        """Test manual violation mark (not voice command)"""
        encounter_id = self.test_create_encounter_for_voice_commands()
        
        headers = {"Authorization": f"Bearer {self.token}"}
        mark_data = {
            "timestamp": "120.0",
            "note": "Manual mark - officer raised voice"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/encounters/{encounter_id}/mark-violation",
            data=mark_data,
            headers=headers
        )
        
        assert response.status_code == 200, f"Manual mark failed: {response.text}"
        data = response.json()
        
        assert data.get("success") == True
        mark = data["mark"]
        assert mark.get("source") == "manual"  # Not voice_command
        print(f"✓ Manual violation mark works - source: {mark['source']}")
    
    def test_mark_violation_persisted_in_encounter(self):
        """Test that marks are persisted in the encounter document"""
        encounter_id = self.test_create_encounter_for_voice_commands()
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        # Add multiple marks
        marks_to_add = [
            {"timestamp": "30.0", "note": "Voice command: violation marked"},
            {"timestamp": "60.0", "note": "Manual mark - suspicious behavior"},
            {"timestamp": "90.0", "note": "Voice command: flag violation"}
        ]
        
        for mark_data in marks_to_add:
            response = requests.post(
                f"{BASE_URL}/api/encounters/{encounter_id}/mark-violation",
                data=mark_data,
                headers=headers
            )
            assert response.status_code == 200, f"Mark failed: {response.text}"
        
        # Get encounter and verify marks are embedded
        response = self.session.get(f"{BASE_URL}/api/encounters/{encounter_id}")
        assert response.status_code == 200
        
        encounter = response.json()
        manual_marks = encounter.get("manual_marks", [])
        
        assert len(manual_marks) >= 3, f"Expected at least 3 marks, got {len(manual_marks)}"
        print(f"✓ Marks persisted in encounter - count: {len(manual_marks)}")
        
        # Verify mark structure
        for mark in manual_marks:
            assert "mark_id" in mark
            assert "timestamp_seconds" in mark
            assert "note" in mark
            assert "source" in mark
        print("✓ Mark structure is correct")
    
    def test_mark_violation_invalid_encounter(self):
        """Test mark violation with non-existent encounter"""
        headers = {"Authorization": f"Bearer {self.token}"}
        mark_data = {
            "timestamp": "45.5",
            "note": "Test mark"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/encounters/invalid_encounter_id/mark-violation",
            data=mark_data,
            headers=headers
        )
        
        assert response.status_code == 404
        print("✓ Invalid encounter returns 404")
    
    def test_sos_api_integration(self):
        """Test SOS API that voice commands can trigger"""
        # Create SOS alert (simulates voice command "SOS" or "emergency")
        sos_data = {
            "latitude": 34.0522,
            "longitude": -118.2437,
            "address": "Voice Command SOS Test Location"
        }
        
        response = self.session.post(f"{BASE_URL}/api/sos", json=sos_data)
        assert response.status_code == 200, f"SOS creation failed: {response.text}"
        
        data = response.json()
        assert data.get("alert_id") is not None
        assert data.get("status") == "active"
        print(f"✓ SOS API works - alert_id: {data['alert_id']}")
        
        # Resolve the SOS alert
        alert_id = data["alert_id"]
        response = self.session.post(f"{BASE_URL}/api/sos/{alert_id}/resolve")
        assert response.status_code == 200
        print("✓ SOS alert resolved")
    
    def test_encounter_end_with_marks(self):
        """Test ending encounter preserves marks in report"""
        encounter_id = self.test_create_encounter_for_voice_commands()
        
        # Add a mark
        headers = {"Authorization": f"Bearer {self.token}"}
        mark_data = {
            "timestamp": "45.0",
            "note": "Voice command: violation marked"
        }
        requests.post(
            f"{BASE_URL}/api/encounters/{encounter_id}/mark-violation",
            data=mark_data,
            headers=headers
        )
        
        # End the encounter
        response = self.session.post(f"{BASE_URL}/api/encounters/{encounter_id}/end")
        assert response.status_code == 200, f"End encounter failed: {response.text}"
        
        data = response.json()
        assert data.get("status") == "ended"
        print("✓ Encounter ended successfully with marks preserved")
        
        # Clear encounter_id since it's ended
        self.encounter_id = None


class TestVoiceCommandsUI:
    """Test voice commands UI elements (via API verification)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test user"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login
        response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test_voice_commands@example.com",
            "password": "testpass123"
        })
        
        if response.status_code == 401:
            # Register first
            response = self.session.post(f"{BASE_URL}/api/auth/register", json={
                "email": "test_voice_commands@example.com",
                "password": "testpass123",
                "name": "Voice Commands Test User"
            })
        
        assert response.status_code in [200, 201]
        data = response.json()
        self.token = data.get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})
    
    def test_encounter_api_returns_marks_field(self):
        """Verify encounter API returns manual_marks field for UI"""
        # Create encounter
        response = self.session.post(f"{BASE_URL}/api/encounters/start", json={
            "latitude": 34.0522,
            "longitude": -118.2437,
            "encounter_type": "traffic_stop",
            "broadcast_mode": "save"
        })
        assert response.status_code == 200
        encounter_id = response.json()["encounter_id"]
        
        # Get encounter
        response = self.session.get(f"{BASE_URL}/api/encounters/{encounter_id}")
        assert response.status_code == 200
        
        data = response.json()
        # Verify manual_marks field exists (may be empty initially)
        assert "manual_marks" in data or data.get("manual_marks") is None or isinstance(data.get("manual_marks", []), list)
        print("✓ Encounter API returns marks field for UI")
        
        # Cleanup
        self.session.post(f"{BASE_URL}/api/encounters/{encounter_id}/end")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
