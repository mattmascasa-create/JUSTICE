"""
Admin Dashboard and Support Ticket System Tests

Tests for:
- Admin Dashboard API (GET /api/admin/dashboard)
- User Management (GET /api/admin/users, PUT /api/admin/users/{id})
- Support Ticket System (POST /api/admin/tickets, GET /api/admin/tickets)
- AI-assisted ticket resolution
"""

import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "test@example.com"
ADMIN_PASSWORD = "password123"


class TestAdminAuth:
    """Test admin authentication and access control"""
    
    @pytest.fixture(scope="class")
    def auth_token(self):
        """Get authentication token for admin user"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        data = response.json()
        assert "token" in data, "No token in response"
        return data["token"]
    
    @pytest.fixture(scope="class")
    def auth_headers(self, auth_token):
        """Get headers with auth token"""
        return {"Authorization": f"Bearer {auth_token}"}
    
    def test_login_as_admin(self, auth_token):
        """Test that admin user can login"""
        assert auth_token is not None
        print(f"✓ Admin login successful, token received")
    
    def test_verify_admin_role(self, auth_headers):
        """Verify the test user has admin role"""
        response = requests.get(f"{BASE_URL}/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("role") == "admin", f"User role is {data.get('role')}, expected 'admin'"
        print(f"✓ User {data.get('email')} has admin role")


class TestAdminDashboard:
    """Test admin dashboard endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authentication headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_dashboard_stats(self, auth_headers):
        """Test GET /api/admin/dashboard returns stats"""
        response = requests.get(f"{BASE_URL}/api/admin/dashboard", headers=auth_headers)
        assert response.status_code == 200, f"Dashboard failed: {response.text}"
        
        data = response.json()
        
        # Verify users stats
        assert "users" in data, "Missing 'users' in dashboard"
        assert "total" in data["users"], "Missing 'total' in users"
        assert "active_today" in data["users"], "Missing 'active_today' in users"
        assert "by_role" in data["users"], "Missing 'by_role' in users"
        
        # Verify tickets stats
        assert "tickets" in data, "Missing 'tickets' in dashboard"
        assert "open" in data["tickets"], "Missing 'open' in tickets"
        assert "urgent" in data["tickets"], "Missing 'urgent' in tickets"
        
        # Verify platform stats
        assert "platform" in data, "Missing 'platform' in dashboard"
        assert "total_encounters" in data["platform"], "Missing 'total_encounters'"
        
        print(f"✓ Dashboard stats: {data['users']['total']} users, {data['tickets']['open']} open tickets")
    
    def test_dashboard_requires_admin(self):
        """Test that dashboard requires admin role"""
        # Try without auth
        response = requests.get(f"{BASE_URL}/api/admin/dashboard")
        assert response.status_code in [401, 403], "Dashboard should require auth"
        print("✓ Dashboard correctly requires authentication")


class TestUserManagement:
    """Test user management endpoints"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authentication headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_list_users(self, auth_headers):
        """Test GET /api/admin/users lists users"""
        response = requests.get(f"{BASE_URL}/api/admin/users", headers=auth_headers)
        assert response.status_code == 200, f"List users failed: {response.text}"
        
        data = response.json()
        assert "users" in data, "Missing 'users' in response"
        assert "total" in data, "Missing 'total' in response"
        assert isinstance(data["users"], list), "Users should be a list"
        
        if len(data["users"]) > 0:
            user = data["users"][0]
            assert "user_id" in user, "User missing user_id"
            assert "email" in user, "User missing email"
            assert "role" in user, "User missing role"
        
        print(f"✓ Listed {len(data['users'])} users (total: {data['total']})")
    
    def test_list_users_with_role_filter(self, auth_headers):
        """Test filtering users by role"""
        response = requests.get(f"{BASE_URL}/api/admin/users?role=admin", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        for user in data["users"]:
            assert user["role"] == "admin", f"User {user['email']} has role {user['role']}, expected admin"
        
        print(f"✓ Role filter works: {len(data['users'])} admin users")
    
    def test_list_users_with_search(self, auth_headers):
        """Test searching users by name/email"""
        response = requests.get(f"{BASE_URL}/api/admin/users?search=test", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        print(f"✓ Search filter works: {len(data['users'])} users matching 'test'")
    
    def test_list_users_requires_admin(self):
        """Test that listing users requires admin role"""
        response = requests.get(f"{BASE_URL}/api/admin/users")
        assert response.status_code in [401, 403], "List users should require auth"
        print("✓ List users correctly requires admin authentication")


class TestSupportTickets:
    """Test support ticket system"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authentication headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture(scope="class")
    def test_ticket_id(self, auth_headers):
        """Create a test ticket and return its ID"""
        ticket_data = {
            "subject": f"TEST_Ticket_{uuid.uuid4().hex[:8]}",
            "description": "This is a test ticket created by automated testing",
            "category": "technical",
            "priority": "medium"
        }
        response = requests.post(f"{BASE_URL}/api/admin/tickets", json=ticket_data, headers=auth_headers)
        assert response.status_code == 200, f"Create ticket failed: {response.text}"
        data = response.json()
        assert "ticket_id" in data, "Missing ticket_id in response"
        return data["ticket_id"]
    
    def test_create_ticket(self, auth_headers):
        """Test POST /api/admin/tickets creates a ticket"""
        ticket_data = {
            "subject": f"TEST_Create_Ticket_{uuid.uuid4().hex[:8]}",
            "description": "Testing ticket creation endpoint",
            "category": "general",
            "priority": "low"
        }
        response = requests.post(f"{BASE_URL}/api/admin/tickets", json=ticket_data, headers=auth_headers)
        assert response.status_code == 200, f"Create ticket failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        assert "ticket_id" in data, "Missing ticket_id"
        assert "message" in data, "Missing message"
        
        print(f"✓ Created ticket: {data['ticket_id']}")
    
    def test_create_ticket_requires_auth(self):
        """Test that creating tickets requires authentication"""
        ticket_data = {
            "subject": "Unauthorized ticket",
            "description": "This should fail",
            "category": "general",
            "priority": "low"
        }
        response = requests.post(f"{BASE_URL}/api/admin/tickets", json=ticket_data)
        assert response.status_code in [401, 403], "Create ticket should require auth"
        print("✓ Create ticket correctly requires authentication")
    
    def test_get_my_tickets(self, auth_headers):
        """Test GET /api/admin/tickets/my returns user's tickets"""
        response = requests.get(f"{BASE_URL}/api/admin/tickets/my", headers=auth_headers)
        assert response.status_code == 200, f"Get my tickets failed: {response.text}"
        
        data = response.json()
        assert "tickets" in data, "Missing 'tickets' in response"
        assert isinstance(data["tickets"], list), "Tickets should be a list"
        
        print(f"✓ User has {len(data['tickets'])} tickets")
    
    def test_get_ticket_by_id(self, auth_headers, test_ticket_id):
        """Test GET /api/admin/tickets/{id} returns ticket details"""
        response = requests.get(f"{BASE_URL}/api/admin/tickets/{test_ticket_id}", headers=auth_headers)
        assert response.status_code == 200, f"Get ticket failed: {response.text}"
        
        data = response.json()
        assert data.get("ticket_id") == test_ticket_id, "Ticket ID mismatch"
        assert "subject" in data, "Missing subject"
        assert "description" in data, "Missing description"
        assert "status" in data, "Missing status"
        assert "priority" in data, "Missing priority"
        
        print(f"✓ Retrieved ticket: {data['subject']}")
    
    def test_admin_list_all_tickets(self, auth_headers):
        """Test GET /api/admin/tickets lists all tickets (admin only)"""
        response = requests.get(f"{BASE_URL}/api/admin/tickets", headers=auth_headers)
        assert response.status_code == 200, f"List tickets failed: {response.text}"
        
        data = response.json()
        assert "tickets" in data, "Missing 'tickets' in response"
        assert "total" in data, "Missing 'total' in response"
        
        print(f"✓ Admin can see {len(data['tickets'])} tickets (total: {data['total']})")
    
    def test_admin_filter_tickets_by_status(self, auth_headers):
        """Test filtering tickets by status"""
        response = requests.get(f"{BASE_URL}/api/admin/tickets?status=open", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        for ticket in data["tickets"]:
            assert ticket["status"] == "open", f"Ticket has status {ticket['status']}, expected open"
        
        print(f"✓ Status filter works: {len(data['tickets'])} open tickets")
    
    def test_admin_filter_tickets_by_priority(self, auth_headers):
        """Test filtering tickets by priority"""
        response = requests.get(f"{BASE_URL}/api/admin/tickets?priority=urgent", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        for ticket in data["tickets"]:
            assert ticket["priority"] == "urgent", f"Ticket has priority {ticket['priority']}, expected urgent"
        
        print(f"✓ Priority filter works: {len(data['tickets'])} urgent tickets")
    
    def test_admin_update_ticket_status(self, auth_headers, test_ticket_id):
        """Test PUT /api/admin/tickets/{id} updates ticket"""
        update_data = {"status": "in_progress"}
        response = requests.put(
            f"{BASE_URL}/api/admin/tickets/{test_ticket_id}", 
            json=update_data, 
            headers=auth_headers
        )
        assert response.status_code == 200, f"Update ticket failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        
        # Verify the update
        verify_response = requests.get(f"{BASE_URL}/api/admin/tickets/{test_ticket_id}", headers=auth_headers)
        verify_data = verify_response.json()
        assert verify_data.get("status") == "in_progress", "Status not updated"
        
        print(f"✓ Updated ticket status to 'in_progress'")
    
    def test_admin_respond_to_ticket(self, auth_headers, test_ticket_id):
        """Test POST /api/admin/tickets/{id}/respond adds response"""
        response_data = {
            "subject": "Test Response",
            "description": "Original description",
            "response_text": "This is a test response from admin",
            "is_public": True
        }
        response = requests.post(
            f"{BASE_URL}/api/admin/tickets/{test_ticket_id}/respond",
            json=response_data,
            headers=auth_headers
        )
        assert response.status_code == 200, f"Respond to ticket failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        
        print(f"✓ Added response to ticket")
    
    def test_admin_get_ai_suggestion(self, auth_headers, test_ticket_id):
        """Test POST /api/admin/tickets/{id}/ai-suggest gets AI suggestion"""
        response = requests.post(
            f"{BASE_URL}/api/admin/tickets/{test_ticket_id}/ai-suggest",
            headers=auth_headers
        )
        assert response.status_code == 200, f"AI suggestion failed: {response.text}"
        
        data = response.json()
        assert data.get("success") == True, "Expected success=True"
        assert "suggestion" in data, "Missing suggestion"
        assert "source" in data, "Missing source (ai or template)"
        
        print(f"✓ Got AI suggestion (source: {data['source']})")


class TestAdminAnalytics:
    """Test admin analytics endpoint"""
    
    @pytest.fixture(scope="class")
    def auth_headers(self):
        """Get authentication headers"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        token = response.json()["token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_analytics(self, auth_headers):
        """Test GET /api/admin/analytics returns analytics data"""
        response = requests.get(f"{BASE_URL}/api/admin/analytics?days=30", headers=auth_headers)
        assert response.status_code == 200, f"Analytics failed: {response.text}"
        
        data = response.json()
        assert "period_days" in data, "Missing period_days"
        assert "users" in data, "Missing users"
        assert "activity" in data, "Missing activity"
        assert "support" in data, "Missing support"
        
        print(f"✓ Analytics for {data['period_days']} days: {data['users'].get('new_registrations', 0)} new users")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
