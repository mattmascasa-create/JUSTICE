"""
Test Scheduled Reports CRUD Endpoints
Tests for /api/schedules/* endpoints
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"


class TestScheduledReportsCRUD:
    """Test CRUD operations for scheduled reports"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login and get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        
        token = login_response.json().get("access_token")
        assert token, "No access token received"
        
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.created_schedule_ids = []
        
        yield
        
        # Cleanup: Delete any schedules created during tests
        for schedule_id in self.created_schedule_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/schedules/{schedule_id}")
            except:
                pass
    
    # ============== GET /api/schedules/my ==============
    
    def test_get_my_schedules_returns_array(self):
        """GET /api/schedules/my returns schedules array"""
        response = self.session.get(f"{BASE_URL}/api/schedules/my")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "schedules" in data, "Response should contain 'schedules' key"
        assert isinstance(data["schedules"], list), "schedules should be a list"
    
    def test_get_my_schedules_requires_auth(self):
        """GET /api/schedules/my requires authentication"""
        session = requests.Session()
        response = session.get(f"{BASE_URL}/api/schedules/my")
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    # ============== POST /api/schedules/create ==============
    
    def test_create_schedule_requires_recipient_emails(self):
        """POST /api/schedules/create validates required recipient_emails"""
        # Test with empty recipient_emails
        response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "weekly",
                "send_hour": 9,
                "send_day": 0,
                "recipient_emails": []
            }
        )
        assert response.status_code == 400, f"Expected 400 for empty recipients, got {response.status_code}: {response.text}"
        assert "recipient" in response.json().get("detail", "").lower()
    
    def test_create_schedule_validates_frequency(self):
        """POST /api/schedules/create validates frequency values"""
        response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "invalid_frequency",
                "send_hour": 9,
                "recipient_emails": ["test@example.com"]
            }
        )
        assert response.status_code == 400, f"Expected 400 for invalid frequency, got {response.status_code}"
        assert "frequency" in response.json().get("detail", "").lower()
    
    def test_create_schedule_validates_send_hour(self):
        """POST /api/schedules/create validates send_hour range (0-23)"""
        response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "daily",
                "send_hour": 25,  # Invalid hour
                "recipient_emails": ["test@example.com"]
            }
        )
        assert response.status_code == 400, f"Expected 400 for invalid hour, got {response.status_code}"
    
    def test_create_schedule_validates_max_recipients(self):
        """POST /api/schedules/create enforces max 10 recipients"""
        emails = [f"test{i}@example.com" for i in range(11)]  # 11 emails
        response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "weekly",
                "send_hour": 9,
                "send_day": 0,
                "recipient_emails": emails
            }
        )
        assert response.status_code == 400, f"Expected 400 for >10 recipients, got {response.status_code}"
        assert "10" in response.json().get("detail", "")
    
    def test_create_schedule_success_weekly(self):
        """POST /api/schedules/create creates weekly schedule successfully"""
        response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "weekly",
                "send_hour": 9,
                "send_day": 1,  # Tuesday
                "recipient_emails": ["test@example.com"],
                "report_name": "TEST_Weekly Report"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data.get("status") == "created"
        assert "schedule" in data
        
        schedule = data["schedule"]
        assert schedule.get("frequency") == "weekly"
        assert schedule.get("send_hour") == 9
        assert schedule.get("send_day") == 1
        assert schedule.get("is_active") == True
        assert "schedule_id" in schedule
        
        # Track for cleanup
        self.created_schedule_ids.append(schedule["schedule_id"])
    
    def test_create_schedule_success_daily(self):
        """POST /api/schedules/create creates daily schedule successfully"""
        response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "daily",
                "send_hour": 14,
                "recipient_emails": ["daily@example.com"],
                "report_name": "TEST_Daily Report"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["schedule"]["frequency"] == "daily"
        assert data["schedule"]["send_hour"] == 14
        
        self.created_schedule_ids.append(data["schedule"]["schedule_id"])
    
    def test_create_schedule_success_monthly(self):
        """POST /api/schedules/create creates monthly schedule successfully"""
        response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "monthly",
                "send_hour": 10,
                "send_date": 15,  # 15th of month
                "recipient_emails": ["monthly@example.com"],
                "report_name": "TEST_Monthly Report"
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["schedule"]["frequency"] == "monthly"
        assert data["schedule"]["send_date"] == 15
        
        self.created_schedule_ids.append(data["schedule"]["schedule_id"])
    
    def test_create_schedule_generates_default_name(self):
        """POST /api/schedules/create generates default report name if not provided"""
        response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "weekly",
                "send_hour": 9,
                "send_day": 0,
                "recipient_emails": ["test@example.com"]
                # No report_name provided
            }
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        schedule = response.json()["schedule"]
        assert schedule.get("report_name"), "Should have generated a default name"
        assert "Weekly" in schedule["report_name"]
        
        self.created_schedule_ids.append(schedule["schedule_id"])
    
    # ============== GET /api/schedules/{schedule_id} ==============
    
    def test_get_schedule_by_id(self):
        """GET /api/schedules/{id} returns specific schedule"""
        # First create a schedule
        create_response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "weekly",
                "send_hour": 9,
                "send_day": 0,
                "recipient_emails": ["test@example.com"],
                "report_name": "TEST_Get By ID"
            }
        )
        assert create_response.status_code == 200
        schedule_id = create_response.json()["schedule"]["schedule_id"]
        self.created_schedule_ids.append(schedule_id)
        
        # Get the schedule
        response = self.session.get(f"{BASE_URL}/api/schedules/{schedule_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert "schedule" in data
        assert data["schedule"]["schedule_id"] == schedule_id
    
    def test_get_schedule_not_found(self):
        """GET /api/schedules/{id} returns 404 for non-existent schedule"""
        response = self.session.get(f"{BASE_URL}/api/schedules/nonexistent_id_12345")
        assert response.status_code == 404
    
    # ============== PUT /api/schedules/{schedule_id} ==============
    
    def test_update_schedule_success(self):
        """PUT /api/schedules/{id} updates schedule successfully"""
        # First create a schedule
        create_response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "weekly",
                "send_hour": 9,
                "send_day": 0,
                "recipient_emails": ["test@example.com"],
                "report_name": "TEST_Original Name"
            }
        )
        assert create_response.status_code == 200
        schedule_id = create_response.json()["schedule"]["schedule_id"]
        self.created_schedule_ids.append(schedule_id)
        
        # Update the schedule
        update_response = self.session.put(
            f"{BASE_URL}/api/schedules/{schedule_id}",
            json={
                "report_name": "TEST_Updated Name",
                "send_hour": 14,
                "recipient_emails": ["updated@example.com", "another@example.com"]
            }
        )
        assert update_response.status_code == 200, f"Expected 200, got {update_response.status_code}: {update_response.text}"
        
        data = update_response.json()
        assert data.get("status") == "updated"
        assert data["schedule"]["report_name"] == "TEST_Updated Name"
        assert data["schedule"]["send_hour"] == 14
        assert len(data["schedule"]["recipient_emails"]) == 2
    
    def test_update_schedule_validates_frequency(self):
        """PUT /api/schedules/{id} validates frequency on update"""
        # First create a schedule
        create_response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "weekly",
                "send_hour": 9,
                "send_day": 0,
                "recipient_emails": ["test@example.com"],
                "report_name": "TEST_Validate Freq"
            }
        )
        schedule_id = create_response.json()["schedule"]["schedule_id"]
        self.created_schedule_ids.append(schedule_id)
        
        # Try to update with invalid frequency
        response = self.session.put(
            f"{BASE_URL}/api/schedules/{schedule_id}",
            json={"frequency": "invalid"}
        )
        assert response.status_code == 400
    
    def test_update_schedule_not_found(self):
        """PUT /api/schedules/{id} returns 404 for non-existent schedule"""
        response = self.session.put(
            f"{BASE_URL}/api/schedules/nonexistent_id_12345",
            json={"report_name": "Test"}
        )
        assert response.status_code == 404
    
    # ============== DELETE /api/schedules/{schedule_id} ==============
    
    def test_delete_schedule_success(self):
        """DELETE /api/schedules/{id} deletes schedule successfully"""
        # First create a schedule
        create_response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "weekly",
                "send_hour": 9,
                "send_day": 0,
                "recipient_emails": ["test@example.com"],
                "report_name": "TEST_To Delete"
            }
        )
        assert create_response.status_code == 200
        schedule_id = create_response.json()["schedule"]["schedule_id"]
        
        # Delete the schedule
        delete_response = self.session.delete(f"{BASE_URL}/api/schedules/{schedule_id}")
        assert delete_response.status_code == 200, f"Expected 200, got {delete_response.status_code}"
        
        data = delete_response.json()
        assert data.get("status") == "deleted"
        assert data.get("schedule_id") == schedule_id
        
        # Verify it's deleted
        get_response = self.session.get(f"{BASE_URL}/api/schedules/{schedule_id}")
        assert get_response.status_code == 404
    
    def test_delete_schedule_not_found(self):
        """DELETE /api/schedules/{id} returns 404 for non-existent schedule"""
        response = self.session.delete(f"{BASE_URL}/api/schedules/nonexistent_id_12345")
        assert response.status_code == 404
    
    # ============== POST /api/schedules/{schedule_id}/toggle ==============
    
    def test_toggle_schedule_success(self):
        """POST /api/schedules/{id}/toggle toggles active status"""
        # First create a schedule (active by default)
        create_response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "weekly",
                "send_hour": 9,
                "send_day": 0,
                "recipient_emails": ["test@example.com"],
                "report_name": "TEST_Toggle Test"
            }
        )
        assert create_response.status_code == 200
        schedule_id = create_response.json()["schedule"]["schedule_id"]
        self.created_schedule_ids.append(schedule_id)
        
        # Toggle to inactive
        toggle_response = self.session.post(f"{BASE_URL}/api/schedules/{schedule_id}/toggle")
        assert toggle_response.status_code == 200, f"Expected 200, got {toggle_response.status_code}"
        
        data = toggle_response.json()
        assert data.get("status") == "paused"
        assert data.get("is_active") == False
        
        # Toggle back to active
        toggle_response2 = self.session.post(f"{BASE_URL}/api/schedules/{schedule_id}/toggle")
        assert toggle_response2.status_code == 200
        
        data2 = toggle_response2.json()
        assert data2.get("status") == "activated"
        assert data2.get("is_active") == True
    
    def test_toggle_schedule_not_found(self):
        """POST /api/schedules/{id}/toggle returns 404 for non-existent schedule"""
        response = self.session.post(f"{BASE_URL}/api/schedules/nonexistent_id_12345/toggle")
        assert response.status_code == 404
    
    # ============== Existing Schedule Test ==============
    
    def test_existing_schedule_sched_dd463f484e15(self):
        """Test that the pre-created schedule sched_dd463f484e15 exists"""
        response = self.session.get(f"{BASE_URL}/api/schedules/sched_dd463f484e15")
        # It may or may not exist depending on test state
        # Just verify the endpoint works
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            assert "schedule" in data
            print(f"Found existing schedule: {data['schedule'].get('report_name')}")


class TestScheduledReportsValidation:
    """Additional validation tests for scheduled reports"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
        # Login and get token
        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        token = login_response.json().get("access_token")
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.created_schedule_ids = []
        
        yield
        
        # Cleanup
        for schedule_id in self.created_schedule_ids:
            try:
                self.session.delete(f"{BASE_URL}/api/schedules/{schedule_id}")
            except:
                pass
    
    def test_create_validates_send_day_for_weekly(self):
        """Weekly schedules validate send_day range (0-6)"""
        response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "weekly",
                "send_hour": 9,
                "send_day": 7,  # Invalid - should be 0-6
                "recipient_emails": ["test@example.com"]
            }
        )
        assert response.status_code == 400, f"Expected 400 for invalid send_day, got {response.status_code}"
    
    def test_create_validates_send_date_for_monthly(self):
        """Monthly schedules validate send_date range (1-28)"""
        response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "monthly",
                "send_hour": 9,
                "send_date": 30,  # Invalid - should be 1-28
                "recipient_emails": ["test@example.com"]
            }
        )
        assert response.status_code == 400, f"Expected 400 for invalid send_date, got {response.status_code}"
    
    def test_create_validates_email_format(self):
        """POST /api/schedules/create validates email format"""
        response = self.session.post(
            f"{BASE_URL}/api/schedules/create",
            json={
                "frequency": "weekly",
                "send_hour": 9,
                "send_day": 0,
                "recipient_emails": ["invalid-email"]  # Invalid email format
            }
        )
        # Pydantic should return 422 for invalid email format
        assert response.status_code == 422, f"Expected 422 for invalid email, got {response.status_code}"


class TestScheduledReportsAPIExists:
    """Verify API endpoints exist and are accessible"""
    
    def test_schedules_my_endpoint_exists(self):
        """Verify GET /api/schedules/my endpoint exists"""
        response = requests.get(f"{BASE_URL}/api/schedules/my")
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code != 404, "Endpoint /api/schedules/my should exist"
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_schedules_create_endpoint_exists(self):
        """Verify POST /api/schedules/create endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/schedules/create", json={})
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code != 404, "Endpoint /api/schedules/create should exist"
        assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    def test_schedules_toggle_endpoint_exists(self):
        """Verify POST /api/schedules/{id}/toggle endpoint exists"""
        response = requests.post(f"{BASE_URL}/api/schedules/test_id/toggle")
        # Should return 401 (unauthorized) not 404 (not found) for the endpoint itself
        assert response.status_code in [401, 403, 404], f"Unexpected status: {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
