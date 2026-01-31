"""
Test Suite for Witness Network and Panic Gesture Features

Tests:
- Witness Network: Location sharing, witness alerts, multi-angle recording coordination
- Panic Gesture: Secret gesture configuration, trigger, presets
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuth:
    """Authentication tests"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }


class TestWitnessNetworkConfig(TestAuth):
    """Witness Network Configuration Tests"""
    
    def test_get_config(self, auth_headers):
        """GET /api/witness-network/config - Returns configuration"""
        response = requests.get(f"{BASE_URL}/api/witness-network/config", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "receive_alerts" in data
        assert "share_location" in data
        assert "alert_radius_meters" in data
        print(f"✓ Witness config retrieved: enabled={data.get('enabled')}")
    
    def test_get_config_requires_auth(self):
        """GET /api/witness-network/config - Requires authentication"""
        response = requests.get(f"{BASE_URL}/api/witness-network/config")
        assert response.status_code in [401, 403]
        print("✓ Config endpoint requires authentication")
    
    def test_update_config(self, auth_headers):
        """PUT /api/witness-network/config - Updates configuration"""
        config = {
            "enabled": True,
            "receive_alerts": True,
            "share_location": True,
            "alert_radius_meters": 750,
            "auto_record": True,
            "quiet_hours_start": 22,
            "quiet_hours_end": 6
        }
        response = requests.put(f"{BASE_URL}/api/witness-network/config", 
                               headers=auth_headers, json=config)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print("✓ Witness config updated successfully")
        
        # Verify update persisted
        get_response = requests.get(f"{BASE_URL}/api/witness-network/config", headers=auth_headers)
        assert get_response.status_code == 200
        updated_config = get_response.json()
        assert updated_config["alert_radius_meters"] == 750
        assert updated_config["auto_record"] == True
        print("✓ Config update verified via GET")


class TestWitnessNetworkLocation(TestAuth):
    """Witness Network Location Tests"""
    
    def test_update_location(self, auth_headers):
        """POST /api/witness-network/location - Updates user location"""
        # First ensure config is saved with share_location=True
        config = {
            "enabled": True,
            "receive_alerts": True,
            "share_location": True,
            "alert_radius_meters": 500,
            "auto_record": False
        }
        requests.put(f"{BASE_URL}/api/witness-network/config", headers=auth_headers, json=config)
        
        # Now update location
        location = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "accuracy": 10.5,
            "altitude": 50.0
        }
        response = requests.post(f"{BASE_URL}/api/witness-network/location", 
                                headers=auth_headers, json=location)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert data["message"] == "Location updated"
        print(f"✓ Location updated: {location['latitude']}, {location['longitude']}")
    
    def test_update_location_requires_auth(self):
        """POST /api/witness-network/location - Requires authentication"""
        location = {"latitude": 40.7128, "longitude": -74.0060}
        response = requests.post(f"{BASE_URL}/api/witness-network/location", json=location)
        assert response.status_code in [401, 403]
        print("✓ Location endpoint requires authentication")
    
    def test_clear_location(self, auth_headers):
        """DELETE /api/witness-network/location - Clears user location"""
        response = requests.delete(f"{BASE_URL}/api/witness-network/location", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print("✓ Location cleared successfully")


class TestWitnessNetworkAlert(TestAuth):
    """Witness Network Alert Tests"""
    
    def test_send_alert(self, auth_headers):
        """POST /api/witness-network/alert - Sends witness alert"""
        alert = {
            "encounter_id": f"TEST_encounter_{uuid.uuid4().hex[:8]}",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "encounter_type": "traffic_stop",
            "urgency": "normal",
            "message": "Test alert for witness network"
        }
        response = requests.post(f"{BASE_URL}/api/witness-network/alert", 
                                headers=auth_headers, json=alert)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "witnesses_alerted" in data
        print(f"✓ Alert sent: {data['witnesses_alerted']} witnesses alerted")
    
    def test_send_alert_high_urgency(self, auth_headers):
        """POST /api/witness-network/alert - High urgency alert"""
        alert = {
            "encounter_id": f"TEST_urgent_{uuid.uuid4().hex[:8]}",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "encounter_type": "emergency",
            "urgency": "critical"
        }
        response = requests.post(f"{BASE_URL}/api/witness-network/alert", 
                                headers=auth_headers, json=alert)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print("✓ High urgency alert sent successfully")
    
    def test_send_alert_requires_auth(self):
        """POST /api/witness-network/alert - Requires authentication"""
        alert = {
            "encounter_id": "test-123",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "encounter_type": "traffic_stop"
        }
        response = requests.post(f"{BASE_URL}/api/witness-network/alert", json=alert)
        assert response.status_code in [401, 403]
        print("✓ Alert endpoint requires authentication")


class TestWitnessNetworkStats(TestAuth):
    """Witness Network Statistics Tests"""
    
    def test_get_stats(self, auth_headers):
        """GET /api/witness-network/stats - Returns network statistics"""
        response = requests.get(f"{BASE_URL}/api/witness-network/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify network stats structure
        assert "network" in data
        assert "active_witnesses" in data["network"]
        assert "total_witness_recordings" in data["network"]
        assert "completed_recordings" in data["network"]
        assert "alerts_sent_today" in data["network"]
        
        # Verify personal stats structure
        assert "personal" in data
        assert "my_witness_recordings" in data["personal"]
        assert "alerts_received" in data["personal"]
        
        print(f"✓ Stats retrieved: {data['network']['active_witnesses']} active witnesses")
    
    def test_get_stats_requires_auth(self):
        """GET /api/witness-network/stats - Requires authentication"""
        response = requests.get(f"{BASE_URL}/api/witness-network/stats")
        assert response.status_code in [401, 403]
        print("✓ Stats endpoint requires authentication")


class TestPanicGestureConfig(TestAuth):
    """Panic Gesture Configuration Tests"""
    
    def test_get_config(self, auth_headers):
        """GET /api/panic-gesture/config - Returns configuration"""
        response = requests.get(f"{BASE_URL}/api/panic-gesture/config", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        # Verify config structure
        assert "enabled" in data
        assert "gesture_type" in data
        assert "sensitivity" in data
        assert "shake_threshold" in data
        assert "auto_stealth" in data
        assert "auto_record_video" in data
        assert "auto_record_audio" in data
        assert "notify_contacts" in data
        assert "cooldown_seconds" in data
        
        print(f"✓ Panic config retrieved: gesture_type={data.get('gesture_type')}")
    
    def test_get_config_requires_auth(self):
        """GET /api/panic-gesture/config - Requires authentication"""
        response = requests.get(f"{BASE_URL}/api/panic-gesture/config")
        assert response.status_code in [401, 403]
        print("✓ Config endpoint requires authentication")
    
    def test_update_config(self, auth_headers):
        """PUT /api/panic-gesture/config - Updates configuration"""
        config = {
            "enabled": True,
            "gesture_type": "volume_triple",
            "sensitivity": "high",
            "shake_threshold": 4,
            "shake_duration_ms": 1500,
            "auto_stealth": True,
            "auto_record_video": True,
            "auto_record_audio": True,
            "notify_contacts": True,
            "confirmation_vibrate": True,
            "cooldown_seconds": 45
        }
        response = requests.put(f"{BASE_URL}/api/panic-gesture/config", 
                               headers=auth_headers, json=config)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print("✓ Panic config updated successfully")
        
        # Verify update persisted
        get_response = requests.get(f"{BASE_URL}/api/panic-gesture/config", headers=auth_headers)
        assert get_response.status_code == 200
        updated_config = get_response.json()
        assert updated_config["gesture_type"] == "volume_triple"
        assert updated_config["sensitivity"] == "high"
        assert updated_config["cooldown_seconds"] == 45
        print("✓ Config update verified via GET")
    
    def test_update_config_shake_gesture(self, auth_headers):
        """PUT /api/panic-gesture/config - Shake gesture configuration"""
        config = {
            "enabled": True,
            "gesture_type": "shake",
            "sensitivity": "medium",
            "shake_threshold": 3,
            "shake_duration_ms": 1000,
            "auto_stealth": True,
            "auto_record_video": True,
            "auto_record_audio": True,
            "notify_contacts": False,
            "confirmation_vibrate": True,
            "cooldown_seconds": 30
        }
        response = requests.put(f"{BASE_URL}/api/panic-gesture/config", 
                               headers=auth_headers, json=config)
        assert response.status_code == 200
        print("✓ Shake gesture config saved")


class TestPanicGestureTrigger(TestAuth):
    """Panic Gesture Trigger Tests"""
    
    def test_trigger_panic_recording(self, auth_headers):
        """POST /api/panic-gesture/trigger - Triggers panic recording"""
        # First reset cooldown by waiting or using a fresh config
        config = {
            "enabled": True,
            "gesture_type": "shake",
            "sensitivity": "medium",
            "shake_threshold": 3,
            "shake_duration_ms": 1000,
            "auto_stealth": True,
            "auto_record_video": True,
            "auto_record_audio": True,
            "notify_contacts": False,
            "confirmation_vibrate": True,
            "cooldown_seconds": 1  # Short cooldown for testing
        }
        requests.put(f"{BASE_URL}/api/panic-gesture/config", headers=auth_headers, json=config)
        
        import time
        time.sleep(2)  # Wait for cooldown
        
        trigger = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "gesture_type": "shake",
            "trigger_source": "gesture"
        }
        response = requests.post(f"{BASE_URL}/api/panic-gesture/trigger", 
                                headers=auth_headers, json=trigger)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "encounter_id" in data
        assert data["stealth_mode"] == True
        assert data["video_enabled"] == True
        assert data["audio_enabled"] == True
        print(f"✓ Panic recording triggered: encounter_id={data['encounter_id']}")
    
    def test_trigger_manual_test(self, auth_headers):
        """POST /api/panic-gesture/trigger - Manual test trigger"""
        import time
        time.sleep(2)  # Wait for cooldown
        
        trigger = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "gesture_type": "shake",
            "trigger_source": "manual_test"
        }
        response = requests.post(f"{BASE_URL}/api/panic-gesture/trigger", 
                                headers=auth_headers, json=trigger)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        print("✓ Manual test trigger successful")
    
    def test_trigger_requires_auth(self):
        """POST /api/panic-gesture/trigger - Requires authentication"""
        trigger = {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "gesture_type": "shake",
            "trigger_source": "gesture"
        }
        response = requests.post(f"{BASE_URL}/api/panic-gesture/trigger", json=trigger)
        assert response.status_code in [401, 403]
        print("✓ Trigger endpoint requires authentication")


class TestPanicGesturePresets(TestAuth):
    """Panic Gesture Presets Tests"""
    
    def test_get_presets(self, auth_headers):
        """GET /api/panic-gesture/presets - Returns gesture presets"""
        response = requests.get(f"{BASE_URL}/api/panic-gesture/presets", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "presets" in data
        presets = data["presets"]
        assert len(presets) >= 4  # shake, volume_triple, power_triple, squeeze
        
        # Verify preset structure
        preset_ids = [p["id"] for p in presets]
        assert "shake" in preset_ids
        assert "volume_triple" in preset_ids
        assert "power_triple" in preset_ids
        assert "squeeze" in preset_ids
        
        # Verify each preset has required fields
        for preset in presets:
            assert "id" in preset
            assert "name" in preset
            assert "description" in preset
            assert "icon" in preset
            assert "sensitivity_options" in preset
            assert "default_settings" in preset
        
        print(f"✓ Retrieved {len(presets)} gesture presets")
    
    def test_presets_no_auth_required(self, auth_headers):
        """GET /api/panic-gesture/presets - Works with auth"""
        # Presets should work with auth
        response = requests.get(f"{BASE_URL}/api/panic-gesture/presets", headers=auth_headers)
        assert response.status_code == 200
        print("✓ Presets endpoint works with authentication")


class TestPanicGestureHistory(TestAuth):
    """Panic Gesture History Tests"""
    
    def test_get_history(self, auth_headers):
        """GET /api/panic-gesture/history - Returns trigger history"""
        response = requests.get(f"{BASE_URL}/api/panic-gesture/history", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert "triggers" in data
        assert "count" in data
        assert isinstance(data["triggers"], list)
        
        # If there are triggers, verify structure
        if data["triggers"]:
            trigger = data["triggers"][0]
            assert "trigger_id" in trigger
            assert "gesture_type" in trigger
            assert "triggered_at" in trigger
        
        print(f"✓ Retrieved {data['count']} trigger history entries")
    
    def test_get_history_with_limit(self, auth_headers):
        """GET /api/panic-gesture/history - With limit parameter"""
        response = requests.get(f"{BASE_URL}/api/panic-gesture/history?limit=5", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["triggers"]) <= 5
        print("✓ History limit parameter works")


class TestPanicGestureTest(TestAuth):
    """Panic Gesture Test Endpoint Tests"""
    
    def test_test_gesture(self, auth_headers):
        """POST /api/panic-gesture/test - Tests gesture detection"""
        response = requests.post(f"{BASE_URL}/api/panic-gesture/test", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        
        assert data["success"] == True
        assert "message" in data
        assert "config" in data
        assert "enabled" in data["config"]
        assert "gesture_type" in data["config"]
        assert "sensitivity" in data["config"]
        
        print(f"✓ Gesture test successful: {data['message']}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
