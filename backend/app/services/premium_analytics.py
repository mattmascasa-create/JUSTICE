"""
Premium Analytics Service - Predictive analytics and trend analysis for police accountability
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict
import uuid

from app.db.database import db

logger = logging.getLogger(__name__)


class PremiumAnalyticsService:
    """
    Premium tier analytics for police accountability:
    - Predictive risk scoring
    - Trend analysis
    - Audit report generation
    - Department comparison
    """
    
    async def get_department_risk_prediction(self, department_id: str) -> Dict:
        """
        Predict future violation risk for a department based on historical patterns.
        Uses weighted factors: recent violations, settlement trends, officer turnover.
        """
        # Get department
        dept = await db.accountability_departments.find_one(
            {"department_id": department_id},
            {"_id": 0}
        )
        if not dept:
            return {"error": "Department not found"}
        
        # Get violation history
        violations = await db.officer_violations.find(
            {"department_id": department_id},
            {"_id": 0, "incident_date": 1, "severity": 1, "outcome": 1, "settlement_amount": 1}
        ).to_list(500)
        
        # Calculate risk factors
        now = datetime.now(timezone.utc)
        recent_30_days = [v for v in violations if self._parse_date(v.get("incident_date")) and 
                         (now - self._parse_date(v.get("incident_date"))).days <= 30]
        recent_90_days = [v for v in violations if self._parse_date(v.get("incident_date")) and 
                         (now - self._parse_date(v.get("incident_date"))).days <= 90]
        recent_year = [v for v in violations if self._parse_date(v.get("incident_date")) and 
                      (now - self._parse_date(v.get("incident_date"))).days <= 365]
        
        # Risk factor calculations
        recent_violation_rate = len(recent_30_days) * 12  # Annualized
        quarterly_trend = len(recent_30_days) / max(len(recent_90_days) / 3, 1) if recent_90_days else 1
        
        # Severity score (weighted by recency)
        def get_severity(v):
            """Extract severity as float"""
            sev = v.get("severity", 5)
            if isinstance(sev, str):
                # Map severity strings to numbers
                mapping = {"minor": 2, "moderate": 4, "serious": 7, "critical": 9}
                return mapping.get(sev.lower(), 5)
            return float(sev) if sev else 5
        
        severity_score = sum(get_severity(v) * (1 if v in recent_30_days else 0.5 if v in recent_90_days else 0.25) 
                            for v in violations[-50:]) / max(len(violations[-50:]), 1)
        
        # Settlement trend
        settlements = [v.get("settlement_amount", 0) for v in recent_year if v.get("settlement_amount")]
        settlement_trend = sum(settlements) if settlements else 0
        
        # Calculate composite risk score (0-100)
        risk_score = min(100, (
            (recent_violation_rate / 12) * 30 +  # Recent violations (30% weight)
            (quarterly_trend - 1) * 20 +         # Trend direction (20% weight)
            (severity_score / 10) * 25 +         # Severity (25% weight)
            min(settlement_trend / 1000000, 1) * 25  # Settlements (25% weight)
        ))
        
        # Risk level classification
        if risk_score >= 70:
            risk_level = "critical"
            prediction = "High probability of significant violations in next 90 days"
        elif risk_score >= 50:
            risk_level = "elevated"
            prediction = "Elevated risk of violations, recommend enhanced monitoring"
        elif risk_score >= 30:
            risk_level = "moderate"
            prediction = "Normal risk profile, standard oversight sufficient"
        else:
            risk_level = "low"
            prediction = "Below average risk, positive accountability trend"
        
        return {
            "department_id": department_id,
            "department_name": dept.get("name"),
            "risk_score": round(risk_score, 1),
            "risk_level": risk_level,
            "prediction": prediction,
            "factors": {
                "recent_violation_rate": recent_violation_rate,
                "quarterly_trend": round(quarterly_trend, 2),
                "average_severity": round(severity_score, 2),
                "settlement_trend_ytd": settlement_trend,
                "total_violations_30d": len(recent_30_days),
                "total_violations_90d": len(recent_90_days),
                "total_violations_year": len(recent_year)
            },
            "recommendations": self._get_risk_recommendations(risk_level, quarterly_trend, severity_score),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime (timezone-aware)"""
        if not date_str:
            return None
        try:
            if isinstance(date_str, datetime):
                # Ensure timezone-aware
                if date_str.tzinfo is None:
                    return date_str.replace(tzinfo=timezone.utc)
                return date_str
            # Try ISO format first
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                return dt.replace(tzinfo=timezone.utc)
            except:
                return None
    
    def _get_risk_recommendations(self, risk_level: str, trend: float, severity: float) -> List[str]:
        """Generate recommendations based on risk factors"""
        recs = []
        
        if risk_level in ["critical", "elevated"]:
            recs.append("Implement immediate oversight review")
            recs.append("Schedule department leadership meeting")
            
        if trend > 1.5:
            recs.append("Investigate cause of increasing violation trend")
            recs.append("Review recent policy changes or personnel additions")
            
        if severity > 7:
            recs.append("Focus on de-escalation training")
            recs.append("Review use of force policies")
            
        if risk_level == "low":
            recs.append("Continue current accountability practices")
            recs.append("Consider as model for other departments")
            
        return recs
    
    async def get_violation_trends(
        self,
        department_id: Optional[str] = None,
        state: Optional[str] = None,
        months: int = 12
    ) -> Dict:
        """
        Analyze violation trends over time with breakdown by type and severity.
        """
        def get_severity_num(v):
            """Extract severity as number"""
            sev = v.get("severity", 5)
            if isinstance(sev, str):
                mapping = {"minor": 2, "moderate": 4, "serious": 7, "critical": 9}
                return mapping.get(sev.lower(), 5)
            return float(sev) if sev else 5
        
        query = {}
        if department_id:
            query["department_id"] = department_id
        
        # Get violations with dates
        violations = await db.officer_violations.find(
            query,
            {"_id": 0, "incident_date": 1, "violation_type": 1, "severity": 1, "outcome": 1, "department_id": 1}
        ).sort("incident_date", -1).to_list(2000)
        
        # Group by month
        monthly_data = {}
        type_breakdown = {}
        severity_distribution = {"minor": 0, "moderate": 0, "serious": 0, "critical": 0}
        outcome_distribution = {}
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=months * 30)
        
        for v in violations:
            date = self._parse_date(v.get("incident_date"))
            if not date or date < cutoff_date:
                continue
                
            month_key = date.strftime("%Y-%m")
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {"count": 0, "severity_sum": 0}
            monthly_data[month_key]["count"] += 1
            monthly_data[month_key]["severity_sum"] += get_severity_num(v)
            
            # Type breakdown
            vtype = v.get("violation_type", "unknown")
            type_breakdown[vtype] = type_breakdown.get(vtype, 0) + 1
            
            # Severity
            severity = get_severity_num(v)
            if severity <= 3:
                severity_distribution["minor"] += 1
            elif severity <= 5:
                severity_distribution["moderate"] += 1
            elif severity <= 7:
                severity_distribution["serious"] += 1
            else:
                severity_distribution["critical"] += 1
            
            # Outcome
            outcome = v.get("outcome", "pending")
            outcome_distribution[outcome] = outcome_distribution.get(outcome, 0) + 1
        
        # Calculate trends
        sorted_months = sorted(monthly_data.keys())
        if len(sorted_months) >= 2:
            first_half = sorted_months[:len(sorted_months)//2]
            second_half = sorted_months[len(sorted_months)//2:]
            
            first_half_avg = sum(monthly_data[m]["count"] for m in first_half) / max(len(first_half), 1)
            second_half_avg = sum(monthly_data[m]["count"] for m in second_half) / max(len(second_half), 1)
            
            trend_direction = "increasing" if second_half_avg > first_half_avg * 1.1 else \
                             "decreasing" if second_half_avg < first_half_avg * 0.9 else "stable"
            trend_percentage = ((second_half_avg - first_half_avg) / max(first_half_avg, 1)) * 100
        else:
            trend_direction = "insufficient_data"
            trend_percentage = 0
        
        return {
            "period_months": months,
            "filters": {"department_id": department_id, "state": state},
            "monthly_breakdown": [
                {
                    "month": m,
                    "count": monthly_data[m]["count"],
                    "avg_severity": round(monthly_data[m]["severity_sum"] / max(monthly_data[m]["count"], 1), 2)
                }
                for m in sorted_months
            ],
            "type_breakdown": dict(sorted(type_breakdown.items(), key=lambda x: x[1], reverse=True)),
            "severity_distribution": severity_distribution,
            "outcome_distribution": outcome_distribution,
            "trend_analysis": {
                "direction": trend_direction,
                "change_percentage": round(trend_percentage, 1),
                "interpretation": self._interpret_trend(trend_direction, trend_percentage)
            },
            "total_violations": sum(monthly_data[m]["count"] for m in monthly_data),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _interpret_trend(self, direction: str, percentage: float) -> str:
        """Generate human-readable trend interpretation"""
        if direction == "increasing":
            if abs(percentage) > 50:
                return f"Significant increase of {abs(percentage):.0f}% - immediate attention required"
            return f"Violations increasing by {abs(percentage):.0f}% - monitor closely"
        elif direction == "decreasing":
            if abs(percentage) > 50:
                return f"Major improvement with {abs(percentage):.0f}% reduction"
            return f"Positive trend with {abs(percentage):.0f}% decrease"
        return "Violation rate remains stable"
    
    async def generate_audit_report(
        self,
        department_id: Optional[str] = None,
        state: Optional[str] = None,
        include_officers: bool = True,
        include_settlements: bool = True
    ) -> Dict:
        """
        Generate comprehensive audit report for oversight committees.
        """
        report_id = f"audit_{uuid.uuid4().hex[:8]}"
        
        # Build query
        dept_query = {}
        if department_id:
            dept_query["department_id"] = department_id
        if state:
            dept_query["state"] = state.upper()
        
        # Get departments
        departments = await db.accountability_departments.find(
            dept_query,
            {"_id": 0}
        ).to_list(100)
        
        # Aggregate statistics
        total_officers = 0
        total_violations = 0
        total_settlements = 0
        department_summaries = []
        
        for dept in departments:
            # Get officers
            officers = await db.officers.find(
                {"department_id": dept["department_id"]},
                {"_id": 0}
            ).to_list(500)
            
            # Get violations
            violations = await db.officer_violations.find(
                {"department_id": dept["department_id"]},
                {"_id": 0}
            ).to_list(1000)
            
            dept_settlements = sum(v.get("settlement_amount", 0) for v in violations)
            
            total_officers += len(officers)
            total_violations += len(violations)
            total_settlements += dept_settlements
            
            # Top violators
            officer_violations = {}
            for v in violations:
                oid = v.get("officer_id", "unknown")
                officer_violations[oid] = officer_violations.get(oid, 0) + 1
            
            top_violators = sorted(officer_violations.items(), key=lambda x: x[1], reverse=True)[:5]
            
            summary = {
                "department_id": dept["department_id"],
                "name": dept.get("name"),
                "city": dept.get("city"),
                "state": dept.get("state"),
                "accountability_score": dept.get("accountability_score"),
                "officer_count": len(officers),
                "violation_count": len(violations),
                "settlement_total": dept_settlements,
                "violations_per_officer": round(len(violations) / max(len(officers), 1), 2)
            }
            
            if include_officers:
                summary["top_violators"] = [
                    {"officer_id": oid, "violation_count": count}
                    for oid, count in top_violators
                ]
            
            department_summaries.append(summary)
        
        # Sort departments by violations per officer (worst first)
        department_summaries.sort(
            key=lambda x: x["violations_per_officer"],
            reverse=True
        )
        
        report = {
            "report_id": report_id,
            "report_type": "accountability_audit",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "filters": {
                "department_id": department_id,
                "state": state,
                "include_officers": include_officers,
                "include_settlements": include_settlements
            },
            "executive_summary": {
                "departments_analyzed": len(departments),
                "total_officers_tracked": total_officers,
                "total_violations_recorded": total_violations,
                "total_settlements": total_settlements if include_settlements else "hidden",
                "average_violations_per_officer": round(total_violations / max(total_officers, 1), 2),
                "average_settlement_per_violation": round(total_settlements / max(total_violations, 1), 2) if include_settlements else "hidden"
            },
            "department_rankings": {
                "best_accountability": sorted(department_summaries, key=lambda x: x["accountability_score"], reverse=True)[:5],
                "worst_accountability": sorted(department_summaries, key=lambda x: x["accountability_score"])[:5],
                "highest_settlement_exposure": sorted(department_summaries, key=lambda x: x["settlement_total"], reverse=True)[:5] if include_settlements else []
            },
            "department_details": department_summaries,
            "recommendations": self._generate_audit_recommendations(department_summaries, total_violations, total_settlements)
        }
        
        # Store report
        await db.audit_reports.insert_one({
            **report,
            "created_at": datetime.now(timezone.utc)
        })
        
        return report
    
    def _generate_audit_recommendations(self, summaries: List[Dict], total_violations: int, total_settlements: float) -> List[Dict]:
        """Generate recommendations based on audit findings"""
        recs = []
        
        # Check for departments with high violations per officer
        high_violation_depts = [s for s in summaries if s["violations_per_officer"] > 1.5]
        if high_violation_depts:
            recs.append({
                "priority": "high",
                "category": "oversight",
                "recommendation": f"{len(high_violation_depts)} department(s) have >1.5 violations per officer - require immediate oversight review",
                "affected_departments": [d["name"] for d in high_violation_depts[:3]]
            })
        
        # Check settlement trends
        if total_settlements > 5000000:
            recs.append({
                "priority": "high",
                "category": "financial",
                "recommendation": f"Total settlements exceed $5M - recommend policy review and training enhancements",
                "affected_departments": [s["name"] for s in summaries if s["settlement_total"] > 500000][:3]
            })
        
        # Check for low-scoring departments
        low_score_depts = [s for s in summaries if s["accountability_score"] < 50]
        if low_score_depts:
            recs.append({
                "priority": "medium",
                "category": "accountability",
                "recommendation": f"{len(low_score_depts)} department(s) score below 50 - implement improvement plans",
                "affected_departments": [d["name"] for d in low_score_depts[:3]]
            })
        
        # Positive recognition
        high_score_depts = [s for s in summaries if s["accountability_score"] >= 80]
        if high_score_depts:
            recs.append({
                "priority": "info",
                "category": "recognition",
                "recommendation": f"{len(high_score_depts)} department(s) demonstrate excellent accountability - consider as models",
                "affected_departments": [d["name"] for d in high_score_depts[:3]]
            })
        
        return recs
    
    async def compare_departments(
        self,
        department_ids: List[str]
    ) -> Dict:
        """
        Side-by-side comparison of multiple departments.
        """
        comparisons = []
        
        for dept_id in department_ids[:10]:  # Max 10 departments
            dept = await db.accountability_departments.find_one(
                {"department_id": dept_id},
                {"_id": 0}
            )
            if not dept:
                continue
            
            violations = await db.officer_violations.find(
                {"department_id": dept_id},
                {"_id": 0}
            ).to_list(500)
            
            officers = await db.officers.find(
                {"department_id": dept_id},
                {"_id": 0, "accountability_score": 1}
            ).to_list(200)
            
            # Calculate metrics
            violation_types = {}
            for v in violations:
                vtype = v.get("violation_type", "unknown")
                violation_types[vtype] = violation_types.get(vtype, 0) + 1
            
            comparisons.append({
                "department_id": dept_id,
                "name": dept.get("name"),
                "state": dept.get("state"),
                "metrics": {
                    "accountability_score": dept.get("accountability_score"),
                    "officer_count": len(officers),
                    "violation_count": len(violations),
                    "violations_per_officer": round(len(violations) / max(len(officers), 1), 2),
                    "avg_officer_score": round(sum(o.get("accountability_score", 100) for o in officers) / max(len(officers), 1), 1),
                    "settlement_total": sum(v.get("settlement_amount", 0) for v in violations),
                    "top_violation_type": max(violation_types.items(), key=lambda x: x[1])[0] if violation_types else "none"
                }
            })
        
        # Rank departments
        if comparisons:
            comparisons.sort(key=lambda x: x["metrics"]["accountability_score"], reverse=True)
            for i, c in enumerate(comparisons):
                c["rank"] = i + 1
        
        return {
            "comparison_count": len(comparisons),
            "departments": comparisons,
            "best_performer": comparisons[0]["name"] if comparisons else None,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }


# Singleton instance
premium_analytics = PremiumAnalyticsService()
