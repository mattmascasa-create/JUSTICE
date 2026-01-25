"""
Test Court-Grade AI and Premium Analytics APIs
Tests for P1/P2 features: RAG-enhanced AI, Premium Analytics, Quick Officer Lookup
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestCourtGradeAI:
    """Test Court-Grade AI endpoints - RAG-enhanced legal analysis"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures - login to get auth token"""
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
    
    # ============== KNOWLEDGE BASE TESTS ==============
    
    def test_list_amendments(self):
        """Test GET /api/court-grade/knowledge-base/amendments - list legal knowledge base"""
        response = requests.get(
            f"{BASE_URL}/api/court-grade/knowledge-base/amendments",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"List amendments failed: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert data.get("success") is True
        assert "amendments" in data
        assert "statutes" in data
        assert "violation_types" in data
        
        # Verify expected amendments are present
        amendments = data["amendments"]
        assert "1st" in amendments, "1st Amendment missing"
        assert "4th" in amendments, "4th Amendment missing"
        assert "5th" in amendments, "5th Amendment missing"
        assert "14th" in amendments, "14th Amendment missing"
        
        # Verify statutes
        statutes = data["statutes"]
        assert "42_usc_1983" in statutes, "Section 1983 missing"
        assert "18_usc_242" in statutes, "Section 242 missing"
        
        # Verify violation types
        violation_types = data["violation_types"]
        assert "excessive_force" in violation_types
        assert "unlawful_search" in violation_types
        assert "miranda_violation" in violation_types
        print(f"✓ Found {len(amendments)} amendments, {len(statutes)} statutes, {len(violation_types)} violation types")
    
    def test_get_violation_definition_excessive_force(self):
        """Test GET /api/court-grade/knowledge-base/violation/excessive_force"""
        response = requests.get(
            f"{BASE_URL}/api/court-grade/knowledge-base/violation/excessive_force",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get violation definition failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert data.get("violation_type") == "excessive_force"
        
        definition = data.get("definition")
        assert definition is not None
        assert "definition" in definition
        assert "standard" in definition
        assert "factors" in definition
        assert "indicators" in definition
        
        # Verify Graham v. Connor standard is referenced
        assert "Graham v. Connor" in definition.get("standard", "")
        print(f"✓ Excessive force definition includes {len(definition.get('factors', []))} factors")
    
    def test_get_violation_definition_unlawful_search(self):
        """Test GET /api/court-grade/knowledge-base/violation/unlawful_search"""
        response = requests.get(
            f"{BASE_URL}/api/court-grade/knowledge-base/violation/unlawful_search",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data.get("success") is True
        definition = data.get("definition")
        assert "exceptions" in definition, "Search exceptions not listed"
        print(f"✓ Unlawful search definition includes {len(definition.get('exceptions', []))} exceptions")
    
    def test_get_violation_definition_not_found(self):
        """Test GET /api/court-grade/knowledge-base/violation/invalid_type returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/court-grade/knowledge-base/violation/invalid_type_xyz",
            headers=self.headers
        )
        
        assert response.status_code == 404, "Should return 404 for unknown violation type"
        print("✓ Unknown violation type correctly returns 404")
    
    def test_explain_confidence_levels(self):
        """Test GET /api/court-grade/confidence/explain - no auth required"""
        # This endpoint doesn't require auth based on the code
        response = requests.get(f"{BASE_URL}/api/court-grade/confidence/explain")
        
        assert response.status_code == 200, f"Explain confidence failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "confidence_levels" in data
        assert "breakdown_factors" in data
        
        levels = data["confidence_levels"]
        assert "very_high" in levels
        assert "high" in levels
        assert "moderate" in levels
        assert "low" in levels
        assert "very_low" in levels
        
        # Verify structure of confidence level
        very_high = levels["very_high"]
        assert "range" in very_high
        assert "meaning" in very_high
        assert "court_ready" in very_high
        assert very_high["court_ready"] is True
        
        print(f"✓ Confidence levels explained with {len(data['breakdown_factors'])} breakdown factors")


class TestPremiumAnalytics:
    """Test Premium Analytics endpoints - Predictive risk, trends, audit reports"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test fixtures"""
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
    
    def test_get_violation_hotspots(self):
        """Test GET /api/premium-analytics/hotspots - identify high-violation departments"""
        response = requests.get(
            f"{BASE_URL}/api/premium-analytics/hotspots",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get hotspots failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "hotspots" in data
        assert "total_analyzed" in data
        
        hotspots = data["hotspots"]
        assert len(hotspots) > 0, "Should have at least one hotspot"
        
        # Verify hotspot structure
        first_hotspot = hotspots[0]
        assert "department_id" in first_hotspot
        assert "name" in first_hotspot
        assert "violation_count" in first_hotspot
        assert "officer_count" in first_hotspot
        assert "violations_per_officer" in first_hotspot
        
        print(f"✓ Found {len(hotspots)} hotspots, top: {first_hotspot['name']} ({first_hotspot['violations_per_officer']} violations/officer)")
    
    def test_get_risk_prediction(self):
        """Test GET /api/premium-analytics/risk-prediction/{dept_id} - Philadelphia PD"""
        dept_id = "dept_9ff94c5f6253"  # Philadelphia PD
        response = requests.get(
            f"{BASE_URL}/api/premium-analytics/risk-prediction/{dept_id}",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get risk prediction failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "prediction" in data
        
        prediction = data["prediction"]
        assert prediction.get("department_id") == dept_id
        assert "department_name" in prediction
        assert "risk_score" in prediction
        assert "risk_level" in prediction
        assert "prediction" in prediction
        assert "factors" in prediction
        
        # Verify risk factors
        factors = prediction["factors"]
        assert "recent_violation_rate" in factors
        assert "quarterly_trend" in factors
        assert "average_severity" in factors
        
        print(f"✓ Risk prediction for {prediction['department_name']}: {prediction['risk_level']} ({prediction['risk_score']})")
    
    def test_get_risk_prediction_not_found(self):
        """Test GET /api/premium-analytics/risk-prediction/invalid_dept returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/premium-analytics/risk-prediction/invalid_dept_xyz",
            headers=self.headers
        )
        
        assert response.status_code == 404, "Should return 404 for unknown department"
        print("✓ Unknown department correctly returns 404")
    
    def test_get_violation_trends(self):
        """Test GET /api/premium-analytics/trends - violation trend analysis"""
        response = requests.get(
            f"{BASE_URL}/api/premium-analytics/trends",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get trends failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert "trends" in data
        
        trends = data["trends"]
        assert "period_months" in trends
        assert "monthly_breakdown" in trends
        assert "type_breakdown" in trends
        assert "severity_distribution" in trends
        assert "trend_analysis" in trends
        
        # Verify trend analysis
        analysis = trends["trend_analysis"]
        assert "direction" in analysis
        assert "change_percentage" in analysis
        
        print(f"✓ Trends: {trends['total_violations']} violations, direction: {analysis['direction']}")
    
    def test_get_state_overview(self):
        """Test GET /api/premium-analytics/state-overview/CA - California overview"""
        response = requests.get(
            f"{BASE_URL}/api/premium-analytics/state-overview/CA",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Get state overview failed: {response.text}"
        data = response.json()
        
        assert data.get("success") is True
        assert data.get("state") == "CA"
        assert "overview" in data
        
        overview = data["overview"]
        assert "department_count" in overview
        assert "officer_count" in overview
        assert "violation_count" in overview
        assert "average_accountability_score" in overview
        assert "total_settlements" in overview
        
        # Verify best/worst departments
        assert "best_department" in data
        assert "worst_department" in data
        
        print(f"✓ CA overview: {overview['department_count']} depts, {overview['violation_count']} violations")
    
    def test_get_state_overview_not_found(self):
        """Test GET /api/premium-analytics/state-overview/XX returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/premium-analytics/state-overview/XX",
            headers=self.headers
        )
        
        assert response.status_code == 404, "Should return 404 for state with no departments"
        print("✓ Unknown state correctly returns 404")


class TestQuickOfficerLookup:
    """Test Quick Officer Lookup - instant badge number search"""
    
    def test_quick_lookup_found(self):
        """Test GET /api/accountability/public/officers/quick-lookup?badge=3803 - finds officer"""
        response = requests.get(
            f"{BASE_URL}/api/accountability/public/officers/quick-lookup?badge=3803"
        )
        
        assert response.status_code == 200, f"Quick lookup failed: {response.text}"
        data = response.json()
        
        assert data.get("found") is True
        assert data.get("count") == 1
        assert "officers" in data
        
        officers = data["officers"]
        assert len(officers) == 1
        
        officer = officers[0]
        assert officer.get("badge_number") == "3803"
        assert officer.get("full_name") == "James Garcia"
        assert "department_name" in officer
        assert "accountability_score" in officer
        assert "total_violations" in officer
        assert "recent_violations" in officer
        assert "warning_level" in officer
        
        # Verify warning level structure
        warning = officer["warning_level"]
        assert "level" in warning
        assert "color" in warning
        assert "message" in warning
        
        print(f"✓ Found officer {officer['full_name']} (badge {officer['badge_number']}) - {warning['level']} warning")
    
    def test_quick_lookup_not_found(self):
        """Test GET /api/accountability/public/officers/quick-lookup?badge=99999 - not found"""
        response = requests.get(
            f"{BASE_URL}/api/accountability/public/officers/quick-lookup?badge=99999"
        )
        
        assert response.status_code == 200, f"Quick lookup failed: {response.text}"
        data = response.json()
        
        assert data.get("found") is False
        assert "message" in data
        assert data.get("officers") == []
        
        print("✓ Non-existent badge correctly returns found=false")
    
    def test_quick_lookup_no_badge_param(self):
        """Test GET /api/accountability/public/officers/quick-lookup without badge param"""
        response = requests.get(
            f"{BASE_URL}/api/accountability/public/officers/quick-lookup"
        )
        
        # Should return 422 (validation error) or handle gracefully
        assert response.status_code in [200, 422], f"Unexpected status: {response.status_code}"
        print(f"✓ Missing badge param handled with status {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
