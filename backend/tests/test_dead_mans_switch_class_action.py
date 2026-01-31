"""
Test Dead Man's Switch, Class Action Finder, and Voice Commands APIs
Testing iteration 44 - Three new safety-critical features
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"


class TestAuthentication:
    """Authentication tests - required for all other tests"""
    
    def test_login_success(self):
        """Test admin login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "access_token" in data, "No access_token in response"
        return data["access_token"]


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token for tests"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {"Authorization": f"Bearer {auth_token}"}


# ============== DEAD MAN'S SWITCH TESTS ==============

class TestDeadMansSwitchConfig:
    """Dead Man's Switch Configuration API tests"""
    
    def test_get_config(self, auth_headers):
        """GET /api/dead-mans-switch/config - Get configuration"""
        response = requests.get(
            f"{BASE_URL}/api/dead-mans-switch/config",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # Verify config structure
        assert "enabled" in data
        assert "check_in_interval_minutes" in data
        assert "grace_period_minutes" in data
        print(f"✓ Config retrieved: enabled={data.get('enabled')}, interval={data.get('check_in_interval_minutes')}min")
    
    def test_get_config_requires_auth(self):
        """GET /api/dead-mans-switch/config - Requires authentication"""
        response = requests.get(f"{BASE_URL}/api/dead-mans-switch/config")
        assert response.status_code == 401, "Should require authentication"
        print("✓ Config endpoint requires authentication")
    
    def test_update_config(self, auth_headers):
        """PUT /api/dead-mans-switch/config - Update configuration"""
        config = {
            "enabled": True,
            "check_in_interval_minutes": 20,
            "grace_period_minutes": 5,
            "auto_publish_to_contacts": True,
            "auto_publish_to_cloud": True,
            "auto_notify_attorney": True,
            "auto_call_emergency": False
        }
        response = requests.put(
            f"{BASE_URL}/api/dead-mans-switch/config",
            headers=auth_headers,
            json=config
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print("✓ Config updated successfully")
        
        # Verify update persisted
        get_response = requests.get(
            f"{BASE_URL}/api/dead-mans-switch/config",
            headers=auth_headers
        )
        assert get_response.status_code == 200
        updated_config = get_response.json()
        assert updated_config.get("check_in_interval_minutes") == 20
        print("✓ Config update verified via GET")


class TestDeadMansSwitchContacts:
    """Dead Man's Switch Trusted Contacts API tests"""
    
    def test_get_contacts(self, auth_headers):
        """GET /api/dead-mans-switch/contacts - Get trusted contacts"""
        response = requests.get(
            f"{BASE_URL}/api/dead-mans-switch/contacts",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "contacts" in data
        print(f"✓ Retrieved {len(data.get('contacts', []))} trusted contacts")
    
    def test_add_contact(self, auth_headers):
        """POST /api/dead-mans-switch/contacts - Add trusted contact"""
        contact = {
            "name": "TEST_Emergency_Contact",
            "email": "test_emergency@example.com",
            "phone": "+15551234567",
            "relationship": "emergency_contact",
            "notify_methods": ["email", "sms"]
        }
        response = requests.post(
            f"{BASE_URL}/api/dead-mans-switch/contacts",
            headers=auth_headers,
            json=contact
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "contact_id" in data
        print(f"✓ Contact added: {data.get('contact_id')}")
        return data.get("contact_id")
    
    def test_add_contact_requires_auth(self):
        """POST /api/dead-mans-switch/contacts - Requires authentication"""
        contact = {
            "name": "Test",
            "email": "test@example.com",
            "relationship": "friend"
        }
        response = requests.post(
            f"{BASE_URL}/api/dead-mans-switch/contacts",
            json=contact
        )
        assert response.status_code == 401, "Should require authentication"
        print("✓ Add contact requires authentication")
    
    def test_add_and_remove_contact(self, auth_headers):
        """POST then DELETE /api/dead-mans-switch/contacts - Full CRUD"""
        # Add contact
        contact = {
            "name": "TEST_Delete_Contact",
            "email": "test_delete@example.com",
            "relationship": "friend",
            "notify_methods": ["email"]
        }
        add_response = requests.post(
            f"{BASE_URL}/api/dead-mans-switch/contacts",
            headers=auth_headers,
            json=contact
        )
        assert add_response.status_code == 200
        contact_id = add_response.json().get("contact_id")
        print(f"✓ Contact created: {contact_id}")
        
        # Delete contact
        delete_response = requests.delete(
            f"{BASE_URL}/api/dead-mans-switch/contacts/{contact_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200, f"Delete failed: {delete_response.text}"
        assert delete_response.json().get("success") == True
        print(f"✓ Contact deleted: {contact_id}")


class TestDeadMansSwitchCheckIn:
    """Dead Man's Switch Check-in API tests"""
    
    def test_check_in(self, auth_headers):
        """POST /api/dead-mans-switch/check-in - User check-in"""
        response = requests.post(
            f"{BASE_URL}/api/dead-mans-switch/check-in",
            headers=auth_headers,
            json={"status": "ok"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print(f"✓ Check-in successful: {data.get('message')}")
    
    def test_check_in_with_extend(self, auth_headers):
        """POST /api/dead-mans-switch/check-in - Check-in with time extension"""
        response = requests.post(
            f"{BASE_URL}/api/dead-mans-switch/check-in",
            headers=auth_headers,
            json={"status": "extended", "extend_minutes": 30}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print(f"✓ Extended check-in: interval={data.get('interval_minutes')}min")
    
    def test_get_status(self, auth_headers):
        """GET /api/dead-mans-switch/status - Get session status"""
        response = requests.get(
            f"{BASE_URL}/api/dead-mans-switch/status",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # Status should indicate active or not
        assert "active" in data
        print(f"✓ Status retrieved: active={data.get('active')}")


class TestDeadMansSwitchSession:
    """Dead Man's Switch Session management tests"""
    
    def test_start_session(self, auth_headers):
        """POST /api/dead-mans-switch/start-session - Start session"""
        response = requests.post(
            f"{BASE_URL}/api/dead-mans-switch/start-session?encounter_id=test_encounter_123",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # May fail if no contacts configured, which is expected
        print(f"✓ Start session response: success={data.get('success')}, message={data.get('message')}")
    
    def test_end_session(self, auth_headers):
        """POST /api/dead-mans-switch/end-session - End session"""
        response = requests.post(
            f"{BASE_URL}/api/dead-mans-switch/end-session",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print(f"✓ Session ended: {data.get('message')}")


# ============== CLASS ACTION FINDER TESTS ==============

class TestClassActionStats:
    """Class Action Stats API tests"""
    
    def test_get_stats(self, auth_headers):
        """GET /api/class-action/stats - Get class action statistics"""
        response = requests.get(
            f"{BASE_URL}/api/class-action/stats",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "total_patterns_analyzed" in data
        assert "viable_class_actions" in data
        assert "total_interested_users" in data
        print(f"✓ Stats: patterns={data.get('total_patterns_analyzed')}, viable={data.get('viable_class_actions')}")
    
    def test_get_stats_requires_auth(self):
        """GET /api/class-action/stats - Requires authentication"""
        response = requests.get(f"{BASE_URL}/api/class-action/stats")
        assert response.status_code == 401, "Should require authentication"
        print("✓ Stats endpoint requires authentication")


class TestClassActionAnalyze:
    """Class Action Pattern Analysis API tests"""
    
    def test_analyze_patterns(self, auth_headers):
        """POST /api/class-action/analyze - Analyze patterns"""
        response = requests.post(
            f"{BASE_URL}/api/class-action/analyze",
            headers=auth_headers,
            json={"date_range_days": 365}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        # May return no patterns if no violations exist
        assert "success" in data
        print(f"✓ Analysis: success={data.get('success')}, similar_cases={data.get('similar_cases_found', 0)}")
    
    def test_analyze_with_violation_types(self, auth_headers):
        """POST /api/class-action/analyze - Analyze with specific violation types"""
        response = requests.post(
            f"{BASE_URL}/api/class-action/analyze",
            headers=auth_headers,
            json={
                "violation_types": ["excessive_force", "unlawful_search"],
                "date_range_days": 365
            }
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        print(f"✓ Analysis with types: pattern_strength={data.get('pattern_strength', {}).get('strength', 'N/A')}")
    
    def test_analyze_requires_auth(self):
        """POST /api/class-action/analyze - Requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/class-action/analyze",
            json={"date_range_days": 365}
        )
        assert response.status_code == 401, "Should require authentication"
        print("✓ Analyze endpoint requires authentication")


class TestClassActionPatterns:
    """Class Action Patterns API tests"""
    
    def test_get_patterns(self, auth_headers):
        """GET /api/class-action/patterns - Get active patterns"""
        response = requests.get(
            f"{BASE_URL}/api/class-action/patterns",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "patterns" in data
        print(f"✓ Retrieved {len(data.get('patterns', []))} patterns")
    
    def test_get_patterns_with_filter(self, auth_headers):
        """GET /api/class-action/patterns - With strength filter"""
        response = requests.get(
            f"{BASE_URL}/api/class-action/patterns?min_strength=strong",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        print(f"✓ Retrieved {len(data.get('patterns', []))} strong patterns")
    
    def test_get_my_patterns(self, auth_headers):
        """GET /api/class-action/my-patterns - Get user's patterns"""
        response = requests.get(
            f"{BASE_URL}/api/class-action/my-patterns",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "analyzed_patterns" in data
        assert "interested_patterns" in data
        print(f"✓ My patterns: analyzed={len(data.get('analyzed_patterns', []))}, interested={len(data.get('interested_patterns', []))}")


class TestClassActionInterest:
    """Class Action Express Interest API tests"""
    
    def test_express_interest_invalid_pattern(self, auth_headers):
        """POST /api/class-action/express-interest - Invalid pattern ID"""
        response = requests.post(
            f"{BASE_URL}/api/class-action/express-interest",
            headers=auth_headers,
            json={
                "pattern_id": "nonexistent_pattern",
                "contact_consent": True
            }
        )
        # Should return 404 for non-existent pattern
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Express interest correctly rejects invalid pattern")


# ============== VOICE COMMANDS TESTS ==============

class TestVoiceCommandsProcess:
    """Voice Commands Process API tests"""
    
    def test_process_command(self, auth_headers):
        """POST /api/voice-commands/process - Process voice command"""
        response = requests.post(
            f"{BASE_URL}/api/voice-commands/process",
            headers=auth_headers,
            json={"text": "Hey Justice, help"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "success" in data
        assert "command_recognized" in data
        print(f"✓ Command processed: recognized={data.get('command_recognized')}")
    
    def test_process_start_recording_command(self, auth_headers):
        """POST /api/voice-commands/process - Start recording command"""
        response = requests.post(
            f"{BASE_URL}/api/voice-commands/process",
            headers=auth_headers,
            json={"text": "Hey Justice, start recording"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        print(f"✓ Start recording: {data.get('command_recognized')}")
    
    def test_process_emergency_command(self, auth_headers):
        """POST /api/voice-commands/process - Emergency command"""
        response = requests.post(
            f"{BASE_URL}/api/voice-commands/process",
            headers=auth_headers,
            json={"text": "Hey Justice, emergency"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        print(f"✓ Emergency command: {data.get('command_recognized')}")
    
    def test_process_rights_command(self, auth_headers):
        """POST /api/voice-commands/process - Rights command"""
        response = requests.post(
            f"{BASE_URL}/api/voice-commands/process",
            headers=auth_headers,
            json={"text": "Hey Justice, what are my rights"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        print(f"✓ Rights command: {data.get('command_recognized')}")
    
    def test_process_short_command(self, auth_headers):
        """POST /api/voice-commands/process - Too short command"""
        response = requests.post(
            f"{BASE_URL}/api/voice-commands/process",
            headers=auth_headers,
            json={"text": "a"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("success") == False
        print("✓ Short command correctly rejected")
    
    def test_process_requires_auth(self):
        """POST /api/voice-commands/process - Requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, help"}
        )
        assert response.status_code == 401, "Should require authentication"
        print("✓ Process endpoint requires authentication")


class TestVoiceCommandsList:
    """Voice Commands List API tests"""
    
    def test_get_commands(self):
        """GET /api/voice-commands/commands - List available commands"""
        response = requests.get(f"{BASE_URL}/api/voice-commands/commands")
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "commands" in data
        assert "wake_word" in data
        print(f"✓ Retrieved {len(data.get('commands', []))} voice commands")
        print(f"  Wake word: {data.get('wake_word')}")


class TestVoiceCommandsRights:
    """Voice Commands Rights API tests"""
    
    def test_get_rights_traffic_stop(self, auth_headers):
        """GET /api/voice-commands/rights/traffic_stop - Get traffic stop rights"""
        response = requests.get(
            f"{BASE_URL}/api/voice-commands/rights/traffic_stop",
            headers=auth_headers
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        assert "rights_text" in data
        print(f"✓ Traffic stop rights retrieved")
    
    def test_get_rights_invalid_type(self, auth_headers):
        """GET /api/voice-commands/rights/invalid - Invalid encounter type"""
        response = requests.get(
            f"{BASE_URL}/api/voice-commands/rights/invalid_type",
            headers=auth_headers
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ Invalid encounter type correctly rejected")


class TestVoiceCommandsTest:
    """Voice Commands Test endpoint (no auth required)"""
    
    def test_command_parsing(self):
        """POST /api/voice-commands/test - Test command parsing"""
        response = requests.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, start recording"}
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "parsed_command" in data
        assert "would_execute" in data
        print(f"✓ Test parsing: command={data.get('parsed_command')}, would_execute={data.get('would_execute')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
