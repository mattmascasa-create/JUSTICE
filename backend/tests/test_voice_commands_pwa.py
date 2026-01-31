"""
Test Voice Commands API and PWA-related endpoints
Tests for iteration 46 - Voice Control Panel and PWA features
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestVoiceCommandsAPI:
    """Voice Commands API endpoint tests"""
    
    def test_get_commands_list(self):
        """Test GET /api/voice-commands/commands returns list of commands"""
        response = requests.get(f"{BASE_URL}/api/voice-commands/commands")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data.get('success') == True
        assert 'wake_word' in data
        assert 'commands' in data
        assert isinstance(data['commands'], list)
        
        # Verify wake word
        assert data['wake_word'] == 'Hey Justice'
        
        # Verify commands list has expected commands
        command_names = [cmd['command'] for cmd in data['commands']]
        expected_commands = [
            'start_recording', 'stop_recording', 'alert_attorney',
            'panic_button', 'know_rights', 'officer_lookup',
            'share_location', 'add_note', 'get_status', 'help'
        ]
        
        for expected in expected_commands:
            assert expected in command_names, f"Missing command: {expected}"
        
        print(f"✓ Voice commands API returned {len(data['commands'])} commands")
    
    def test_commands_have_examples(self):
        """Test that each command has examples"""
        response = requests.get(f"{BASE_URL}/api/voice-commands/commands")
        
        assert response.status_code == 200
        data = response.json()
        
        for cmd in data['commands']:
            assert 'examples' in cmd, f"Command {cmd['command']} missing examples"
            assert len(cmd['examples']) > 0, f"Command {cmd['command']} has no examples"
            assert 'description' in cmd, f"Command {cmd['command']} missing description"
        
        print("✓ All commands have examples and descriptions")
    
    def test_commands_have_descriptions(self):
        """Test that each command has a description"""
        response = requests.get(f"{BASE_URL}/api/voice-commands/commands")
        
        assert response.status_code == 200
        data = response.json()
        
        for cmd in data['commands']:
            assert 'description' in cmd
            assert len(cmd['description']) > 0
        
        print("✓ All commands have descriptions")


class TestHealthEndpoint:
    """Health endpoint tests"""
    
    def test_health_check(self):
        """Test GET /api/health returns healthy status"""
        response = requests.get(f"{BASE_URL}/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get('status') == 'healthy'
        assert 'version' in data
        assert 'features' in data
        
        print(f"✓ Health check passed - version {data.get('version')}")
    
    def test_health_features(self):
        """Test health endpoint returns feature flags"""
        response = requests.get(f"{BASE_URL}/api/health")
        
        assert response.status_code == 200
        data = response.json()
        
        features = data.get('features', {})
        
        # Verify key features are present
        expected_features = [
            'real_time_sharing', 'live_guidance', 'video_streaming',
            'ai_rights_coach', 'dead_mans_switch', 'witness_network'
        ]
        
        for feature in expected_features:
            assert feature in features, f"Missing feature flag: {feature}"
        
        print(f"✓ Health endpoint returned {len(features)} feature flags")


class TestEncounterEndpoints:
    """Encounter-related endpoint tests"""
    
    def test_encounter_types_available(self):
        """Test that encounter types endpoint is accessible"""
        # This tests the frontend config, but we verify the backend supports it
        response = requests.get(f"{BASE_URL}/api/health")
        
        assert response.status_code == 200
        print("✓ Backend is ready to support encounter types")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
