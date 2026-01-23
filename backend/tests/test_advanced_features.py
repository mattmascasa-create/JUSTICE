"""
Test Advanced Features APIs - Violation Detection, Legal Precedent, FOIA Automation
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAdvancedFeaturesAPIs:
    """Test Advanced Features endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        # Login to get token
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    # ============== VIOLATION DETECTION TESTS ==============
    
    def test_violation_analyze_endpoint(self):
        """Test POST /api/advanced/violations/analyze"""
        response = requests.post(
            f"{BASE_URL}/api/advanced/violations/analyze",
            headers=self.headers,
            json={
                "encounter_id": "test_encounter_123",
                "transcript": "Officer said: I need to search your car without a warrant. You have to let me search.",
                "encounter_type": "traffic_stop"
            }
        )
        
        assert response.status_code == 200, f"Violation analyze failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "analysis_id" in data, "Missing analysis_id in response"
        assert "violations" in data, "Missing violations in response"
        assert "encounter_id" in data, "Missing encounter_id in response"
        assert data["encounter_id"] == "test_encounter_123"
        
        # If violations found, verify structure
        if data.get("violations"):
            violation = data["violations"][0]
            assert "amendment_violated" in violation or "violation_type" in violation
            print(f"Found {len(data['violations'])} violations")
    
    def test_violation_quick_scan_endpoint(self):
        """Test POST /api/advanced/violations/quick-scan"""
        response = requests.post(
            f"{BASE_URL}/api/advanced/violations/quick-scan",
            headers=self.headers,
            params={"transcript": "Officer grabbed me and pushed me against the wall"}
        )
        
        assert response.status_code == 200, f"Quick scan failed: {response.text}"
        data = response.json()
        
        assert "flags" in data, "Missing flags in response"
        assert "count" in data, "Missing count in response"
        print(f"Quick scan found {data['count']} flags")
    
    def test_violation_stats_endpoint(self):
        """Test GET /api/advanced/violations/stats"""
        response = requests.get(
            f"{BASE_URL}/api/advanced/violations/stats",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Violation stats failed: {response.text}"
        data = response.json()
        
        assert "total_analyses" in data, "Missing total_analyses in response"
    
    # ============== LEGAL PRECEDENT TESTS ==============
    
    def test_legal_precedents_endpoint(self):
        """Test POST /api/advanced/legal/precedents"""
        response = requests.post(
            f"{BASE_URL}/api/advanced/legal/precedents",
            headers=self.headers,
            json={
                "encounter_id": "test_encounter_123",
                "violations": [
                    {"type": "4th Amendment", "severity": 7, "violation_type": "Warrantless Search"}
                ],
                "transcript": "Officer searched my car without a warrant or consent",
                "encounter_type": "traffic_stop"
            }
        )
        
        assert response.status_code == 200, f"Legal precedents failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "search_id" in data or "matching_precedents" in data, "Missing expected fields in response"
        assert "encounter_id" in data, "Missing encounter_id in response"
        
        if data.get("matching_precedents"):
            precedent = data["matching_precedents"][0]
            assert "case_name" in precedent, "Missing case_name in precedent"
            print(f"Found {len(data['matching_precedents'])} matching precedents")
    
    def test_legal_cases_by_amendment_endpoint(self):
        """Test GET /api/advanced/legal/cases/{amendment}"""
        response = requests.get(
            f"{BASE_URL}/api/advanced/legal/cases/4th",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Cases by amendment failed: {response.text}"
        data = response.json()
        
        assert "cases" in data, "Missing cases in response"
        assert "count" in data, "Missing count in response"
        print(f"Found {data['count']} cases for 4th Amendment")
    
    def test_legal_search_cases_endpoint(self):
        """Test POST /api/advanced/legal/search"""
        response = requests.post(
            f"{BASE_URL}/api/advanced/legal/search",
            headers=self.headers,
            json=["search", "warrant", "vehicle"]
        )
        
        assert response.status_code == 200, f"Legal search failed: {response.text}"
        data = response.json()
        
        assert "results" in data, "Missing results in response"
        assert "count" in data, "Missing count in response"
    
    def test_legal_estimate_value_endpoint(self):
        """Test POST /api/advanced/legal/estimate-value"""
        response = requests.post(
            f"{BASE_URL}/api/advanced/legal/estimate-value",
            headers=self.headers,
            json={
                "violations": [
                    {"type": "4th Amendment", "severity": 7}
                ],
                "has_injury": False,
                "has_arrest": False,
                "has_video": True
            }
        )
        
        assert response.status_code == 200, f"Estimate value failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "low_estimate" in data, "Missing low_estimate in response"
        assert "mid_estimate" in data, "Missing mid_estimate in response"
        assert "high_estimate" in data, "Missing high_estimate in response"
        assert "factors" in data, "Missing factors in response"
        assert "disclaimer" in data, "Missing disclaimer in response"
        
        # Verify values are reasonable
        assert data["low_estimate"] > 0, "Low estimate should be positive"
        assert data["mid_estimate"] >= data["low_estimate"], "Mid estimate should be >= low"
        assert data["high_estimate"] >= data["mid_estimate"], "High estimate should be >= mid"
        
        print(f"Case value estimate: ${data['low_estimate']:,} - ${data['high_estimate']:,}")
    
    # ============== FOIA AUTOMATION TESTS ==============
    
    def test_foia_generate_endpoint_no_encounter(self):
        """Test POST /api/advanced/foia/generate with non-existent encounter"""
        response = requests.post(
            f"{BASE_URL}/api/advanced/foia/generate",
            headers=self.headers,
            json={
                "encounter_id": "non_existent_encounter"
            }
        )
        
        # Should return 200 with error message since encounter doesn't exist
        assert response.status_code == 200, f"FOIA generate failed: {response.text}"
        data = response.json()
        
        # Should have error since encounter doesn't exist
        assert "error" in data, "Expected error for non-existent encounter"
        assert data["error"] == "Encounter not found"
    
    def test_foia_my_requests_endpoint(self):
        """Test GET /api/advanced/foia/my-requests"""
        response = requests.get(
            f"{BASE_URL}/api/advanced/foia/my-requests",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"FOIA my-requests failed: {response.text}"
        data = response.json()
        
        assert "requests" in data, "Missing requests in response"
        assert "count" in data, "Missing count in response"
        print(f"User has {data['count']} FOIA requests")
    
    def test_foia_stats_endpoint(self):
        """Test GET /api/advanced/foia/stats"""
        response = requests.get(
            f"{BASE_URL}/api/advanced/foia/stats",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"FOIA stats failed: {response.text}"
        data = response.json()
        
        assert "total_requests" in data, "Missing total_requests in response"
        assert "by_status" in data, "Missing by_status in response"
    
    # ============== DEAD MAN'S SWITCH TESTS ==============
    
    def test_dms_config_get_endpoint(self):
        """Test GET /api/advanced/dead-mans-switch/config"""
        response = requests.get(
            f"{BASE_URL}/api/advanced/dead-mans-switch/config",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"DMS config get failed: {response.text}"
        data = response.json()
        
        # Verify config structure
        assert "enabled" in data, "Missing enabled in config"
        assert "inactivity_threshold" in data, "Missing inactivity_threshold in config"
        assert "warning_time" in data, "Missing warning_time in config"
    
    def test_dms_config_update_endpoint(self):
        """Test PUT /api/advanced/dead-mans-switch/config"""
        response = requests.put(
            f"{BASE_URL}/api/advanced/dead-mans-switch/config",
            headers=self.headers,
            json={
                "enabled": True,
                "inactivity_threshold": 60,
                "warning_time": 45,
                "auto_broadcast": True,
                "notify_emergency_contacts": True,
                "notify_witness_network": False,
                "auto_upload": True
            }
        )
        
        assert response.status_code == 200, f"DMS config update failed: {response.text}"
        data = response.json()
        
        assert data.get("enabled") == True, "Config not updated correctly"
    
    # ============== WITNESS NETWORK TESTS ==============
    
    def test_witness_stats_endpoint(self):
        """Test GET /api/advanced/witness/stats"""
        response = requests.get(
            f"{BASE_URL}/api/advanced/witness/stats",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Witness stats failed: {response.text}"
        data = response.json()
        
        assert "total_witnessed" in data, "Missing total_witnessed in response"
        assert "recordings_submitted" in data, "Missing recordings_submitted in response"
        assert "reputation_score" in data, "Missing reputation_score in response"


class TestAdvancedFeaturesEdgeCases:
    """Test edge cases and error handling"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "test@example.com", "password": "password123"}
        )
        self.token = response.json().get("access_token")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def test_violation_analyze_empty_transcript(self):
        """Test violation analysis with empty transcript"""
        response = requests.post(
            f"{BASE_URL}/api/advanced/violations/analyze",
            headers=self.headers,
            json={
                "encounter_id": "test_empty",
                "transcript": "",
                "encounter_type": "general"
            }
        )
        
        # Should still return 200 but with no violations
        assert response.status_code == 200
        data = response.json()
        assert "violations" in data
    
    def test_legal_estimate_with_high_severity_violations(self):
        """Test case value estimation with high severity violations"""
        response = requests.post(
            f"{BASE_URL}/api/advanced/legal/estimate-value",
            headers=self.headers,
            json={
                "violations": [
                    {"type": "4th Amendment", "severity": 9},
                    {"type": "8th Amendment", "severity": 10}
                ],
                "has_injury": True,
                "has_arrest": True,
                "has_video": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # High severity + injury + arrest + video should give high estimate
        assert data["high_estimate"] > 100000, "High severity case should have high estimate"
        print(f"High severity case estimate: ${data['low_estimate']:,} - ${data['high_estimate']:,}")
    
    def test_unauthorized_access(self):
        """Test endpoints without authentication"""
        response = requests.get(
            f"{BASE_URL}/api/advanced/violations/stats"
        )
        
        # Should return 401 or 403
        assert response.status_code in [401, 403], "Should require authentication"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
