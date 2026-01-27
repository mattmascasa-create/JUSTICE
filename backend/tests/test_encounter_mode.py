"""
Test Encounter Mode - Recording, Audio/Video Upload, Transcription
Tests for: start/stop recording, audio upload with transcription, video upload
"""
import pytest
import requests
import os
import io
import wave
import struct
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Authentication failed - skipping tests")


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


def create_test_audio_blob():
    """Create a minimal valid WAV audio file for testing"""
    # Create a simple WAV file in memory
    sample_rate = 16000
    duration = 1  # 1 second
    num_samples = sample_rate * duration
    
    # Generate silence (zeros)
    audio_data = struct.pack('<' + 'h' * num_samples, *([0] * num_samples))
    
    # Create WAV file
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data)
    
    buffer.seek(0)
    return buffer.read()


def create_test_video_blob():
    """Create a minimal test video blob (webm header)"""
    # Minimal webm header bytes
    webm_header = bytes([
        0x1A, 0x45, 0xDF, 0xA3,  # EBML header
        0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F,
        0x42, 0x86, 0x81, 0x01,  # EBMLVersion
        0x42, 0xF7, 0x81, 0x01,  # EBMLReadVersion
        0x42, 0xF2, 0x81, 0x04,  # EBMLMaxIDLength
        0x42, 0xF3, 0x81, 0x08,  # EBMLMaxSizeLength
        0x42, 0x82, 0x84, 0x77, 0x65, 0x62, 0x6D,  # DocType: webm
    ])
    return webm_header


class TestEncounterStart:
    """Test POST /api/encounters/start - Create new encounter"""
    
    def test_start_encounter_success(self, auth_headers):
        """Test starting a new encounter successfully"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/start",
            headers=auth_headers,
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "address": "Test Location, NY",
                "encounter_type": "traffic_stop",
                "broadcast_mode": "save",
                "video_enabled": True
            }
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "encounter_id" in data, "Response should contain encounter_id"
        assert data["encounter_id"].startswith("enc_"), "encounter_id should start with 'enc_'"
        assert data["status"] == "active", "New encounter should be active"
        assert data["encounter_type"] == "traffic_stop"
        assert data["broadcast_mode"] == "save"
        
        print(f"✓ Created encounter: {data['encounter_id']}")
        return data["encounter_id"]
    
    def test_start_encounter_requires_auth(self):
        """Test that starting encounter requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/start",
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "encounter_type": "traffic_stop"
            }
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403 without auth, got {response.status_code}"
        print("✓ Start encounter requires authentication")
    
    def test_start_encounter_different_types(self, auth_headers):
        """Test starting encounters with different types"""
        encounter_types = ["traffic_stop", "pedestrian_stop", "arrest", "search", "other"]
        
        for enc_type in encounter_types:
            response = requests.post(
                f"{BASE_URL}/api/encounters/start",
                headers=auth_headers,
                json={
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "encounter_type": enc_type,
                    "broadcast_mode": "save"
                }
            )
            
            assert response.status_code == 200, f"Failed for type {enc_type}: {response.text}"
            data = response.json()
            assert data["encounter_type"] == enc_type
            print(f"✓ Created {enc_type} encounter: {data['encounter_id']}")


class TestEncounterEnd:
    """Test POST /api/encounters/{id}/end - End encounter"""
    
    def test_end_encounter_success(self, auth_headers):
        """Test ending an encounter successfully"""
        # First create an encounter
        start_response = requests.post(
            f"{BASE_URL}/api/encounters/start",
            headers=auth_headers,
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "encounter_type": "traffic_stop",
                "broadcast_mode": "save"
            }
        )
        assert start_response.status_code == 200
        encounter_id = start_response.json()["encounter_id"]
        
        # Wait a moment
        time.sleep(0.5)
        
        # End the encounter
        end_response = requests.post(
            f"{BASE_URL}/api/encounters/{encounter_id}/end",
            headers=auth_headers
        )
        
        assert end_response.status_code == 200, f"Expected 200, got {end_response.status_code}: {end_response.text}"
        data = end_response.json()
        
        assert data["success"] == True
        assert data["encounter_id"] == encounter_id
        assert "ended_at" in data
        assert "duration_seconds" in data
        
        print(f"✓ Ended encounter {encounter_id}, duration: {data['duration_seconds']}s")
    
    def test_end_encounter_not_found(self, auth_headers):
        """Test ending non-existent encounter returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/enc_nonexistent123/end",
            headers=auth_headers
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ End non-existent encounter returns 404")
    
    def test_end_encounter_requires_auth(self):
        """Test that ending encounter requires authentication"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/enc_test123/end"
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ End encounter requires authentication")


class TestAudioUpload:
    """Test POST /api/encounters/{id}/audio - Audio upload with transcription"""
    
    @pytest.fixture
    def active_encounter(self, auth_headers):
        """Create an active encounter for testing"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/start",
            headers=auth_headers,
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "encounter_type": "traffic_stop",
                "broadcast_mode": "save"
            }
        )
        assert response.status_code == 200
        return response.json()["encounter_id"]
    
    def test_audio_upload_accepts_blob(self, auth_headers, active_encounter):
        """Test that audio upload endpoint accepts audio blob"""
        audio_data = create_test_audio_blob()
        
        # Remove Content-Type from headers for multipart
        headers = {"Authorization": auth_headers["Authorization"]}
        
        files = {
            'audio': ('chunk_0.wav', audio_data, 'audio/wav')
        }
        data = {
            'chunk_index': '0'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/encounters/{active_encounter}/audio",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        
        assert result["success"] == True
        assert result["chunk_index"] == 0
        assert "filename" in result
        
        # Transcription may or may not be present depending on STT service
        if result.get("transcription"):
            print(f"✓ Audio uploaded with transcription: {result['transcription'].get('text', '')[:50]}...")
        else:
            print(f"✓ Audio uploaded successfully (no transcription - STT may not be available)")
    
    def test_audio_upload_webm_format(self, auth_headers, active_encounter):
        """Test audio upload with webm format"""
        # Create minimal webm-like data
        webm_data = bytes([0x1A, 0x45, 0xDF, 0xA3] + [0] * 100)
        
        headers = {"Authorization": auth_headers["Authorization"]}
        
        files = {
            'audio': ('chunk_1.webm', webm_data, 'audio/webm')
        }
        data = {
            'chunk_index': '1'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/encounters/{active_encounter}/audio",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("✓ Audio upload accepts webm format")
    
    def test_audio_upload_not_found(self, auth_headers):
        """Test audio upload to non-existent encounter"""
        audio_data = create_test_audio_blob()
        headers = {"Authorization": auth_headers["Authorization"]}
        
        files = {
            'audio': ('chunk_0.wav', audio_data, 'audio/wav')
        }
        data = {
            'chunk_index': '0'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/encounters/enc_nonexistent123/audio",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Audio upload to non-existent encounter returns 404")
    
    def test_audio_upload_requires_auth(self):
        """Test that audio upload requires authentication"""
        audio_data = create_test_audio_blob()
        
        files = {
            'audio': ('chunk_0.wav', audio_data, 'audio/wav')
        }
        data = {
            'chunk_index': '0'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/encounters/enc_test123/audio",
            files=files,
            data=data
        )
        
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
        print("✓ Audio upload requires authentication")


class TestVideoUpload:
    """Test POST /api/encounters/{id}/video - Video upload"""
    
    @pytest.fixture
    def active_encounter(self, auth_headers):
        """Create an active encounter for testing"""
        response = requests.post(
            f"{BASE_URL}/api/encounters/start",
            headers=auth_headers,
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "encounter_type": "traffic_stop",
                "broadcast_mode": "save",
                "video_enabled": True
            }
        )
        assert response.status_code == 200
        return response.json()["encounter_id"]
    
    def test_video_upload_success(self, auth_headers, active_encounter):
        """Test video upload endpoint works"""
        video_data = create_test_video_blob()
        
        headers = {"Authorization": auth_headers["Authorization"]}
        
        files = {
            'video': ('video_chunk_0.webm', video_data, 'video/webm')
        }
        data = {
            'chunk_index': '0'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/encounters/{active_encounter}/video",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        result = response.json()
        
        assert result["success"] == True
        assert result["chunk_index"] == 0
        assert "filename" in result
        
        print(f"✓ Video uploaded: {result['filename']}")
    
    def test_video_upload_multiple_chunks(self, auth_headers, active_encounter):
        """Test uploading multiple video chunks"""
        headers = {"Authorization": auth_headers["Authorization"]}
        
        for i in range(3):
            video_data = create_test_video_blob()
            
            files = {
                'video': (f'video_chunk_{i}.webm', video_data, 'video/webm')
            }
            data = {
                'chunk_index': str(i)
            }
            
            response = requests.post(
                f"{BASE_URL}/api/encounters/{active_encounter}/video",
                headers=headers,
                files=files,
                data=data
            )
            
            assert response.status_code == 200, f"Chunk {i} failed: {response.text}"
        
        print("✓ Multiple video chunks uploaded successfully")
    
    def test_video_upload_not_found(self, auth_headers):
        """Test video upload to non-existent encounter"""
        video_data = create_test_video_blob()
        headers = {"Authorization": auth_headers["Authorization"]}
        
        files = {
            'video': ('video_chunk_0.webm', video_data, 'video/webm')
        }
        data = {
            'chunk_index': '0'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/encounters/enc_nonexistent123/video",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Video upload to non-existent encounter returns 404")


class TestSTTServiceInitialization:
    """Test that STT service is properly initialized"""
    
    def test_stt_service_available(self, auth_headers):
        """Test that transcription works when STT service is available"""
        # Create encounter
        start_response = requests.post(
            f"{BASE_URL}/api/encounters/start",
            headers=auth_headers,
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "encounter_type": "traffic_stop",
                "broadcast_mode": "save"
            }
        )
        assert start_response.status_code == 200
        encounter_id = start_response.json()["encounter_id"]
        
        # Upload audio
        audio_data = create_test_audio_blob()
        headers = {"Authorization": auth_headers["Authorization"]}
        
        files = {
            'audio': ('chunk_0.wav', audio_data, 'audio/wav')
        }
        data = {
            'chunk_index': '0'
        }
        
        response = requests.post(
            f"{BASE_URL}/api/encounters/{encounter_id}/audio",
            headers=headers,
            files=files,
            data=data
        )
        
        assert response.status_code == 200, f"Audio upload failed: {response.text}"
        result = response.json()
        
        # The endpoint should work regardless of STT availability
        assert result["success"] == True
        
        # Check if transcription was returned (depends on STT service)
        if result.get("transcription"):
            print(f"✓ STT service is working - transcription returned")
            assert "text" in result["transcription"] or "segment_id" in result["transcription"]
        else:
            print("✓ Audio upload works (STT service may not have transcribed silent audio)")


class TestEncounterList:
    """Test GET /api/encounters - List encounters"""
    
    def test_list_encounters(self, auth_headers):
        """Test listing user's encounters"""
        response = requests.get(
            f"{BASE_URL}/api/encounters",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert isinstance(data, list), "Response should be a list"
        print(f"✓ Listed {len(data)} encounters")
    
    def test_list_encounters_by_status(self, auth_headers):
        """Test filtering encounters by status"""
        response = requests.get(
            f"{BASE_URL}/api/encounters",
            headers=auth_headers,
            params={"status": "completed"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # All returned encounters should be completed
        for enc in data:
            if enc.get("status"):
                assert enc["status"] == "completed", f"Expected completed, got {enc['status']}"
        
        print(f"✓ Filtered encounters by status: {len(data)} completed")


class TestEncounterGet:
    """Test GET /api/encounters/{id} - Get specific encounter"""
    
    def test_get_encounter(self, auth_headers):
        """Test getting a specific encounter"""
        # Create encounter first
        start_response = requests.post(
            f"{BASE_URL}/api/encounters/start",
            headers=auth_headers,
            json={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "encounter_type": "traffic_stop",
                "broadcast_mode": "save"
            }
        )
        assert start_response.status_code == 200
        encounter_id = start_response.json()["encounter_id"]
        
        # Get the encounter
        response = requests.get(
            f"{BASE_URL}/api/encounters/{encounter_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        assert data["encounter_id"] == encounter_id
        assert data["encounter_type"] == "traffic_stop"
        assert data["status"] == "active"
        
        print(f"✓ Retrieved encounter {encounter_id}")
    
    def test_get_encounter_not_found(self, auth_headers):
        """Test getting non-existent encounter"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/enc_nonexistent123",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        print("✓ Get non-existent encounter returns 404")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
