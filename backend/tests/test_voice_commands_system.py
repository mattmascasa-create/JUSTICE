"""
Voice Command System Tests - Hands-free encounter control with natural language processing
Tests: Command parsing, command execution, rights queries, officer lookup
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestVoiceCommandsNoAuth:
    """Test voice command endpoints that don't require authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
    
    # ==================== GET /api/voice-commands/commands ====================
    def test_list_commands_returns_all_10_commands(self):
        """GET /api/voice-commands/commands - Returns all 10 voice commands"""
        response = self.session.get(f"{BASE_URL}/api/voice-commands/commands")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["wake_word"] == "Hey Justice"
        assert len(data["commands"]) == 10
        
        # Verify all command types are present
        command_names = [cmd["command"] for cmd in data["commands"]]
        expected_commands = [
            "start_recording", "stop_recording", "alert_attorney", "panic_button",
            "know_rights", "officer_lookup", "share_location", "add_note",
            "get_status", "help"
        ]
        for expected in expected_commands:
            assert expected in command_names, f"Missing command: {expected}"
    
    def test_list_commands_has_examples(self):
        """GET /api/voice-commands/commands - Each command has examples"""
        response = self.session.get(f"{BASE_URL}/api/voice-commands/commands")
        assert response.status_code == 200
        
        data = response.json()
        for cmd in data["commands"]:
            assert "examples" in cmd
            assert len(cmd["examples"]) > 0
            assert "description" in cmd
    
    # ==================== POST /api/voice-commands/test ====================
    def test_parse_start_recording(self):
        """POST /api/voice-commands/test - Parse 'Hey Justice, start recording'"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, start recording"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "start_recording"
        assert data["would_execute"] is True
    
    def test_parse_stop_recording(self):
        """POST /api/voice-commands/test - Parse 'Hey Justice, stop recording'"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, stop recording"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "stop_recording"
        assert data["would_execute"] is True
    
    def test_parse_badge_number_extracts_params(self):
        """POST /api/voice-commands/test - Parse 'Hey Justice, badge number 3803' extracts badge"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, badge number 3803"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "officer_lookup"
        assert data["extracted_params"]["badge_number"] == "3803"
        assert data["would_execute"] is True
    
    def test_parse_know_rights_default(self):
        """POST /api/voice-commands/test - Parse 'Hey Justice, what are my rights'"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, what are my rights"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "know_rights"
        assert data["extracted_params"]["topic"] == "default"
        assert data["would_execute"] is True
    
    def test_parse_know_rights_search_topic(self):
        """POST /api/voice-commands/test - Parse 'do I have to consent to a search' extracts search topic"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, do I have to consent to a search"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "know_rights"
        assert data["extracted_params"]["topic"] == "search"
    
    def test_parse_panic_button_help_me(self):
        """POST /api/voice-commands/test - Parse 'Hey Justice, help me' -> panic_button"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, help me"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "panic_button"
        assert data["would_execute"] is True
    
    def test_parse_panic_button_emergency(self):
        """POST /api/voice-commands/test - Parse 'Hey Justice, emergency' -> panic_button"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, emergency"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "panic_button"
    
    def test_parse_panic_button_sos(self):
        """POST /api/voice-commands/test - Parse 'SOS' -> panic_button"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "SOS"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "panic_button"
    
    def test_parse_alert_attorney(self):
        """POST /api/voice-commands/test - Parse 'Hey Justice, alert my attorney'"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, alert my attorney"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "alert_attorney"
    
    def test_parse_share_location(self):
        """POST /api/voice-commands/test - Parse 'Hey Justice, share my location'"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, share my location"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "share_location"
    
    def test_parse_add_note(self):
        """POST /api/voice-commands/test - Parse 'Hey Justice, add note: officer was aggressive'"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, add note: officer was aggressive"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "add_note"
        assert "note_content" in data["extracted_params"]
    
    def test_parse_get_status(self):
        """POST /api/voice-commands/test - Parse 'Hey Justice, status'"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, status"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "get_status"
    
    def test_parse_help_command(self):
        """POST /api/voice-commands/test - Parse 'Hey Justice, help'"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, help"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "help"
    
    def test_parse_unknown_command(self):
        """POST /api/voice-commands/test - Unknown command returns 'unknown'"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, make me a sandwich"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "unknown"
        assert data["would_execute"] is False
    
    def test_parse_without_wake_word(self):
        """POST /api/voice-commands/test - Commands work without wake word"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "start recording"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "start_recording"
    
    def test_parse_case_insensitive(self):
        """POST /api/voice-commands/test - Command parsing is case insensitive"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "HEY JUSTICE, START RECORDING"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["parsed_command"] == "start_recording"


class TestVoiceCommandsAuth:
    """Test voice command endpoints that require authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed - skipping authenticated tests")
    
    # ==================== POST /api/voice-commands/process ====================
    def test_process_requires_auth(self):
        """POST /api/voice-commands/process - Requires authentication"""
        # Use a new session without auth
        no_auth_session = requests.Session()
        no_auth_session.headers.update({"Content-Type": "application/json"})
        
        response = no_auth_session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, start recording"}
        )
        # API returns 401 or 403 for unauthorized access
        assert response.status_code in [401, 403]
    
    def test_process_officer_lookup_badge_3803(self):
        """POST /api/voice-commands/process - Officer lookup badge 3803 returns James Garcia"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, badge number 3803"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["command_recognized"] == "officer_lookup"
        assert data["response"]["action_taken"] == "officer_found"
        assert data["response"]["data"]["officer_name"] == "James Garcia"
        assert data["response"]["data"]["accountability_score"] == 40.2
        assert data["response"]["data"]["badge_number"] == "3803"
    
    def test_process_officer_lookup_not_found(self):
        """POST /api/voice-commands/process - Officer lookup for unknown badge"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, badge number 99999"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["command_recognized"] == "officer_lookup"
        assert data["response"]["action_taken"] == "officer_not_found"
        assert "not found" in data["response"]["response_text"].lower()
    
    def test_process_officer_lookup_no_badge(self):
        """POST /api/voice-commands/process - Officer lookup without badge number"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, look up this officer"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["command_recognized"] == "officer_lookup"
        assert data["response"]["action_taken"] == "need_badge"
    
    def test_process_know_rights_default(self):
        """POST /api/voice-commands/process - Know rights returns contextual info"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, what are my rights"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["command_recognized"] == "know_rights"
        assert data["response"]["action_taken"] == "rights_provided"
        # Response contains rights information (license, registration, searches, silent, etc.)
        response_text = data["response"]["response_text"].lower()
        assert any(word in response_text for word in ["license", "registration", "searches", "silent", "traffic stop"])
    
    def test_process_know_rights_search_topic(self):
        """POST /api/voice-commands/process - Know rights with search topic"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, do I have to consent to a search"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["command_recognized"] == "know_rights"
        assert data["response"]["data"]["topic"] == "search"
        assert "search" in data["response"]["response_text"].lower()
    
    def test_process_start_recording(self):
        """POST /api/voice-commands/process - Start recording command"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, start recording"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["command_recognized"] == "start_recording"
        assert data["response"]["action_taken"] in ["start_recording", "already_recording"]
    
    def test_process_stop_recording(self):
        """POST /api/voice-commands/process - Stop recording command"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, stop recording"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["command_recognized"] == "stop_recording"
        assert data["response"]["action_taken"] == "stop_recording"
    
    def test_process_panic_button(self):
        """POST /api/voice-commands/process - Panic button triggers emergency"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, help me"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["command_recognized"] == "panic_button"
        assert data["response"]["action_taken"] == "emergency_triggered"
        assert data["response"]["data"]["sos_triggered"] is True
    
    def test_process_share_location(self):
        """POST /api/voice-commands/process - Share location command"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, share my location"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["command_recognized"] == "share_location"
        assert data["response"]["action_taken"] == "location_shared"
    
    def test_process_help_command(self):
        """POST /api/voice-commands/process - Help command lists available commands"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, help"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["command_recognized"] == "help"
        assert data["response"]["action_taken"] == "help_provided"
        assert "available_commands" in data["response"]["data"]
    
    def test_process_get_status_no_encounter(self):
        """POST /api/voice-commands/process - Get status without active encounter"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, status"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["command_recognized"] == "get_status"
        assert data["response"]["action_taken"] == "no_encounter"
    
    def test_process_short_command_rejected(self):
        """POST /api/voice-commands/process - Short commands are rejected"""
        response = self.session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "a"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is False
        assert "error" in data
    
    # ==================== GET /api/voice-commands/rights/{type} ====================
    def test_rights_traffic_stop_default(self):
        """GET /api/voice-commands/rights/traffic_stop - Returns traffic stop rights"""
        response = self.session.get(
            f"{BASE_URL}/api/voice-commands/rights/traffic_stop"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["encounter_type"] == "traffic_stop"
        assert "license" in data["rights_text"].lower() or "registration" in data["rights_text"].lower()
    
    def test_rights_traffic_stop_search(self):
        """GET /api/voice-commands/rights/traffic_stop?topic=search - Returns search rights"""
        response = self.session.get(
            f"{BASE_URL}/api/voice-commands/rights/traffic_stop",
            params={"topic": "search"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["topic"] == "search"
        assert "consent" in data["rights_text"].lower() or "search" in data["rights_text"].lower()
    
    def test_rights_pedestrian_stop(self):
        """GET /api/voice-commands/rights/pedestrian_stop - Returns pedestrian stop rights"""
        response = self.session.get(
            f"{BASE_URL}/api/voice-commands/rights/pedestrian_stop"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["encounter_type"] == "pedestrian_stop"
        assert "free to go" in data["rights_text"].lower() or "identify" in data["rights_text"].lower()
    
    def test_rights_home(self):
        """GET /api/voice-commands/rights/home - Returns home encounter rights"""
        response = self.session.get(
            f"{BASE_URL}/api/voice-commands/rights/home"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["encounter_type"] == "home"
        assert "warrant" in data["rights_text"].lower()
    
    def test_rights_arrest(self):
        """GET /api/voice-commands/rights/arrest - Returns arrest rights"""
        response = self.session.get(
            f"{BASE_URL}/api/voice-commands/rights/arrest"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert data["encounter_type"] == "arrest"
        assert "silent" in data["rights_text"].lower() or "attorney" in data["rights_text"].lower()
    
    def test_rights_invalid_type(self):
        """GET /api/voice-commands/rights/invalid - Returns 400 for invalid type"""
        response = self.session.get(
            f"{BASE_URL}/api/voice-commands/rights/invalid_type"
        )
        assert response.status_code == 400
    
    # ==================== GET /api/voice-commands/stats ====================
    def test_stats_returns_usage_data(self):
        """GET /api/voice-commands/stats - Returns usage statistics"""
        response = self.session.get(
            f"{BASE_URL}/api/voice-commands/stats"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "stats" in data
        assert "total_commands" in data["stats"]
        assert "success_rate" in data["stats"]


class TestVoiceCommandsIntegration:
    """Integration tests for voice command workflows"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup authenticated test session"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed - skipping authenticated tests")
    
    def test_full_officer_lookup_workflow(self):
        """Integration: Parse command -> Execute -> Verify officer data"""
        # Step 1: Parse the command
        parse_response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, badge number 3803"}
        )
        assert parse_response.status_code == 200
        parse_data = parse_response.json()
        assert parse_data["parsed_command"] == "officer_lookup"
        assert parse_data["extracted_params"]["badge_number"] == "3803"
        
        # Step 2: Execute the command
        exec_response = self.session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, badge number 3803"}
        )
        assert exec_response.status_code == 200
        exec_data = exec_response.json()
        assert exec_data["response"]["data"]["officer_name"] == "James Garcia"
        assert exec_data["response"]["data"]["accountability_score"] == 40.2
    
    def test_full_rights_query_workflow(self):
        """Integration: Parse rights query -> Execute -> Verify contextual response"""
        # Step 1: Parse the command
        parse_response = self.session.post(
            f"{BASE_URL}/api/voice-commands/test",
            json={"text": "Hey Justice, do I have to consent to a search"}
        )
        assert parse_response.status_code == 200
        parse_data = parse_response.json()
        assert parse_data["parsed_command"] == "know_rights"
        assert parse_data["extracted_params"]["topic"] == "search"
        
        # Step 2: Execute the command
        exec_response = self.session.post(
            f"{BASE_URL}/api/voice-commands/process",
            json={"text": "Hey Justice, do I have to consent to a search"}
        )
        assert exec_response.status_code == 200
        exec_data = exec_response.json()
        assert exec_data["response"]["data"]["topic"] == "search"
        
        # Step 3: Verify via direct rights endpoint
        rights_response = self.session.get(
            f"{BASE_URL}/api/voice-commands/rights/traffic_stop",
            params={"topic": "search"}
        )
        assert rights_response.status_code == 200
        rights_data = rights_response.json()
        assert "consent" in rights_data["rights_text"].lower()
    
    def test_multiple_commands_sequence(self):
        """Integration: Execute multiple commands in sequence"""
        commands = [
            ("Hey Justice, what are my rights", "know_rights"),
            ("Hey Justice, badge number 3803", "officer_lookup"),
            ("Hey Justice, share my location", "share_location"),
            ("Hey Justice, help", "help"),
        ]
        
        for text, expected_command in commands:
            response = self.session.post(
                f"{BASE_URL}/api/voice-commands/process",
                json={"text": text}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["command_recognized"] == expected_command


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
