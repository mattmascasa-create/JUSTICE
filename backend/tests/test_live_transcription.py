"""
Test Live Transcription Feature for Video Calls
Tests the following endpoints:
- POST /api/calls/{call_id}/live-transcribe - Transcribe audio chunk
- GET /api/calls/{call_id}/live-transcript - Get live transcript
- POST /api/calls/{call_id}/live-note - Add note during call
- POST /api/calls/{call_id}/save-live-transcript - Save transcript to DB
- POST /api/calls/initiate - Initiate a call
- POST /api/calls/{call_id}/recording/start - Start recording
- POST /api/calls/{call_id}/recording/stop - Stop recording
"""
import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_USER = {"email": "test@example.com", "password": "password123"}
ATTORNEY_USER = {"email": "my_attorney@lawfirm.com", "password": "attorney123"}


class TestLiveTranscription:
    """Test live transcription endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.test_token = None
        self.attorney_token = None
        self.test_user_id = None
        self.attorney_user_id = None
        self.call_id = None
    
    def login_user(self, email, password):
        """Login and return token and user_id"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("token"), data.get("user", {}).get("user_id")
        return None, None
    
    def test_01_health_check(self):
        """Verify API is healthy"""
        response = self.session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy"
        print(f"✓ Health check passed - version {data.get('version')}")
    
    def test_02_login_test_user(self):
        """Login as test user"""
        self.test_token, self.test_user_id = self.login_user(
            TEST_USER["email"], TEST_USER["password"]
        )
        assert self.test_token is not None, "Failed to login test user"
        assert self.test_user_id is not None, "Failed to get test user ID"
        print(f"✓ Test user logged in: {self.test_user_id}")
    
    def test_03_login_attorney_user(self):
        """Login as attorney user"""
        self.attorney_token, self.attorney_user_id = self.login_user(
            ATTORNEY_USER["email"], ATTORNEY_USER["password"]
        )
        assert self.attorney_token is not None, "Failed to login attorney user"
        assert self.attorney_user_id is not None, "Failed to get attorney user ID"
        print(f"✓ Attorney user logged in: {self.attorney_user_id}")
    
    def test_04_initiate_call(self):
        """Test initiating a video call"""
        # Login first
        self.test_token, self.test_user_id = self.login_user(
            TEST_USER["email"], TEST_USER["password"]
        )
        self.attorney_token, self.attorney_user_id = self.login_user(
            ATTORNEY_USER["email"], ATTORNEY_USER["password"]
        )
        
        # Initiate call from test user to attorney
        response = self.session.post(
            f"{BASE_URL}/api/calls/initiate",
            data={
                "recipient_id": self.attorney_user_id,
                "call_type": "video"
            },
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        # Accept 200, 201, or 409 (already in call)
        assert response.status_code in [200, 201, 409], f"Unexpected status: {response.status_code} - {response.text}"
        
        if response.status_code == 409:
            print("✓ Call initiation returned 409 (user already in call) - expected behavior")
            # Get active call instead
            active_response = self.session.get(
                f"{BASE_URL}/api/calls/active",
                headers={"Authorization": f"Bearer {self.test_token}"}
            )
            if active_response.status_code == 200:
                active_data = active_response.json()
                if active_data.get("has_active_call"):
                    self.call_id = active_data["call"]["call_id"]
                    print(f"✓ Using existing active call: {self.call_id}")
        else:
            data = response.json()
            self.call_id = data.get("call_id")
            assert self.call_id is not None, "No call_id returned"
            assert data.get("status") == "pending"
            print(f"✓ Call initiated: {self.call_id}")
    
    def test_05_get_active_call(self):
        """Test getting active call"""
        self.test_token, _ = self.login_user(TEST_USER["email"], TEST_USER["password"])
        
        response = self.session.get(
            f"{BASE_URL}/api/calls/active",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Either has active call or not
        assert "has_active_call" in data
        print(f"✓ Get active call: has_active_call={data.get('has_active_call')}")
    
    def test_06_get_incoming_calls(self):
        """Test getting incoming calls"""
        self.attorney_token, _ = self.login_user(ATTORNEY_USER["email"], ATTORNEY_USER["password"])
        
        response = self.session.get(
            f"{BASE_URL}/api/calls/incoming",
            headers={"Authorization": f"Bearer {self.attorney_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "incoming_calls" in data
        print(f"✓ Get incoming calls: {len(data.get('incoming_calls', []))} calls")
    
    def test_07_get_call_history(self):
        """Test getting call history"""
        self.test_token, _ = self.login_user(TEST_USER["email"], TEST_USER["password"])
        
        response = self.session.get(
            f"{BASE_URL}/api/calls/history",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "calls" in data
        print(f"✓ Get call history: {len(data.get('calls', []))} calls")
    
    def test_08_live_transcript_endpoint_exists(self):
        """Test that live transcript endpoint exists (even without active call)"""
        self.test_token, _ = self.login_user(TEST_USER["email"], TEST_USER["password"])
        
        # Use a fake call_id - should return 404 (not found) not 500
        response = self.session.get(
            f"{BASE_URL}/api/calls/fake_call_123/live-transcript",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        # Should return 404 for non-existent call, not 500
        assert response.status_code in [404, 403], f"Unexpected status: {response.status_code}"
        print(f"✓ Live transcript endpoint returns {response.status_code} for non-existent call")
    
    def test_09_live_note_endpoint_exists(self):
        """Test that live note endpoint exists"""
        self.test_token, _ = self.login_user(TEST_USER["email"], TEST_USER["password"])
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/fake_call_123/live-note",
            data={
                "content": "Test note",
                "timestamp": 0,
                "note_type": "general"
            },
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        # Should return 404 for non-existent call
        assert response.status_code in [404, 403], f"Unexpected status: {response.status_code}"
        print(f"✓ Live note endpoint returns {response.status_code} for non-existent call")
    
    def test_10_save_live_transcript_endpoint_exists(self):
        """Test that save live transcript endpoint exists"""
        self.test_token, _ = self.login_user(TEST_USER["email"], TEST_USER["password"])
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/fake_call_123/save-live-transcript",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        # Should return 404 for non-existent call
        assert response.status_code in [404, 403], f"Unexpected status: {response.status_code}"
        print(f"✓ Save live transcript endpoint returns {response.status_code} for non-existent call")
    
    def test_11_live_transcribe_endpoint_exists(self):
        """Test that live transcribe endpoint exists"""
        self.test_token, _ = self.login_user(TEST_USER["email"], TEST_USER["password"])
        
        # Create a minimal audio file (empty webm)
        audio_data = b'\x1a\x45\xdf\xa3'  # Minimal EBML header
        files = {
            'audio_chunk': ('chunk.webm', io.BytesIO(audio_data), 'audio/webm')
        }
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/fake_call_123/live-transcribe",
            files=files,
            data={"chunk_index": 0},
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        # Should return 404 for non-existent call
        assert response.status_code in [404, 403], f"Unexpected status: {response.status_code}"
        print(f"✓ Live transcribe endpoint returns {response.status_code} for non-existent call")
    
    def test_12_recording_start_endpoint(self):
        """Test recording start endpoint"""
        self.test_token, _ = self.login_user(TEST_USER["email"], TEST_USER["password"])
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/fake_call_123/recording/start",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        # Should return 404 for non-existent call
        assert response.status_code == 404, f"Unexpected status: {response.status_code}"
        print(f"✓ Recording start endpoint returns 404 for non-existent call")
    
    def test_13_recording_stop_endpoint(self):
        """Test recording stop endpoint"""
        self.test_token, _ = self.login_user(TEST_USER["email"], TEST_USER["password"])
        
        response = self.session.post(
            f"{BASE_URL}/api/calls/fake_call_123/recording/stop",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        # Should return 404 for non-existent call
        assert response.status_code == 404, f"Unexpected status: {response.status_code}"
        print(f"✓ Recording stop endpoint returns 404 for non-existent call")
    
    def test_14_get_call_recordings(self):
        """Test get call recordings endpoint"""
        self.test_token, _ = self.login_user(TEST_USER["email"], TEST_USER["password"])
        
        response = self.session.get(
            f"{BASE_URL}/api/calls/fake_call_123/recordings",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        # Should return 404 for non-existent call
        assert response.status_code == 404, f"Unexpected status: {response.status_code}"
        print(f"✓ Get recordings endpoint returns 404 for non-existent call")
    
    def test_15_get_my_recordings(self):
        """Test get my recordings endpoint"""
        self.test_token, _ = self.login_user(TEST_USER["email"], TEST_USER["password"])
        
        response = self.session.get(
            f"{BASE_URL}/api/calls/recordings/my",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "recordings" in data
        print(f"✓ Get my recordings: {len(data.get('recordings', []))} recordings")
    
    def test_16_search_transcripts(self):
        """Test search transcripts endpoint"""
        self.test_token, _ = self.login_user(TEST_USER["email"], TEST_USER["password"])
        
        response = self.session.get(
            f"{BASE_URL}/api/calls/transcripts/search",
            params={"query": "test", "limit": 10},
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query" in data
        print(f"✓ Search transcripts: {data.get('total_results', 0)} results")


class TestLiveTranscriptionWithRealCall:
    """Test live transcription with a real call (if possible)"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.test_token = None
        self.attorney_token = None
        self.test_user_id = None
        self.attorney_user_id = None
        self.call_id = None
    
    def login_user(self, email, password):
        """Login and return token and user_id"""
        response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get("token"), data.get("user", {}).get("user_id")
        return None, None
    
    def test_01_create_call_and_test_live_features(self):
        """Create a call and test live transcription features"""
        # Login both users
        self.test_token, self.test_user_id = self.login_user(
            TEST_USER["email"], TEST_USER["password"]
        )
        self.attorney_token, self.attorney_user_id = self.login_user(
            ATTORNEY_USER["email"], ATTORNEY_USER["password"]
        )
        
        assert self.test_token is not None, "Failed to login test user"
        assert self.attorney_token is not None, "Failed to login attorney user"
        
        # First, end any existing calls
        active_response = self.session.get(
            f"{BASE_URL}/api/calls/active",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        if active_response.status_code == 200:
            active_data = active_response.json()
            if active_data.get("has_active_call"):
                existing_call_id = active_data["call"]["call_id"]
                self.session.post(
                    f"{BASE_URL}/api/calls/{existing_call_id}/end",
                    headers={"Authorization": f"Bearer {self.test_token}"}
                )
                print(f"  Ended existing call: {existing_call_id}")
        
        # Initiate new call
        response = self.session.post(
            f"{BASE_URL}/api/calls/initiate",
            data={
                "recipient_id": self.attorney_user_id,
                "call_type": "video"
            },
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        
        if response.status_code not in [200, 201]:
            pytest.skip(f"Could not initiate call: {response.status_code} - {response.text}")
        
        data = response.json()
        self.call_id = data.get("call_id")
        assert self.call_id is not None
        print(f"✓ Call initiated: {self.call_id}")
        
        # Test live transcript endpoint with real call
        transcript_response = self.session.get(
            f"{BASE_URL}/api/calls/{self.call_id}/live-transcript",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        assert transcript_response.status_code == 200
        transcript_data = transcript_response.json()
        assert "segments" in transcript_data
        assert "notes" in transcript_data
        print(f"✓ Live transcript retrieved: {len(transcript_data.get('segments', []))} segments")
        
        # Test adding a live note
        note_response = self.session.post(
            f"{BASE_URL}/api/calls/{self.call_id}/live-note",
            data={
                "content": "Test note during call",
                "timestamp": 10.5,
                "note_type": "important"
            },
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        assert note_response.status_code == 200
        note_data = note_response.json()
        assert note_data.get("success") == True
        assert "note" in note_data
        assert note_data["note"]["content"] == "Test note during call"
        assert note_data["note"]["note_type"] == "important"
        print(f"✓ Live note added: {note_data['note']['note_id']}")
        
        # Verify note appears in transcript
        transcript_response2 = self.session.get(
            f"{BASE_URL}/api/calls/{self.call_id}/live-transcript",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        assert transcript_response2.status_code == 200
        transcript_data2 = transcript_response2.json()
        assert len(transcript_data2.get("notes", [])) > 0
        print(f"✓ Note appears in transcript: {len(transcript_data2.get('notes', []))} notes")
        
        # Test save live transcript
        save_response = self.session.post(
            f"{BASE_URL}/api/calls/{self.call_id}/save-live-transcript",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        assert save_response.status_code == 200
        save_data = save_response.json()
        assert save_data.get("success") == True
        print(f"✓ Live transcript saved")
        
        # End the call
        end_response = self.session.post(
            f"{BASE_URL}/api/calls/{self.call_id}/end",
            headers={"Authorization": f"Bearer {self.test_token}"}
        )
        assert end_response.status_code == 200
        print(f"✓ Call ended")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
