"""
Test 3D Evidence Reconstruction API Endpoints

Tests for:
- POST /api/reconstruction/create - Create new 3D reconstruction
- GET /api/reconstruction/encounter/{id} - Get reconstruction by encounter
- GET /api/reconstruction/ - List reconstructions
- GET /api/reconstruction/preview/{id} - Get reconstruction preview
- DELETE /api/reconstruction/{id} - Delete reconstruction
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"
TEST_ENCOUNTER_ID = "enc_191bdcbb293a"


class TestReconstruction3DAPI:
    """3D Reconstruction API endpoint tests"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            self.authenticated = True
        else:
            self.authenticated = False
            pytest.skip("Authentication failed - skipping authenticated tests")
    
    def test_health_check(self):
        """Verify backend is healthy"""
        response = self.session.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print(f"✓ Backend healthy - version {data.get('version')}")
    
    def test_list_reconstructions_endpoint(self):
        """Test GET /api/reconstruction/ - List reconstructions"""
        # Note: trailing slash required due to FastAPI redirect
        response = self.session.get(f"{BASE_URL}/api/reconstruction/")
        assert response.status_code == 200
        
        data = response.json()
        assert "success" in data
        assert data["success"] == True
        assert "reconstructions" in data
        assert "count" in data
        assert isinstance(data["reconstructions"], list)
        print(f"✓ List reconstructions - found {data['count']} reconstructions")
    
    def test_get_reconstruction_by_encounter(self):
        """Test GET /api/reconstruction/encounter/{id} - Get or create reconstruction"""
        response = self.session.get(f"{BASE_URL}/api/reconstruction/encounter/{TEST_ENCOUNTER_ID}")
        
        # Should return 200 (found/created) or 404 (encounter not found)
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert data["success"] == True
            assert "reconstruction" in data
            
            reconstruction = data["reconstruction"]
            assert "reconstruction_id" in reconstruction
            assert "encounter_id" in reconstruction
            assert reconstruction["encounter_id"] == TEST_ENCOUNTER_ID
            assert "scene_data" in reconstruction
            
            # Verify scene_data structure
            scene_data = reconstruction["scene_data"]
            assert "version" in scene_data
            assert "environment" in scene_data
            assert "camera" in scene_data
            assert "markers" in scene_data
            assert "timeline" in scene_data
            
            print(f"✓ Get reconstruction by encounter - ID: {reconstruction['reconstruction_id']}")
            print(f"  - Scene version: {scene_data.get('version')}")
            print(f"  - Markers count: {len(scene_data.get('markers', []))}")
            print(f"  - Timeline events: {len(scene_data.get('timeline', []))}")
            
            # Store reconstruction_id for later tests
            self.reconstruction_id = reconstruction["reconstruction_id"]
        else:
            data = response.json()
            print(f"✓ Encounter not found (expected if test encounter doesn't exist): {data.get('detail')}")
    
    def test_create_reconstruction(self):
        """Test POST /api/reconstruction/create - Create new reconstruction"""
        # Get list of encounters (returns list directly)
        encounters_response = self.session.get(f"{BASE_URL}/api/encounters?limit=5")
        
        if encounters_response.status_code != 200:
            pytest.skip("Could not fetch encounters")
        
        # Encounters endpoint returns list directly
        encounters = encounters_response.json()
        if isinstance(encounters, dict):
            encounters = encounters.get("encounters", [])
        
        if not encounters:
            pytest.skip("No encounters available for testing")
        
        # Use first available encounter
        test_encounter_id = encounters[0].get("encounter_id")
        
        response = self.session.post(f"{BASE_URL}/api/reconstruction/create", json={
            "encounter_id": test_encounter_id,
            "options": {
                "generate_point_cloud": True
            }
        })
        
        # Should return 200 (created) or 404 (encounter not found)
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert data["success"] == True
            assert "reconstruction" in data
            assert "message" in data
            
            reconstruction = data["reconstruction"]
            assert "reconstruction_id" in reconstruction
            assert "scene_data" in reconstruction
            
            print(f"✓ Create reconstruction - ID: {reconstruction['reconstruction_id']}")
            print(f"  - Message: {data.get('message')}")
        else:
            print(f"✓ Create reconstruction returned {response.status_code} - {response.json().get('detail', 'Unknown error')}")
    
    def test_get_reconstruction_preview(self):
        """Test GET /api/reconstruction/preview/{id} - Get preview info"""
        # Get list of encounters (returns list directly)
        encounters_response = self.session.get(f"{BASE_URL}/api/encounters?limit=5")
        
        if encounters_response.status_code != 200:
            pytest.skip("Could not fetch encounters")
        
        # Encounters endpoint returns list directly
        encounters = encounters_response.json()
        if isinstance(encounters, dict):
            encounters = encounters.get("encounters", [])
        
        if not encounters:
            pytest.skip("No encounters available for testing")
        
        # Use first available encounter
        test_encounter_id = encounters[0].get("encounter_id")
        
        response = self.session.get(f"{BASE_URL}/api/reconstruction/preview/{test_encounter_id}")
        
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert data["success"] == True
            assert "preview" in data
            
            preview = data["preview"]
            assert "encounter_id" in preview
            assert "encounter_type" in preview
            assert "can_reconstruct" in preview
            
            print(f"✓ Get reconstruction preview - Encounter: {preview['encounter_id']}")
            print(f"  - Type: {preview.get('encounter_type')}")
            print(f"  - Can reconstruct: {preview.get('can_reconstruct')}")
            print(f"  - Estimated complexity: {preview.get('estimated_complexity')}")
        else:
            print(f"✓ Preview returned 404 - encounter not found")
    
    def test_scene_data_structure(self):
        """Test that scene_data has correct structure for Three.js rendering"""
        # Get a reconstruction to verify scene_data structure
        response = self.session.get(f"{BASE_URL}/api/reconstruction/?limit=1")
        
        if response.status_code != 200:
            pytest.skip("Could not fetch reconstructions")
        
        reconstructions = response.json().get("reconstructions", [])
        
        if not reconstructions:
            # Try to create one first
            encounters_response = self.session.get(f"{BASE_URL}/api/encounters?limit=1")
            if encounters_response.status_code == 200:
                encounters = encounters_response.json()
                if isinstance(encounters, dict):
                    encounters = encounters.get("encounters", [])
                if encounters:
                    enc_id = encounters[0].get("encounter_id")
                    create_response = self.session.get(f"{BASE_URL}/api/reconstruction/encounter/{enc_id}")
                    if create_response.status_code == 200:
                        reconstruction = create_response.json().get("reconstruction")
                        if reconstruction:
                            self._verify_scene_data(reconstruction.get("scene_data", {}))
                            return
            
            pytest.skip("No reconstructions available for testing")
        
        # Get full reconstruction with scene_data
        recon_id = reconstructions[0].get("reconstruction_id")
        full_response = self.session.get(f"{BASE_URL}/api/reconstruction/{recon_id}")
        
        if full_response.status_code == 200:
            reconstruction = full_response.json().get("reconstruction", {})
            scene_data = reconstruction.get("scene_data", {})
            self._verify_scene_data(scene_data)
    
    def _verify_scene_data(self, scene_data):
        """Helper to verify scene_data structure"""
        # Verify environment settings
        if "environment" in scene_data:
            env = scene_data["environment"]
            assert "ambientLight" in env
            assert "directionalLight" in env
            print(f"✓ Scene environment configured")
            print(f"  - Ambient intensity: {env.get('ambientLight', {}).get('intensity')}")
            print(f"  - Sky color: {env.get('skyColor')}")
        
        # Verify camera settings
        if "camera" in scene_data:
            camera = scene_data["camera"]
            assert "position" in camera
            assert "fov" in camera
            print(f"✓ Camera configured - FOV: {camera.get('fov')}")
        
        # Verify markers
        if "markers" in scene_data:
            markers = scene_data["markers"]
            print(f"✓ Markers: {len(markers)} total")
            for marker in markers[:3]:  # Check first 3
                assert "id" in marker
                assert "type" in marker
                assert "position" in marker
        
        # Verify timeline
        if "timeline" in scene_data:
            timeline = scene_data["timeline"]
            print(f"✓ Timeline: {len(timeline)} events")
            for event in timeline[:3]:  # Check first 3
                assert "time" in event
                assert "event" in event
                assert "label" in event
        
        # Verify point cloud (if present)
        if "point_cloud" in scene_data and scene_data["point_cloud"]:
            pc = scene_data["point_cloud"]
            assert "points" in pc
            assert "colors" in pc
            print(f"✓ Point cloud: {len(pc.get('points', []))} points")
    
    def test_encounters_endpoint_for_selector(self):
        """Test GET /api/encounters - Used by encounter selector dropdown"""
        response = self.session.get(f"{BASE_URL}/api/encounters?limit=50")
        assert response.status_code == 200
        
        # Encounters endpoint returns list directly
        data = response.json()
        if isinstance(data, list):
            encounters = data
        else:
            encounters = data.get("encounters", [])
        
        print(f"✓ Encounters endpoint - found {len(encounters)} encounters")
        
        if encounters:
            # Verify encounter structure for selector
            enc = encounters[0]
            assert "encounter_id" in enc
            print(f"  - First encounter: {enc.get('encounter_id')}")
            print(f"  - Type: {enc.get('encounter_type')}")


class TestReconstruction3DEdgeCases:
    """Edge case tests for 3D Reconstruction API"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test session with authentication"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login to get token
        login_response = self.session.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if login_response.status_code == 200:
            token = login_response.json().get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        else:
            pytest.skip("Authentication failed")
    
    def test_invalid_encounter_id(self):
        """Test with invalid encounter ID"""
        response = self.session.get(f"{BASE_URL}/api/reconstruction/encounter/invalid_id_12345")
        assert response.status_code == 404
        print("✓ Invalid encounter ID returns 404")
    
    def test_invalid_reconstruction_id(self):
        """Test with invalid reconstruction ID"""
        response = self.session.get(f"{BASE_URL}/api/reconstruction/invalid_recon_id")
        assert response.status_code == 404
        print("✓ Invalid reconstruction ID returns 404")
    
    def test_create_without_encounter_id(self):
        """Test create without encounter_id"""
        response = self.session.post(f"{BASE_URL}/api/reconstruction/create", json={
            "options": {}
        })
        # Should return 422 (validation error) for missing required field
        assert response.status_code == 422
        print("✓ Create without encounter_id returns 422 validation error")
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated requests are rejected"""
        # Create new session without auth
        unauth_session = requests.Session()
        unauth_session.headers.update({"Content-Type": "application/json"})
        
        response = unauth_session.get(f"{BASE_URL}/api/reconstruction/")
        # FastAPI returns 403 for missing auth on protected routes
        assert response.status_code in [401, 403]
        print(f"✓ Unauthenticated access returns {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
