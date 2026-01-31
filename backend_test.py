#!/usr/bin/env python3
"""
JUSTICE Platform Backend API Testing
Tests all API endpoints for the police accountability platform
"""

import requests
import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

class JusticeAPITester:
    def __init__(self, base_url="https://civil-rights-shield.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.session = requests.Session()
        
    def log_test(self, name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            
        result = {
            "test_name": name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    {details}")
        if not success and response_data:
            print(f"    Response: {response_data}")
        print()

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, 
                 data: Optional[Dict] = None, headers: Optional[Dict] = None) -> tuple:
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        
        # Default headers
        req_headers = {'Content-Type': 'application/json'}
        if self.token:
            req_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            req_headers.update(headers)

        try:
            if method == 'GET':
                response = self.session.get(url, headers=req_headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=req_headers)
            elif method == 'PATCH':
                response = self.session.patch(url, json=data, headers=req_headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=req_headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            response_data = None
            
            try:
                response_data = response.json()
            except:
                response_data = response.text

            details = f"Status: {response.status_code} (expected {expected_status})"
            self.log_test(name, success, details, response_data if not success else None)
            
            return success, response_data

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}")
            return False, str(e)

    def test_health_check(self):
        """Test health endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)

    def test_user_registration(self):
        """Test user registration"""
        test_email = f"test_user_{datetime.now().strftime('%H%M%S')}@example.com"
        test_data = {
            "email": test_email,
            "password": "TestPass123!",
            "name": "Test User",
            "phone": "+1234567890"
        }
        
        success, response = self.run_test("User Registration", "POST", "auth/register", 200, test_data)
        
        if success and response:
            self.token = response.get('access_token')
            if response.get('user'):
                self.user_id = response['user'].get('user_id')
            return True, test_email, "TestPass123!"
        return False, None, None

    def test_user_login(self, email: str, password: str):
        """Test user login"""
        login_data = {"email": email, "password": password}
        success, response = self.run_test("User Login", "POST", "auth/login", 200, login_data)
        
        if success and response:
            self.token = response.get('access_token')
            if response.get('user'):
                self.user_id = response['user'].get('user_id')
        return success

    def test_get_user_profile(self):
        """Test get current user profile"""
        return self.run_test("Get User Profile", "GET", "auth/me", 200)

    def test_create_case(self):
        """Test case creation"""
        case_data = {
            "title": "Test Police Misconduct Case",
            "description": "Testing case creation functionality",
            "incident_date": datetime.now(timezone.utc).isoformat(),
            "location": "123 Test Street, Test City, TS 12345",
            "department": "Test Police Department",
            "officer_name": "Officer Test",
            "officer_badge": "12345",
            "violation_type": "Excessive Force",
            "severity": "high"
        }
        
        success, response = self.run_test("Create Case", "POST", "cases", 200, case_data)
        
        if success and response:
            return response.get('case_id')
        return None

    def test_get_cases(self):
        """Test get user cases"""
        return self.run_test("Get Cases", "GET", "cases", 200)

    def test_get_case_detail(self, case_id: str):
        """Test get specific case"""
        if not case_id:
            self.log_test("Get Case Detail", False, "No case_id provided")
            return False
        return self.run_test("Get Case Detail", "GET", f"cases/{case_id}", 200)

    def test_create_evidence(self, case_id: str):
        """Test evidence creation"""
        if not case_id:
            self.log_test("Create Evidence", False, "No case_id provided")
            return None
            
        evidence_data = {
            "case_id": case_id,
            "file_name": "test_evidence.jpg",
            "file_url": "https://example.com/evidence/test.jpg",
            "file_type": "image",
            "file_size": 1024000,
            "description": "Test evidence file"
        }
        
        success, response = self.run_test("Create Evidence", "POST", "evidence", 200, evidence_data)
        
        if success and response:
            return response.get('evidence_id')
        return None

    def test_get_evidence(self):
        """Test get all evidence"""
        return self.run_test("Get All Evidence", "GET", "evidence", 200)

    def test_get_attorneys(self):
        """Test get attorneys directory"""
        return self.run_test("Get Attorneys", "GET", "attorneys", 200)

    def test_create_sos_alert(self):
        """Test SOS alert creation"""
        sos_data = {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "address": "San Francisco, CA"
        }
        
        success, response = self.run_test("Create SOS Alert", "POST", "sos", 200, sos_data)
        
        if success and response:
            return response.get('alert_id')
        return None

    def test_get_active_sos(self):
        """Test get active SOS alert"""
        return self.run_test("Get Active SOS", "GET", "sos/active", 200)

    def test_ai_chat(self):
        """Test AI Attorney chat"""
        chat_data = {
            "message": "What are my rights during a traffic stop?",
            "session_id": None
        }
        
        success, response = self.run_test("AI Chat", "POST", "ai/chat", 200, chat_data)
        
        if success and response:
            return response.get('session_id')
        return None

    def test_get_rights_info(self):
        """Test Know Your Rights endpoint"""
        return self.run_test("Get Rights Info", "GET", "rights", 200)

    def test_dashboard_analytics(self):
        """Test dashboard analytics"""
        return self.run_test("Dashboard Analytics", "GET", "analytics/dashboard", 200)

    def test_public_analytics(self):
        """Test public analytics (no auth required)"""
        # Temporarily remove token for public endpoint
        temp_token = self.token
        self.token = None
        success, response = self.run_test("Public Analytics", "GET", "analytics/public", 200)
        self.token = temp_token
        return success, response

    def test_send_message(self):
        """Test messaging system"""
        message_data = {
            "recipient_id": "test_recipient",
            "content": "Test message",
            "case_id": None
        }
        
        success, response = self.run_test("Send Message", "POST", "messages", 200, message_data)
        
        if success and response:
            return response.get('message_id')
        return None

    def test_get_messages(self):
        """Test get messages"""
        return self.run_test("Get Messages", "GET", "messages/conversations", 200)

    def test_departments_api(self):
        """Test departments API for transparency portal"""
        # Test without auth (public endpoint)
        temp_token = self.token
        self.token = None
        success, response = self.run_test("Get Departments (Public)", "GET", "departments", 200)
        self.token = temp_token
        return success, response

    def test_departments_filtering(self):
        """Test departments filtering by state"""
        temp_token = self.token
        self.token = None
        success, response = self.run_test("Get Departments by State", "GET", "departments?state=California", 200)
        self.token = temp_token
        return success, response

    def test_file_upload_endpoint(self):
        """Test file upload endpoint (without actual file)"""
        # This will test the endpoint exists and returns proper error for missing file
        success, response = self.run_test("File Upload Endpoint", "POST", "upload", 422)
        return success

    def test_websocket_endpoint_exists(self):
        """Test WebSocket endpoint exists (will fail connection but endpoint should exist)"""
        # Test with invalid token to check if endpoint exists
        try:
            import websocket
            ws_url = self.base_url.replace('https://', 'wss://').replace('http://', 'ws://')
            ws = websocket.create_connection(f"{ws_url}/ws/invalid_token", timeout=2)
            ws.close()
            self.log_test("WebSocket Endpoint Exists", True, "WebSocket endpoint accessible")
            return True
        except websocket.WebSocketBadStatusException as e:
            if e.status_code == 4001:  # Expected error for invalid token
                self.log_test("WebSocket Endpoint Exists", True, "WebSocket endpoint exists (invalid token error expected)")
                return True
            else:
                self.log_test("WebSocket Endpoint Exists", False, f"Unexpected WebSocket error: {e}")
                return False
        except Exception as e:
            self.log_test("WebSocket Endpoint Exists", False, f"WebSocket connection failed: {e}")
            return False

    def run_comprehensive_test(self):
        """Run all tests in sequence"""
        print("🚀 Starting JUSTICE Platform API Tests")
        print("=" * 50)
        
        # Test 1: Health Check
        self.test_health_check()
        
        # Test 2: User Registration
        reg_success, email, password = self.test_user_registration()
        if not reg_success:
            print("❌ Registration failed - stopping tests")
            return self.generate_report()
        
        # Test 3: User Login (test with registered credentials)
        if not self.test_user_login(email, password):
            print("❌ Login failed - stopping tests")
            return self.generate_report()
        
        # Test 4: Get User Profile
        self.test_get_user_profile()
        
        # Test 5: Case Management
        case_id = self.test_create_case()
        self.test_get_cases()
        if case_id:
            self.test_get_case_detail(case_id)
        
        # Test 6: Evidence Management
        evidence_id = self.test_create_evidence(case_id)
        self.test_get_evidence()
        
        # Test 7: Attorney Directory
        self.test_get_attorneys()
        
        # Test 8: SOS System
        alert_id = self.test_create_sos_alert()
        self.test_get_active_sos()
        
        # Test 9: AI Attorney
        session_id = self.test_ai_chat()
        
        # Test 10: Know Your Rights
        self.test_get_rights_info()
        
        # Test 11: Analytics
        self.test_dashboard_analytics()
        self.test_public_analytics()
        
        # Test 12: Messaging
        message_id = self.test_send_message()
        self.test_get_messages()
        
        # Test 13: Phase 2 - Departments API (Transparency Portal)
        self.test_departments_api()
        self.test_departments_filtering()
        
        # Test 14: Phase 2 - File Upload
        self.test_file_upload_endpoint()
        
        # Test 15: Phase 2 - WebSocket Endpoint
        self.test_websocket_endpoint_exists()
        
        return self.generate_report()

    def generate_report(self):
        """Generate test report"""
        print("=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.tests_passed < self.tests_run:
            print("\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test_name']}: {result['details']}")
        
        # Save detailed results
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "success_rate": success_rate,
            "detailed_results": self.test_results
        }
        
        with open('/app/test_reports/backend_test_results.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        return success_rate >= 80  # Consider 80%+ success rate as passing

def main():
    """Main test execution"""
    tester = JusticeAPITester()
    
    try:
        success = tester.run_comprehensive_test()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Test execution failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())