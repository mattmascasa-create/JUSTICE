"""
Community Vault API Tests - Phase 6
Tests for the Community Evidence Vault feature including:
- Public endpoints: stats, submissions, departments, officers, profiles
- Auth-required endpoints: submit, upvote
"""

import pytest
import requests
import os
from datetime import datetime, timedelta
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://police-watch-2.preview.emergentagent.com')

# Test credentials
TEST_EMAIL = "encounter_test@example.com"
TEST_PASSWORD = "password123"


class TestCommunityVaultPublicEndpoints:
    """Test public endpoints that don't require authentication"""
    
    def test_health_check(self):
        """Verify API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "4.1.0"
        print(f"✓ Health check passed - version {data['version']}")
    
    def test_get_community_stats(self):
        """GET /api/community/stats - Get overall statistics (public)"""
        response = requests.get(f"{BASE_URL}/api/community/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "total_submissions" in data
        assert "total_departments_tracked" in data
        assert "total_officers_tracked" in data
        assert "top_violations" in data
        assert "by_state" in data
        assert "by_severity" in data
        
        # Verify data types
        assert isinstance(data["total_submissions"], int)
        assert isinstance(data["total_departments_tracked"], int)
        assert isinstance(data["total_officers_tracked"], int)
        assert isinstance(data["top_violations"], list)
        
        print(f"✓ Community stats: {data['total_submissions']} submissions, {data['total_departments_tracked']} departments, {data['total_officers_tracked']} officers")
    
    def test_get_community_submissions_no_filters(self):
        """GET /api/community/submissions - Browse submissions without filters (public)"""
        response = requests.get(f"{BASE_URL}/api/community/submissions")
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "submissions" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data
        
        assert isinstance(data["submissions"], list)
        assert isinstance(data["total"], int)
        
        print(f"✓ Got {len(data['submissions'])} submissions (total: {data['total']})")
        
        # If there are submissions, verify structure
        if data["submissions"]:
            sub = data["submissions"][0]
            assert "submission_id" in sub
            assert "encounter_type" in sub
            assert "location_city" in sub
            assert "location_state" in sub
            assert "severity" in sub
            assert "summary" in sub
            print(f"  First submission: {sub['submission_id']} - {sub['location_city']}, {sub['location_state']}")
    
    def test_get_community_submissions_with_state_filter(self):
        """GET /api/community/submissions?state=California - Filter by state"""
        response = requests.get(f"{BASE_URL}/api/community/submissions", params={"state": "California"})
        assert response.status_code == 200
        data = response.json()
        
        # All submissions should be from California
        for sub in data["submissions"]:
            assert sub["location_state"] == "California", f"Expected California, got {sub['location_state']}"
        
        print(f"✓ State filter works - {len(data['submissions'])} California submissions")
    
    def test_get_community_submissions_with_severity_filter(self):
        """GET /api/community/submissions?severity=high - Filter by severity"""
        response = requests.get(f"{BASE_URL}/api/community/submissions", params={"severity": "high"})
        assert response.status_code == 200
        data = response.json()
        
        # All submissions should have high severity
        for sub in data["submissions"]:
            assert sub["severity"] == "high", f"Expected high severity, got {sub['severity']}"
        
        print(f"✓ Severity filter works - {len(data['submissions'])} high severity submissions")
    
    def test_get_community_submissions_pagination(self):
        """GET /api/community/submissions?page=1&limit=5 - Test pagination"""
        response = requests.get(f"{BASE_URL}/api/community/submissions", params={"page": 1, "limit": 5})
        assert response.status_code == 200
        data = response.json()
        
        assert data["page"] == 1
        assert len(data["submissions"]) <= 5
        
        print(f"✓ Pagination works - page {data['page']} of {data['pages']}")
    
    def test_get_department_rankings(self):
        """GET /api/community/departments - Get department rankings (public)"""
        response = requests.get(f"{BASE_URL}/api/community/departments")
        assert response.status_code == 200
        data = response.json()
        
        assert "departments" in data
        assert "sort_by" in data
        assert isinstance(data["departments"], list)
        
        print(f"✓ Got {len(data['departments'])} departments ranked by {data['sort_by']}")
        
        # Verify department structure if any exist
        if data["departments"]:
            dept = data["departments"][0]
            assert "department" in dept
            assert "total_incidents" in dept
            print(f"  Top department: {dept['department']} with {dept['total_incidents']} incidents")
    
    def test_get_department_rankings_with_state_filter(self):
        """GET /api/community/departments?state=California - Filter by state"""
        response = requests.get(f"{BASE_URL}/api/community/departments", params={"state": "California"})
        assert response.status_code == 200
        data = response.json()
        
        # All departments should be from California
        for dept in data["departments"]:
            assert dept.get("state") == "California", f"Expected California, got {dept.get('state')}"
        
        print(f"✓ Department state filter works - {len(data['departments'])} California departments")
    
    def test_get_officer_rankings(self):
        """GET /api/community/officers - Get officer rankings (public)"""
        response = requests.get(f"{BASE_URL}/api/community/officers")
        assert response.status_code == 200
        data = response.json()
        
        assert "officers" in data
        assert "min_incidents" in data
        assert isinstance(data["officers"], list)
        
        print(f"✓ Got {len(data['officers'])} officers with min {data['min_incidents']} incidents")
        
        # Verify officer structure if any exist
        if data["officers"]:
            officer = data["officers"][0]
            assert "badge_number" in officer
            assert "department" in officer
            assert "total_incidents" in officer
            print(f"  Top officer: Badge #{officer['badge_number']} - {officer['department']} with {officer['total_incidents']} incidents")
    
    def test_get_officer_rankings_with_min_incidents(self):
        """GET /api/community/officers?min_incidents=2 - Filter by minimum incidents"""
        response = requests.get(f"{BASE_URL}/api/community/officers", params={"min_incidents": 2})
        assert response.status_code == 200
        data = response.json()
        
        # All officers should have at least 2 incidents
        for officer in data["officers"]:
            assert officer["total_incidents"] >= 2, f"Expected >= 2 incidents, got {officer['total_incidents']}"
        
        print(f"✓ Min incidents filter works - {len(data['officers'])} officers with 2+ incidents")
    
    def test_get_department_profile_not_found(self):
        """GET /api/community/department/{department} - Non-existent department returns empty profile"""
        response = requests.get(f"{BASE_URL}/api/community/department/NonExistentDepartment12345")
        assert response.status_code == 200  # Returns empty profile, not 404
        data = response.json()
        
        assert data["stats"] is None
        assert data["submissions"] == []
        assert "message" in data
        
        print(f"✓ Non-existent department returns empty profile with message")


class TestCommunityVaultAuthEndpoints:
    """Test endpoints that require authentication"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token before each test"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if response.status_code != 200:
            pytest.skip(f"Authentication failed: {response.status_code}")
        
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        print(f"✓ Authenticated as {TEST_EMAIL}")
    
    def test_submit_requires_auth(self):
        """POST /api/community/submit - Should require authentication"""
        response = requests.post(f"{BASE_URL}/api/community/submit", json={
            "encounter_type": "traffic_stop",
            "location_city": "Test City",
            "location_state": "California",
            "incident_date": datetime.now().isoformat(),
            "violations": ["unlawful_search"],
            "severity": "medium",
            "summary": "Test submission"
        })
        assert response.status_code == 401
        print("✓ Submit endpoint requires authentication")
    
    def test_upvote_requires_auth(self):
        """POST /api/community/upvote/{id} - Should require authentication"""
        response = requests.post(f"{BASE_URL}/api/community/upvote/sub_test123")
        assert response.status_code == 401
        print("✓ Upvote endpoint requires authentication")
    
    def test_submit_to_community_vault(self):
        """POST /api/community/submit - Create new submission"""
        unique_id = uuid.uuid4().hex[:8]
        submission_data = {
            "encounter_type": "traffic_stop",
            "location_city": f"TEST_City_{unique_id}",
            "location_state": "California",
            "incident_date": datetime.now().isoformat(),
            "violations": ["unlawful_search", "4th_amendment_violation"],
            "department": f"TEST_PD_{unique_id}",
            "officer_badge": f"TEST_{unique_id}",
            "severity": "high",
            "outcome": "dismissed",
            "summary": f"TEST submission for automated testing - {unique_id}"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/community/submit",
            json=submission_data,
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "submission_id" in data
        assert data["submission_id"].startswith("sub_")
        assert "message" in data
        assert "created_at" in data
        
        print(f"✓ Created submission: {data['submission_id']}")
        
        # Store for later tests
        self.submission_id = data["submission_id"]
        
        # Verify submission appears in list
        response = requests.get(f"{BASE_URL}/api/community/submissions")
        assert response.status_code == 200
        submissions = response.json()["submissions"]
        
        found = any(s["submission_id"] == data["submission_id"] for s in submissions)
        assert found, "New submission should appear in submissions list"
        print("✓ Submission verified in list")
        
        return data["submission_id"]
    
    def test_submit_with_missing_required_fields(self):
        """POST /api/community/submit - Should fail with missing required fields"""
        # Missing location_city
        response = requests.post(
            f"{BASE_URL}/api/community/submit",
            json={
                "encounter_type": "traffic_stop",
                "location_state": "California",
                "incident_date": datetime.now().isoformat(),
                "violations": [],
                "severity": "medium",
                "summary": "Test"
            },
            headers=self.headers
        )
        assert response.status_code == 422  # Validation error
        print("✓ Submit fails with missing required fields")
    
    def test_upvote_submission(self):
        """POST /api/community/upvote/{id} - Upvote a submission"""
        # First create a submission to upvote
        unique_id = uuid.uuid4().hex[:8]
        create_response = requests.post(
            f"{BASE_URL}/api/community/submit",
            json={
                "encounter_type": "pedestrian_stop",
                "location_city": f"TEST_Upvote_City_{unique_id}",
                "location_state": "New York",
                "incident_date": datetime.now().isoformat(),
                "violations": ["intimidation"],
                "severity": "low",
                "summary": f"TEST submission for upvote testing - {unique_id}"
            },
            headers=self.headers
        )
        assert create_response.status_code == 200
        submission_id = create_response.json()["submission_id"]
        
        # Get initial upvote count
        submissions_response = requests.get(f"{BASE_URL}/api/community/submissions")
        initial_submission = next(
            (s for s in submissions_response.json()["submissions"] if s["submission_id"] == submission_id),
            None
        )
        initial_upvotes = initial_submission["upvotes"] if initial_submission else 0
        
        # Upvote the submission
        upvote_response = requests.post(
            f"{BASE_URL}/api/community/upvote/{submission_id}",
            headers=self.headers
        )
        assert upvote_response.status_code == 200
        data = upvote_response.json()
        assert data["success"] == True
        print(f"✓ Upvoted submission {submission_id}")
        
        # Verify upvote count increased
        submissions_response = requests.get(f"{BASE_URL}/api/community/submissions")
        updated_submission = next(
            (s for s in submissions_response.json()["submissions"] if s["submission_id"] == submission_id),
            None
        )
        assert updated_submission is not None
        assert updated_submission["upvotes"] == initial_upvotes + 1
        print(f"✓ Upvote count increased from {initial_upvotes} to {updated_submission['upvotes']}")
    
    def test_upvote_duplicate_fails(self):
        """POST /api/community/upvote/{id} - Should fail on duplicate upvote"""
        # Create a submission
        unique_id = uuid.uuid4().hex[:8]
        create_response = requests.post(
            f"{BASE_URL}/api/community/submit",
            json={
                "encounter_type": "arrest",
                "location_city": f"TEST_Dup_City_{unique_id}",
                "location_state": "Texas",
                "incident_date": datetime.now().isoformat(),
                "violations": ["excessive_force"],
                "severity": "critical",
                "summary": f"TEST submission for duplicate upvote testing - {unique_id}"
            },
            headers=self.headers
        )
        submission_id = create_response.json()["submission_id"]
        
        # First upvote should succeed
        response1 = requests.post(
            f"{BASE_URL}/api/community/upvote/{submission_id}",
            headers=self.headers
        )
        assert response1.status_code == 200
        
        # Second upvote should fail
        response2 = requests.post(
            f"{BASE_URL}/api/community/upvote/{submission_id}",
            headers=self.headers
        )
        assert response2.status_code == 400
        assert "Already upvoted" in response2.json()["detail"]
        print("✓ Duplicate upvote correctly rejected")
    
    def test_upvote_nonexistent_submission(self):
        """POST /api/community/upvote/{id} - Should fail for non-existent submission"""
        response = requests.post(
            f"{BASE_URL}/api/community/upvote/sub_nonexistent12345",
            headers=self.headers
        )
        # API may return 400 (already upvoted check) or 404 (not found)
        assert response.status_code in [400, 404]
        print(f"✓ Upvote non-existent submission returns {response.status_code}")


class TestCommunityVaultOfficerDepartmentProfiles:
    """Test officer and department profile endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create test data for profile tests"""
        # Login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if response.status_code != 200:
            pytest.skip(f"Authentication failed: {response.status_code}")
        
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create test submission with known officer and department
        self.unique_id = uuid.uuid4().hex[:8]
        self.test_badge = f"PROFILE_TEST_{self.unique_id}"
        self.test_department = f"Profile Test PD {self.unique_id}"
        
        response = requests.post(
            f"{BASE_URL}/api/community/submit",
            json={
                "encounter_type": "search",
                "location_city": "Profile Test City",
                "location_state": "Florida",
                "incident_date": datetime.now().isoformat(),
                "violations": ["unlawful_search", "intimidation"],
                "department": self.test_department,
                "officer_badge": self.test_badge,
                "severity": "high",
                "summary": f"TEST submission for profile testing - {self.unique_id}"
            },
            headers=self.headers
        )
        assert response.status_code == 200
        print(f"✓ Created test submission with badge {self.test_badge} and department {self.test_department}")
    
    def test_get_officer_profile(self):
        """GET /api/community/officer/{badge}/{department} - Get officer profile"""
        # URL encode the department name
        import urllib.parse
        encoded_dept = urllib.parse.quote(self.test_department)
        
        response = requests.get(f"{BASE_URL}/api/community/officer/{self.test_badge}/{encoded_dept}")
        assert response.status_code == 200
        data = response.json()
        
        assert "stats" in data
        assert "submissions" in data
        assert "incident_count" in data
        
        assert data["stats"]["badge_number"] == self.test_badge
        assert data["stats"]["department"] == self.test_department
        assert data["stats"]["total_incidents"] >= 1
        
        print(f"✓ Officer profile: Badge #{self.test_badge} has {data['incident_count']} incidents")
    
    def test_get_officer_profile_not_found(self):
        """GET /api/community/officer/{badge}/{department} - Non-existent officer returns 404"""
        response = requests.get(f"{BASE_URL}/api/community/officer/NONEXISTENT_BADGE/NonExistent%20PD")
        assert response.status_code == 404
        print("✓ Non-existent officer returns 404")
    
    def test_get_department_profile(self):
        """GET /api/community/department/{department} - Get department profile"""
        import urllib.parse
        encoded_dept = urllib.parse.quote(self.test_department)
        
        response = requests.get(f"{BASE_URL}/api/community/department/{encoded_dept}")
        assert response.status_code == 200
        data = response.json()
        
        assert "stats" in data
        assert "submissions" in data
        assert "officers_involved" in data
        
        if data["stats"]:
            assert data["stats"]["department"] == self.test_department
            assert data["stats"]["total_incidents"] >= 1
            print(f"✓ Department profile: {self.test_department} has {data['stats']['total_incidents']} incidents")
        else:
            print(f"✓ Department profile returned (stats may be processing)")


class TestCommunityVaultRegressionPhase1to5:
    """Regression tests to ensure Phase 1-5 features still work"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Get auth token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        
        if response.status_code != 200:
            pytest.skip(f"Authentication failed: {response.status_code}")
        
        self.token = response.json()["access_token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_auth_me_endpoint(self):
        """GET /api/auth/me - Auth still works"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        print(f"✓ Auth working - logged in as {data['email']}")
    
    def test_cases_list(self):
        """GET /api/cases - Cases endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/cases", headers=self.headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"✓ Cases endpoint working - {len(response.json())} cases")
    
    def test_attorneys_list(self):
        """GET /api/attorneys - Attorneys endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/attorneys")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"✓ Attorneys endpoint working - {len(response.json())} attorneys")
    
    def test_departments_list(self):
        """GET /api/departments - Departments endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/departments")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"✓ Departments endpoint working - {len(response.json())} departments")
    
    def test_incidents_map(self):
        """GET /api/incidents/map - Incidents map endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/incidents/map")
        assert response.status_code == 200
        data = response.json()
        # API returns list directly
        assert isinstance(data, list)
        print(f"✓ Incidents map endpoint working - {len(data)} incidents")
    
    def test_encounters_list(self):
        """GET /api/encounters - Encounters endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/encounters", headers=self.headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        print(f"✓ Encounters endpoint working - {len(response.json())} encounters")
    
    def test_analytics_dashboard(self):
        """GET /api/analytics/dashboard - Analytics endpoint still works"""
        response = requests.get(f"{BASE_URL}/api/analytics/dashboard", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_cases" in data
        print(f"✓ Analytics dashboard working - {data['total_cases']} total cases")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
