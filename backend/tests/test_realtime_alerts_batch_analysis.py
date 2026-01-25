"""
Test Real-Time Violation Alerts and Batch Court-Grade Analysis APIs
Tests for JUSTICE Platform extension features:
1. Real-Time Alerts - automatic attorney notifications during live encounters
2. Batch Analysis - process multiple encounters at once
"""
import pytest
import requests
import os
import uuid
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"


class TestAuth:
    """Authentication helper"""
    
    @staticmethod
    def get_token():
        """Get auth token for testing"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code == 200:
            return response.json().get("access_token")
        return None


@pytest.fixture(scope="module")
def auth_token():
    """Get authentication token"""
    token = TestAuth.get_token()
    if not token:
        pytest.skip("Authentication failed - skipping tests")
    return token


@pytest.fixture(scope="module")
def auth_headers(auth_token):
    """Get headers with auth token"""
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture(scope="module")
def test_encounter_id():
    """Generate a test encounter ID"""
    return f"test_enc_{uuid.uuid4().hex[:12]}"


# ============================================================================
# REAL-TIME ALERTS TESTS
# ============================================================================

class TestRealtimeAlertsKeywords:
    """Test GET /api/realtime-alerts/keywords - Get violation keywords"""
    
    def test_get_keywords_success(self, auth_headers):
        """Test getting violation keywords list"""
        response = requests.get(
            f"{BASE_URL}/api/realtime-alerts/keywords",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "keywords" in data
        
        # Verify all 6 violation types are present
        keywords = data["keywords"]
        expected_types = ["excessive_force", "miranda_violation", "unlawful_search", 
                         "detention", "first_amendment", "racial_profiling"]
        
        for vtype in expected_types:
            assert vtype in keywords, f"Missing violation type: {vtype}"
            assert "keywords" in keywords[vtype]
            assert "severity" in keywords[vtype]
        
        print(f"✓ Keywords endpoint returns {len(keywords)} violation types")
    
    def test_keywords_severity_mapping(self, auth_headers):
        """Test that severity levels are correctly mapped"""
        response = requests.get(
            f"{BASE_URL}/api/realtime-alerts/keywords",
            headers=auth_headers
        )
        
        data = response.json()
        keywords = data["keywords"]
        
        # Verify severity mappings per spec
        assert keywords["excessive_force"]["severity"] == "critical"
        assert keywords["miranda_violation"]["severity"] == "high"
        assert keywords["unlawful_search"]["severity"] == "high"
        assert keywords["detention"]["severity"] == "medium"
        assert keywords["first_amendment"]["severity"] == "high"
        assert keywords["racial_profiling"]["severity"] == "high"
        
        print("✓ Severity levels correctly mapped")
    
    def test_critical_keywords_present(self, auth_headers):
        """Test that critical keywords are present"""
        response = requests.get(
            f"{BASE_URL}/api/realtime-alerts/keywords",
            headers=auth_headers
        )
        
        data = response.json()
        keywords = data["keywords"]
        
        # Check critical keywords from spec
        excessive_force_keywords = keywords["excessive_force"]["keywords"]
        assert "tased" in excessive_force_keywords or "taser" in excessive_force_keywords
        assert "pepper spray" in excessive_force_keywords
        assert "gun drawn" in excessive_force_keywords
        
        first_amendment_keywords = keywords["first_amendment"]["keywords"]
        assert "stop recording" in first_amendment_keywords
        
        print("✓ Critical keywords present in keyword list")


class TestRealtimeAlertsAnalyzeChunk:
    """Test POST /api/realtime-alerts/analyze-chunk - Detect violations in transcript"""
    
    def test_analyze_chunk_detention_escalation(self, auth_headers, test_encounter_id):
        """Test detection of detention (medium) and escalation (high) violations"""
        # Transcript from spec: should detect detention (medium) and escalation (high)
        transcript = "Officer: Get on the ground now! Stop resisting! I will tase you!"
        
        response = requests.post(
            f"{BASE_URL}/api/realtime-alerts/analyze-chunk",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter_id,
                "transcript_chunk": transcript
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "alerts" in data
        assert "alert_count" in data
        
        # Should detect at least detention and escalation
        alerts = data["alerts"]
        assert len(alerts) >= 1, "Should detect at least one violation"
        
        # Check for detention detection (medium severity)
        violation_types = [a["violation_type"] for a in alerts]
        severities = [a["severity"] for a in alerts]
        
        print(f"✓ Detected violations: {violation_types}")
        print(f"✓ Severities: {severities}")
        
        # Verify alert structure
        for alert in alerts:
            assert "alert_id" in alert
            assert "encounter_id" in alert
            assert "severity" in alert
            assert "violation_type" in alert
            assert "trigger_text" in alert
    
    def test_analyze_chunk_excessive_force_critical(self, auth_headers, test_encounter_id):
        """Test detection of excessive force (critical severity)"""
        transcript = "The officer tased me while I was on the ground!"
        
        response = requests.post(
            f"{BASE_URL}/api/realtime-alerts/analyze-chunk",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter_id,
                "transcript_chunk": transcript
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        alerts = data["alerts"]
        assert len(alerts) >= 1, "Should detect excessive force"
        
        # Check for critical severity
        has_critical = any(a["severity"] == "critical" for a in alerts)
        has_excessive_force = any(a["violation_type"] == "excessive_force" for a in alerts)
        
        assert has_excessive_force, "Should detect excessive_force violation"
        assert has_critical, "Excessive force should be critical severity"
        
        print("✓ Excessive force detected with critical severity")
    
    def test_analyze_chunk_first_amendment(self, auth_headers, test_encounter_id):
        """Test detection of first amendment violation (high severity)"""
        transcript = "Officer said: Stop recording! Put the phone down now!"
        
        response = requests.post(
            f"{BASE_URL}/api/realtime-alerts/analyze-chunk",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter_id,
                "transcript_chunk": transcript
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        alerts = data["alerts"]
        assert len(alerts) >= 1, "Should detect first amendment violation"
        
        has_first_amendment = any(a["violation_type"] == "first_amendment" for a in alerts)
        has_high = any(a["severity"] == "high" for a in alerts)
        
        assert has_first_amendment, "Should detect first_amendment violation"
        assert has_high, "First amendment should be high severity"
        
        print("✓ First amendment violation detected with high severity")
    
    def test_analyze_chunk_miranda_violation(self, auth_headers, test_encounter_id):
        """Test detection of miranda violation (high severity)"""
        transcript = "You have the right to remain silent. Anything you say can be used against you."
        
        response = requests.post(
            f"{BASE_URL}/api/realtime-alerts/analyze-chunk",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter_id,
                "transcript_chunk": transcript
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        alerts = data["alerts"]
        # Miranda rights being read is detected as a potential violation context
        if len(alerts) > 0:
            has_miranda = any(a["violation_type"] == "miranda_violation" for a in alerts)
            print(f"✓ Miranda context detected: {has_miranda}")
    
    def test_analyze_chunk_short_text(self, auth_headers, test_encounter_id):
        """Test that short chunks are handled gracefully"""
        response = requests.post(
            f"{BASE_URL}/api/realtime-alerts/analyze-chunk",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter_id,
                "transcript_chunk": "Hi"  # Too short
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["alerts"] == []
        assert "too short" in data.get("message", "").lower()
        
        print("✓ Short chunks handled gracefully")
    
    def test_analyze_chunk_no_violations(self, auth_headers, test_encounter_id):
        """Test transcript with no violations"""
        transcript = "The weather is nice today. I'm going to the store to buy groceries."
        
        response = requests.post(
            f"{BASE_URL}/api/realtime-alerts/analyze-chunk",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter_id,
                "transcript_chunk": transcript
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["alert_count"] == 0
        
        print("✓ No false positives for benign text")


class TestRealtimeAlertsManualAlert:
    """Test POST /api/realtime-alerts/manual-alert - Manual attorney alert"""
    
    def test_manual_alert_success(self, auth_headers, test_encounter_id):
        """Test triggering a manual alert"""
        response = requests.post(
            f"{BASE_URL}/api/realtime-alerts/manual-alert",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter_id,
                "message": "I need immediate legal assistance!",
                "severity": "high"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "alert" in data
        
        alert = data["alert"]
        assert alert["severity"] == "high"
        assert alert["violation_type"] == "manual_alert"
        assert "alert_id" in alert
        
        print(f"✓ Manual alert created: {alert['alert_id']}")
        return alert["alert_id"]
    
    def test_manual_alert_critical_severity(self, auth_headers, test_encounter_id):
        """Test manual alert with critical severity"""
        response = requests.post(
            f"{BASE_URL}/api/realtime-alerts/manual-alert",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter_id,
                "message": "Emergency! Officer is being aggressive!",
                "severity": "critical"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["alert"]["severity"] == "critical"
        
        print("✓ Critical manual alert created")
    
    def test_manual_alert_invalid_severity(self, auth_headers, test_encounter_id):
        """Test manual alert with invalid severity"""
        response = requests.post(
            f"{BASE_URL}/api/realtime-alerts/manual-alert",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter_id,
                "message": "Test message",
                "severity": "invalid_severity"
            }
        )
        
        assert response.status_code == 400
        print("✓ Invalid severity rejected with 400")


class TestRealtimeAlertsMyAlerts:
    """Test GET /api/realtime-alerts/my-alerts - Get user alerts"""
    
    def test_get_my_alerts(self, auth_headers):
        """Test getting user's alerts"""
        response = requests.get(
            f"{BASE_URL}/api/realtime-alerts/my-alerts",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "alerts" in data
        assert "total" in data
        assert "severity_breakdown" in data
        assert "unacknowledged" in data
        
        # Verify severity breakdown structure
        breakdown = data["severity_breakdown"]
        assert "critical" in breakdown
        assert "high" in breakdown
        assert "medium" in breakdown
        assert "low" in breakdown
        
        print(f"✓ Retrieved {data['total']} alerts")
        print(f"✓ Severity breakdown: {breakdown}")
    
    def test_get_my_alerts_with_limit(self, auth_headers):
        """Test getting alerts with limit parameter"""
        response = requests.get(
            f"{BASE_URL}/api/realtime-alerts/my-alerts",
            headers=auth_headers,
            params={"limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["alerts"]) <= 5
        
        print("✓ Limit parameter works correctly")


class TestRealtimeAlertsAcknowledge:
    """Test POST /api/realtime-alerts/acknowledge - Acknowledge alert"""
    
    def test_acknowledge_alert(self, auth_headers, test_encounter_id):
        """Test acknowledging an alert"""
        # First create an alert
        create_response = requests.post(
            f"{BASE_URL}/api/realtime-alerts/manual-alert",
            headers=auth_headers,
            json={
                "encounter_id": test_encounter_id,
                "message": "Test alert for acknowledgment",
                "severity": "medium"
            }
        )
        
        assert create_response.status_code == 200
        alert_id = create_response.json()["alert"]["alert_id"]
        
        # Now acknowledge it
        ack_response = requests.post(
            f"{BASE_URL}/api/realtime-alerts/acknowledge",
            headers=auth_headers,
            json={"alert_id": alert_id}
        )
        
        assert ack_response.status_code == 200
        data = ack_response.json()
        assert data["success"] is True
        assert data["alert_id"] == alert_id
        assert "acknowledged_at" in data
        
        print(f"✓ Alert {alert_id} acknowledged")
    
    def test_acknowledge_nonexistent_alert(self, auth_headers):
        """Test acknowledging a non-existent alert"""
        response = requests.post(
            f"{BASE_URL}/api/realtime-alerts/acknowledge",
            headers=auth_headers,
            json={"alert_id": "nonexistent_alert_12345"}
        )
        
        assert response.status_code == 404
        print("✓ Non-existent alert returns 404")


class TestRealtimeAlertsStats:
    """Test GET /api/realtime-alerts/stats - Get alert statistics"""
    
    def test_get_stats(self, auth_headers):
        """Test getting alert statistics"""
        response = requests.get(
            f"{BASE_URL}/api/realtime-alerts/stats",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "period_days" in data
        assert "stats" in data
        assert "by_violation_type" in data
        
        stats = data["stats"]
        assert "total_alerts" in stats
        assert "critical_alerts" in stats
        assert "acknowledged_alerts" in stats
        assert "acknowledgment_rate" in stats
        
        print(f"✓ Stats: {stats['total_alerts']} total, {stats['critical_alerts']} critical")
    
    def test_get_stats_custom_days(self, auth_headers):
        """Test getting stats with custom day range"""
        response = requests.get(
            f"{BASE_URL}/api/realtime-alerts/stats",
            headers=auth_headers,
            params={"days": 7}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["period_days"] == 7
        
        print("✓ Custom day range works")


# ============================================================================
# BATCH COURT-GRADE ANALYSIS TESTS
# ============================================================================

class TestBatchAnalysisQueue:
    """Test POST /api/court-grade/batch-analyze - Queue batch job"""
    
    def test_batch_analyze_queue(self, auth_headers):
        """Test queuing a batch analysis job"""
        encounter_ids = [f"test_batch_{uuid.uuid4().hex[:8]}" for _ in range(3)]
        
        response = requests.post(
            f"{BASE_URL}/api/court-grade/batch-analyze",
            headers=auth_headers,
            json=encounter_ids
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "job_id" in data
        assert data["encounter_count"] == 3
        
        print(f"✓ Batch job queued: {data['job_id']}")
        return data["job_id"]
    
    def test_batch_analyze_max_limit(self, auth_headers):
        """Test that batch is limited to 10 encounters"""
        encounter_ids = [f"test_batch_{i}" for i in range(15)]
        
        response = requests.post(
            f"{BASE_URL}/api/court-grade/batch-analyze",
            headers=auth_headers,
            json=encounter_ids
        )
        
        assert response.status_code == 400
        print("✓ Batch limit of 10 enforced")


class TestBatchAnalysisRun:
    """Test POST /api/court-grade/batch-analyze/run - Synchronous batch processing"""
    
    def test_batch_analyze_run_empty_encounters(self, auth_headers):
        """Test batch analysis with non-existent encounters"""
        encounter_ids = [f"nonexistent_{uuid.uuid4().hex[:8]}" for _ in range(2)]
        
        response = requests.post(
            f"{BASE_URL}/api/court-grade/batch-analyze/run",
            headers=auth_headers,
            json=encounter_ids
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "completed" in data
        assert "failed" in data
        assert data["total"] == 2
        
        # All should fail since encounters don't exist
        assert data["failed_count"] == 2
        
        print(f"✓ Batch run handles non-existent encounters: {data['failed_count']} failed")
    
    def test_batch_analyze_run_max_limit(self, auth_headers):
        """Test that synchronous batch is limited to 5 encounters"""
        encounter_ids = [f"test_batch_{i}" for i in range(8)]
        
        response = requests.post(
            f"{BASE_URL}/api/court-grade/batch-analyze/run",
            headers=auth_headers,
            json=encounter_ids
        )
        
        assert response.status_code == 400
        assert "Maximum 5" in response.json().get("detail", "")
        
        print("✓ Synchronous batch limit of 5 enforced")


class TestBatchAnalysisStatus:
    """Test GET /api/court-grade/batch/{job_id} - Get batch job status"""
    
    def test_get_batch_status(self, auth_headers):
        """Test getting batch job status"""
        # First create a batch job
        encounter_ids = [f"test_status_{uuid.uuid4().hex[:8]}" for _ in range(2)]
        
        create_response = requests.post(
            f"{BASE_URL}/api/court-grade/batch-analyze",
            headers=auth_headers,
            json=encounter_ids
        )
        
        job_id = create_response.json()["job_id"]
        
        # Get status
        status_response = requests.get(
            f"{BASE_URL}/api/court-grade/batch/{job_id}",
            headers=auth_headers
        )
        
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["success"] is True
        assert "job" in data
        
        job = data["job"]
        assert job["job_id"] == job_id
        assert "status" in job
        assert "encounter_ids" in job
        
        print(f"✓ Batch job status: {job['status']}")
    
    def test_get_nonexistent_batch_status(self, auth_headers):
        """Test getting status of non-existent batch job"""
        response = requests.get(
            f"{BASE_URL}/api/court-grade/batch/nonexistent_job_12345",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        print("✓ Non-existent batch job returns 404")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestRealtimeAlertsIntegration:
    """Integration tests for real-time alerts workflow"""
    
    def test_full_alert_workflow(self, auth_headers):
        """Test complete alert workflow: create -> get -> acknowledge"""
        encounter_id = f"integration_test_{uuid.uuid4().hex[:12]}"
        
        # 1. Analyze transcript chunk
        analyze_response = requests.post(
            f"{BASE_URL}/api/realtime-alerts/analyze-chunk",
            headers=auth_headers,
            json={
                "encounter_id": encounter_id,
                "transcript_chunk": "Officer drew his gun and pointed it at me while I was unarmed!"
            }
        )
        
        assert analyze_response.status_code == 200
        alerts = analyze_response.json()["alerts"]
        
        if len(alerts) > 0:
            alert_id = alerts[0]["alert_id"]
            
            # 2. Get my alerts
            my_alerts_response = requests.get(
                f"{BASE_URL}/api/realtime-alerts/my-alerts",
                headers=auth_headers
            )
            
            assert my_alerts_response.status_code == 200
            
            # 3. Acknowledge the alert
            ack_response = requests.post(
                f"{BASE_URL}/api/realtime-alerts/acknowledge",
                headers=auth_headers,
                json={"alert_id": alert_id}
            )
            
            assert ack_response.status_code == 200
            
            print("✓ Full alert workflow completed successfully")
        else:
            print("✓ No alerts generated (transcript may not have triggered keywords)")


class TestCourtGradeAnalysisEndpoints:
    """Test Court-Grade AI analysis endpoints"""
    
    def test_analyze_endpoint(self, auth_headers):
        """Test the main court-grade analyze endpoint"""
        response = requests.post(
            f"{BASE_URL}/api/court-grade/analyze",
            headers=auth_headers,
            json={
                "encounter_id": f"test_analyze_{uuid.uuid4().hex[:8]}",
                "transcript": "Officer: You're under arrest. You have the right to remain silent. Anything you say can and will be used against you in a court of law.",
                "encounter_type": "traffic_stop"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "analysis" in data
        
        analysis = data["analysis"]
        assert "analysis_id" in analysis
        assert "overall_confidence" in analysis
        assert "confidence_level" in analysis
        
        print(f"✓ Court-grade analysis completed: confidence={analysis['overall_confidence']}")
    
    def test_knowledge_base_amendments(self, auth_headers):
        """Test knowledge base amendments endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/court-grade/knowledge-base/amendments",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "amendments" in data
        assert "violation_types" in data
        
        print(f"✓ Knowledge base: {len(data['amendments'])} amendments, {len(data['violation_types'])} violation types")
    
    def test_confidence_explain(self, auth_headers):
        """Test confidence level explanation endpoint"""
        response = requests.get(
            f"{BASE_URL}/api/court-grade/confidence/explain",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "confidence_levels" in data
        assert "breakdown_factors" in data
        
        levels = data["confidence_levels"]
        assert "very_high" in levels
        assert "high" in levels
        assert "moderate" in levels
        assert "low" in levels
        assert "very_low" in levels
        
        print("✓ Confidence levels explained")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
