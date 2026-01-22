"""
Video Streaming Feature Tests (v5.4.0)
Tests for video chunks and video streaming endpoints in SharedEncounterView
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials and encounter data
TEST_EMAIL = "modtest2@test.com"
TEST_PASSWORD = "Test123!"
TEST_ENCOUNTER_ID = "enc_e6692f1e966b"
TEST_SHARE_TOKEN = "adbe232a15954e11"


class TestHealthEndpoint:
    """Health endpoint tests for video_streaming feature"""
    
    def test_health_shows_video_streaming_enabled(self):
        """Health endpoint should show video_streaming feature enabled"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["version"] == "5.4.0"
        assert data["features"]["video_streaming"] == True
        assert data["features"]["real_time_sharing"] == True
        assert data["features"]["live_guidance"] == True
        print("✓ Health endpoint shows video_streaming enabled (v5.4.0)")


class TestVideoChunksEndpoint:
    """Tests for GET /api/encounters/shared/{id}/video/chunks endpoint"""
    
    def test_get_video_chunks_with_valid_token(self):
        """Get video chunks with valid share token returns chunk list"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/video/chunks",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["encounter_id"] == TEST_ENCOUNTER_ID
        assert "total_chunks" in data
        assert "chunk_duration_seconds" in data
        assert data["chunk_duration_seconds"] == 15
        assert "chunks" in data
        assert isinstance(data["chunks"], list)
        assert data["status"] in ["active", "completed"]
        
        # Verify chunk structure if chunks exist
        if data["total_chunks"] > 0:
            chunk = data["chunks"][0]
            assert "index" in chunk
            assert "filename" in chunk
            assert "timestamp_seconds" in chunk
            assert chunk["filename"].startswith("video_chunk_")
            assert chunk["filename"].endswith(".webm")
        
        print(f"✓ Video chunks endpoint returns {data['total_chunks']} chunks")
    
    def test_get_video_chunks_with_invalid_token(self):
        """Get video chunks with invalid token returns 403"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/video/chunks",
            params={"token": "invalid_token_12345"}
        )
        assert response.status_code == 403
        
        data = response.json()
        assert "detail" in data
        assert "Invalid" in data["detail"] or "expired" in data["detail"]
        print("✓ Video chunks endpoint rejects invalid token (403)")
    
    def test_get_video_chunks_nonexistent_encounter(self):
        """Get video chunks for non-existent encounter returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/enc_nonexistent123/video/chunks",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        print("✓ Video chunks endpoint returns 404 for non-existent encounter")
    
    def test_get_video_chunks_without_token(self):
        """Get video chunks without token returns 422 (validation error)"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/video/chunks"
        )
        # Should return 422 for missing required query param
        assert response.status_code == 422
        print("✓ Video chunks endpoint requires token parameter (422)")


class TestVideoChunkFileEndpoint:
    """Tests for GET /api/encounters/shared/{id}/video/{filename} endpoint"""
    
    def test_get_video_chunk_file_with_valid_token(self):
        """Get specific video chunk file with valid token returns video"""
        # First get the chunks to find a valid filename
        chunks_response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/video/chunks",
            params={"token": TEST_SHARE_TOKEN}
        )
        
        if chunks_response.status_code == 200:
            data = chunks_response.json()
            if data["total_chunks"] > 0:
                filename = data["chunks"][0]["filename"]
                
                response = requests.get(
                    f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/video/{filename}",
                    params={"token": TEST_SHARE_TOKEN}
                )
                assert response.status_code == 200
                assert response.headers.get("content-type") == "video/webm"
                assert "Cache-Control" in response.headers
                print(f"✓ Video chunk file endpoint returns video/webm for {filename}")
            else:
                pytest.skip("No video chunks available for testing")
        else:
            pytest.skip("Could not get video chunks list")
    
    def test_get_video_chunk_file_with_invalid_token(self):
        """Get video chunk file with invalid token returns 403"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/video/video_chunk_0.webm",
            params={"token": "invalid_token_12345"}
        )
        assert response.status_code == 403
        
        data = response.json()
        assert "detail" in data
        print("✓ Video chunk file endpoint rejects invalid token (403)")
    
    def test_get_video_chunk_file_nonexistent(self):
        """Get non-existent video chunk file returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/video/video_chunk_999.webm",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
        print("✓ Video chunk file endpoint returns 404 for non-existent file")
    
    def test_get_video_chunk_file_invalid_filename(self):
        """Get video chunk with invalid filename format returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/video/malicious_file.exe",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 404
        print("✓ Video chunk file endpoint rejects invalid filenames (404)")


class TestVideoChunkMetadata:
    """Tests for video chunk metadata and structure"""
    
    def test_chunk_timestamp_calculation(self):
        """Verify chunk timestamps are calculated correctly (15 sec intervals)"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/video/chunks",
            params={"token": TEST_SHARE_TOKEN}
        )
        
        if response.status_code == 200:
            data = response.json()
            for chunk in data["chunks"]:
                expected_timestamp = chunk["index"] * 15
                assert chunk["timestamp_seconds"] == expected_timestamp, \
                    f"Chunk {chunk['index']} should have timestamp {expected_timestamp}, got {chunk['timestamp_seconds']}"
            print("✓ Chunk timestamps calculated correctly (15 sec intervals)")
        else:
            pytest.skip("Could not get video chunks")
    
    def test_chunks_sorted_by_index(self):
        """Verify chunks are returned sorted by index"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}/video/chunks",
            params={"token": TEST_SHARE_TOKEN}
        )
        
        if response.status_code == 200:
            data = response.json()
            chunks = data["chunks"]
            if len(chunks) > 1:
                for i in range(1, len(chunks)):
                    assert chunks[i]["index"] > chunks[i-1]["index"], \
                        "Chunks should be sorted by index"
            print("✓ Chunks are sorted by index")
        else:
            pytest.skip("Could not get video chunks")


class TestSharedEncounterWithVideo:
    """Tests for shared encounter endpoint including video data"""
    
    def test_shared_encounter_returns_media_info(self):
        """Shared encounter endpoint should return encounter with media info"""
        response = requests.get(
            f"{BASE_URL}/api/encounters/shared/{TEST_ENCOUNTER_ID}",
            params={"token": TEST_SHARE_TOKEN}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["encounter_id"] == TEST_ENCOUNTER_ID
        assert "status" in data
        assert "location" in data
        assert "transcriptions" in data
        print("✓ Shared encounter endpoint returns encounter data")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
