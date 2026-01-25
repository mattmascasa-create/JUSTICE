"""
Officer Accountability Service
Handles officer profiles, violation tracking, and scoring calculations
"""
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict
from app.db.database import db
from app.models.accountability import (
    OfficerCreate, OfficerProfile, OfficerViolation,
    DepartmentCreate, DepartmentProfile,
    ViolationType, ViolationSeverity, ViolationOutcome, DisciplinaryAction,
    VIOLATION_SEVERITY_WEIGHTS, DEPARTMENT_SCORE_WEIGHTS, VIOLATION_AMENDMENTS
)


class AccountabilityService:
    """Service for managing officer and department accountability data"""
    
    # ============== Officer Management ==============
    
    async def create_officer(self, data: OfficerCreate, created_by: str) -> dict:
        """Create a new officer profile"""
        now = datetime.now(timezone.utc).isoformat()
        
        # Check if officer already exists
        existing = await db.officers.find_one({
            "badge_number": data.badge_number,
            "department_id": data.department_id
        })
        if existing:
            return {"success": False, "error": "Officer with this badge number already exists in department"}
        
        # Get department name
        department = await db.accountability_departments.find_one(
            {"department_id": data.department_id},
            {"_id": 0, "name": 1}
        )
        department_name = department.get("name", "Unknown") if department else "Unknown"
        
        officer_id = f"officer_{uuid.uuid4().hex[:12]}"
        
        officer = {
            "officer_id": officer_id,
            "badge_number": data.badge_number,
            "department_id": data.department_id,
            "department_name": department_name,
            "first_name": data.first_name,
            "last_name": data.last_name,
            "full_name": f"{data.first_name} {data.last_name}",
            "rank": data.rank or "Officer",
            "unit": data.unit,
            "hire_date": data.hire_date,
            "photo_url": data.photo_url,
            
            # Initial scores
            "accountability_score": 100.0,
            "total_violations": 0,
            "sustained_violations": 0,
            "pending_violations": 0,
            "violations_by_type": {},
            "violations_by_severity": {},
            "disciplinary_actions": [],
            "settlements_involved": 0,
            "settlement_total": 0.0,
            
            "status": "active",
            "last_incident_date": None,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now
        }
        
        await db.officers.insert_one(officer)
        
        return {
            "success": True,
            "officer_id": officer_id,
            "message": f"Officer {data.first_name} {data.last_name} (Badge #{data.badge_number}) created"
        }
    
    async def get_officer(self, officer_id: str) -> Optional[dict]:
        """Get officer profile by ID"""
        return await db.officers.find_one(
            {"officer_id": officer_id},
            {"_id": 0}
        )
    
    async def get_officer_by_badge(self, badge_number: str, department_id: str) -> Optional[dict]:
        """Get officer by badge number and department"""
        return await db.officers.find_one(
            {"badge_number": badge_number, "department_id": department_id},
            {"_id": 0}
        )
    
    async def search_officers(
        self, 
        query: str = None,
        department_id: str = None,
        min_violations: int = None,
        max_score: float = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """Search officers with filters"""
        filter_query = {}
        
        if query:
            filter_query["$or"] = [
                {"full_name": {"$regex": query, "$options": "i"}},
                {"badge_number": {"$regex": query, "$options": "i"}}
            ]
        
        if department_id:
            filter_query["department_id"] = department_id
        
        if min_violations:
            filter_query["total_violations"] = {"$gte": min_violations}
        
        if max_score:
            filter_query["accountability_score"] = {"$lte": max_score}
        
        officers = await db.officers.find(
            filter_query,
            {"_id": 0}
        ).sort("accountability_score", 1).skip(offset).limit(limit).to_list(limit)
        
        return officers
    
    async def find_or_create_officer(
        self,
        badge_number: str,
        department_id: str,
        department_name: str = None,
        first_name: str = "Unknown",
        last_name: str = "Officer",
        created_by: str = "system"
    ) -> dict:
        """Find existing officer or create placeholder"""
        existing = await self.get_officer_by_badge(badge_number, department_id)
        if existing:
            return existing
        
        # Create placeholder officer
        data = OfficerCreate(
            badge_number=badge_number,
            department_id=department_id,
            first_name=first_name,
            last_name=last_name
        )
        result = await self.create_officer(data, created_by)
        
        if result.get("success"):
            return await self.get_officer(result["officer_id"])
        return None
    
    # ============== Violation Management ==============
    
    async def report_violation(
        self,
        badge_number: str,
        department_id: str,
        violation_type: str,
        severity: str,
        description: str,
        incident_date: str,
        reported_by: str,
        encounter_id: str = None,
        evidence_ids: List[str] = None,
        ai_analysis_id: str = None,
        ai_confidence: float = None,
        incident_location: dict = None,
        relevant_statutes: List[str] = None,
        case_law_citations: List[str] = None
    ) -> dict:
        """Report a violation against an officer"""
        now = datetime.now(timezone.utc).isoformat()
        
        # Get or create department
        department = await self.find_or_create_department(department_id)
        if not department:
            return {"success": False, "error": "Department not found"}
        
        # Get or create officer
        officer = await self.find_or_create_officer(
            badge_number=badge_number,
            department_id=department_id,
            department_name=department.get("name"),
            created_by=reported_by
        )
        if not officer:
            return {"success": False, "error": "Could not find or create officer"}
        
        violation_id = f"viol_{uuid.uuid4().hex[:12]}"
        
        # Get constitutional amendment if applicable
        vtype = ViolationType(violation_type) if violation_type in [v.value for v in ViolationType] else None
        amendment = VIOLATION_AMENDMENTS.get(vtype) if vtype else None
        
        violation = {
            "violation_id": violation_id,
            "officer_id": officer["officer_id"],
            "badge_number": badge_number,
            "department_id": department_id,
            "department_name": department.get("name"),
            "officer_name": officer.get("full_name"),
            "encounter_id": encounter_id,
            
            "violation_type": violation_type,
            "severity": severity,
            "description": description,
            
            "evidence_ids": evidence_ids or [],
            "ai_analysis_id": ai_analysis_id,
            "ai_confidence": ai_confidence,
            
            "incident_date": incident_date,
            "incident_location": incident_location,
            
            "constitutional_amendment": amendment,
            "relevant_statutes": relevant_statutes or [],
            "case_law_citations": case_law_citations or [],
            
            "outcome": ViolationOutcome.PENDING.value,
            "disciplinary_action": DisciplinaryAction.NONE.value,
            "settlement_amount": None,
            
            "reported_by": reported_by,
            "reporter_type": "citizen",
            
            "verified": False,
            "verified_by": None,
            "verified_at": None,
            
            "evidence_hash": None,
            "blockchain_proof": None,
            
            "created_at": now,
            "updated_at": now
        }
        
        # Generate evidence hash if evidence exists
        if evidence_ids:
            hash_input = f"{violation_id}:{':'.join(evidence_ids)}:{incident_date}"
            violation["evidence_hash"] = hashlib.sha256(hash_input.encode()).hexdigest()
        
        await db.officer_violations.insert_one(violation)
        
        # Update officer stats
        await self._update_officer_stats(officer["officer_id"])
        
        # Update department stats
        await self._update_department_stats(department_id)
        
        return {
            "success": True,
            "violation_id": violation_id,
            "officer_id": officer["officer_id"],
            "message": f"Violation reported against Officer {officer.get('full_name')} (Badge #{badge_number})"
        }
    
    async def get_officer_violations(self, officer_id: str, limit: int = 100) -> List[dict]:
        """Get all violations for an officer"""
        return await db.officer_violations.find(
            {"officer_id": officer_id},
            {"_id": 0}
        ).sort("incident_date", -1).limit(limit).to_list(limit)
    
    async def update_violation_outcome(
        self,
        violation_id: str,
        outcome: str,
        disciplinary_action: str = None,
        settlement_amount: float = None,
        updated_by: str = None
    ) -> dict:
        """Update violation outcome"""
        now = datetime.now(timezone.utc).isoformat()
        
        violation = await db.officer_violations.find_one({"violation_id": violation_id})
        if not violation:
            return {"success": False, "error": "Violation not found"}
        
        update_data = {
            "outcome": outcome,
            "updated_at": now
        }
        
        if disciplinary_action:
            update_data["disciplinary_action"] = disciplinary_action
        
        if settlement_amount:
            update_data["settlement_amount"] = settlement_amount
        
        await db.officer_violations.update_one(
            {"violation_id": violation_id},
            {"$set": update_data}
        )
        
        # Recalculate scores
        await self._update_officer_stats(violation["officer_id"])
        await self._update_department_stats(violation["department_id"])
        
        return {"success": True, "message": "Violation outcome updated"}
    
    # ============== Department Management ==============
    
    async def create_department(self, data: DepartmentCreate, created_by: str) -> dict:
        """Create a new department"""
        now = datetime.now(timezone.utc).isoformat()
        
        department_id = f"dept_{uuid.uuid4().hex[:12]}"
        
        department = {
            "department_id": department_id,
            "name": data.name,
            "city": data.city,
            "state": data.state,
            "county": data.county,
            "jurisdiction_type": data.jurisdiction_type,
            "total_officers": data.total_officers or 0,
            "website": data.website,
            
            # Scores
            "accountability_score": 100.0,
            "transparency_grade": "A",
            "use_of_force_score": 100.0,
            "complaint_resolution_score": 100.0,
            "settlement_score": 100.0,
            "officer_accountability_score": 100.0,
            "transparency_score": 100.0,
            
            # Stats
            "total_violations": 0,
            "sustained_violations": 0,
            "pending_violations": 0,
            "officers_with_violations": 0,
            "repeat_offenders": 0,
            "total_settlements": 0.0,
            "avg_settlement": 0.0,
            "violations_by_type": {},
            "violations_by_severity": {},
            
            "state_rank": None,
            "national_rank": None,
            "last_incident_date": None,
            "data_last_updated": now,
            "created_by": created_by,
            "created_at": now
        }
        
        await db.accountability_departments.insert_one(department)
        
        return {
            "success": True,
            "department_id": department_id,
            "message": f"Department {data.name} created"
        }
    
    async def get_department(self, department_id: str) -> Optional[dict]:
        """Get department by ID"""
        return await db.accountability_departments.find_one(
            {"department_id": department_id},
            {"_id": 0}
        )
    
    async def find_or_create_department(
        self,
        department_id: str = None,
        name: str = None,
        city: str = None,
        state: str = None
    ) -> Optional[dict]:
        """Find department by ID or create from name/location"""
        if department_id:
            dept = await self.get_department(department_id)
            if dept:
                return dept
        
        # Try to find by name and location
        if name:
            dept = await db.accountability_departments.find_one(
                {"name": {"$regex": name, "$options": "i"}},
                {"_id": 0}
            )
            if dept:
                return dept
        
        # Create new department if we have enough info
        if name and state:
            data = DepartmentCreate(
                name=name,
                city=city or "Unknown",
                state=state
            )
            result = await self.create_department(data, "system")
            if result.get("success"):
                return await self.get_department(result["department_id"])
        
        return None
    
    async def search_departments(
        self,
        query: str = None,
        state: str = None,
        max_score: float = None,
        sort_by: str = "accountability_score",
        limit: int = 50,
        offset: int = 0
    ) -> List[dict]:
        """Search departments with filters"""
        filter_query = {}
        
        if query:
            filter_query["$or"] = [
                {"name": {"$regex": query, "$options": "i"}},
                {"city": {"$regex": query, "$options": "i"}}
            ]
        
        if state and state != "all":
            filter_query["state"] = state
        
        if max_score:
            filter_query["accountability_score"] = {"$lte": max_score}
        
        # Determine sort
        sort_order = 1 if sort_by == "accountability_score" else -1
        if sort_by == "name":
            sort_order = 1
        
        departments = await db.accountability_departments.find(
            filter_query,
            {"_id": 0}
        ).sort(sort_by, sort_order).skip(offset).limit(limit).to_list(limit)
        
        return departments
    
    async def get_department_leaderboard(self, state: str = None, limit: int = 20) -> dict:
        """Get departments ranked by accountability score"""
        filter_query = {}
        if state and state != "all":
            filter_query["state"] = state
        
        # Best departments
        best = await db.accountability_departments.find(
            filter_query,
            {"_id": 0}
        ).sort("accountability_score", -1).limit(limit).to_list(limit)
        
        # Worst departments
        worst = await db.accountability_departments.find(
            filter_query,
            {"_id": 0}
        ).sort("accountability_score", 1).limit(limit).to_list(limit)
        
        return {
            "best_departments": best,
            "worst_departments": worst,
            "state_filter": state
        }
    
    # ============== Score Calculations ==============
    
    async def _update_officer_stats(self, officer_id: str):
        """Recalculate officer statistics and score"""
        violations = await db.officer_violations.find(
            {"officer_id": officer_id},
            {"_id": 0}
        ).to_list(1000)
        
        if not violations:
            return
        
        # Calculate stats
        total = len(violations)
        sustained = sum(1 for v in violations if v.get("outcome") == "sustained")
        pending = sum(1 for v in violations if v.get("outcome") == "pending")
        
        # Violations by type
        by_type = {}
        by_severity = {}
        for v in violations:
            vtype = v.get("violation_type", "unknown")
            severity = v.get("severity", "unknown")
            by_type[vtype] = by_type.get(vtype, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # Calculate accountability score
        score = self._calculate_officer_score(violations)
        
        # Get disciplinary actions
        actions = list(set(v.get("disciplinary_action") for v in violations if v.get("disciplinary_action") != "none"))
        
        # Settlement totals
        settlements = [v.get("settlement_amount", 0) for v in violations if v.get("settlement_amount")]
        settlement_total = sum(settlements)
        settlements_involved = len(settlements)
        
        # Last incident
        sorted_violations = sorted(violations, key=lambda x: x.get("incident_date", ""), reverse=True)
        last_incident = sorted_violations[0].get("incident_date") if sorted_violations else None
        
        # Update officer
        await db.officers.update_one(
            {"officer_id": officer_id},
            {"$set": {
                "accountability_score": score,
                "total_violations": total,
                "sustained_violations": sustained,
                "pending_violations": pending,
                "violations_by_type": by_type,
                "violations_by_severity": by_severity,
                "disciplinary_actions": actions,
                "settlements_involved": settlements_involved,
                "settlement_total": settlement_total,
                "last_incident_date": last_incident,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    def _calculate_officer_score(self, violations: List[dict]) -> float:
        """Calculate officer accountability score (0-100)"""
        if not violations:
            return 100.0
        
        # Start at 100, deduct based on violations
        score = 100.0
        
        for v in violations:
            severity = v.get("severity", "minor")
            outcome = v.get("outcome", "pending")
            
            # Get weight
            try:
                weight = VIOLATION_SEVERITY_WEIGHTS.get(ViolationSeverity(severity), 1)
            except:
                weight = 1
            
            # Apply outcome modifier
            if outcome == "sustained":
                modifier = 1.0  # Full weight
            elif outcome == "pending":
                modifier = 0.5  # Half weight while pending
            elif outcome == "not_sustained":
                modifier = 0.1  # Small impact
            else:
                modifier = 0.0  # No impact for exonerated/unfounded
            
            # Deduct from score
            deduction = weight * modifier * 2  # 2 points per weight unit
            score -= deduction
        
        return max(0.0, min(100.0, score))
    
    async def _update_department_stats(self, department_id: str):
        """Recalculate department statistics and score"""
        # Get all violations for department
        violations = await db.officer_violations.find(
            {"department_id": department_id},
            {"_id": 0}
        ).to_list(10000)
        
        # Get all officers in department
        officers = await db.officers.find(
            {"department_id": department_id},
            {"_id": 0, "officer_id": 1, "accountability_score": 1, "total_violations": 1}
        ).to_list(10000)
        
        # Calculate stats
        total_violations = len(violations)
        sustained = sum(1 for v in violations if v.get("outcome") == "sustained")
        pending = sum(1 for v in violations if v.get("outcome") == "pending")
        
        # Violations by type and severity
        by_type = {}
        by_severity = {}
        for v in violations:
            vtype = v.get("violation_type", "unknown")
            severity = v.get("severity", "unknown")
            by_type[vtype] = by_type.get(vtype, 0) + 1
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # Officer stats
        officers_with_violations = sum(1 for o in officers if o.get("total_violations", 0) > 0)
        repeat_offenders = sum(1 for o in officers if o.get("total_violations", 0) >= 3)
        
        # Settlements
        settlements = [v.get("settlement_amount", 0) for v in violations if v.get("settlement_amount")]
        total_settlements = sum(settlements)
        avg_settlement = total_settlements / len(settlements) if settlements else 0
        
        # Calculate component scores
        use_of_force_violations = sum(1 for v in violations if v.get("violation_type") == "excessive_force")
        use_of_force_score = max(0, 100 - (use_of_force_violations * 5))
        
        resolution_rate = sustained / total_violations if total_violations > 0 else 1.0
        complaint_resolution_score = 100 - (resolution_rate * 50)  # Lower sustained = better
        
        settlement_score = max(0, 100 - (total_settlements / 100000))  # -1 point per $1000
        
        officer_scores = [o.get("accountability_score", 100) for o in officers]
        officer_accountability_score = sum(officer_scores) / len(officer_scores) if officer_scores else 100
        
        transparency_score = 80.0  # Base score, could be enhanced with data availability metrics
        
        # Calculate overall score
        overall_score = (
            use_of_force_score * DEPARTMENT_SCORE_WEIGHTS["use_of_force"] +
            complaint_resolution_score * DEPARTMENT_SCORE_WEIGHTS["complaint_resolution"] +
            settlement_score * DEPARTMENT_SCORE_WEIGHTS["settlements"] +
            officer_accountability_score * DEPARTMENT_SCORE_WEIGHTS["officer_accountability"] +
            transparency_score * DEPARTMENT_SCORE_WEIGHTS["transparency"]
        )
        
        # Determine grade
        if overall_score >= 90:
            grade = "A"
        elif overall_score >= 80:
            grade = "B"
        elif overall_score >= 70:
            grade = "C"
        elif overall_score >= 60:
            grade = "D"
        else:
            grade = "F"
        
        # Last incident
        sorted_violations = sorted(violations, key=lambda x: x.get("incident_date", ""), reverse=True)
        last_incident = sorted_violations[0].get("incident_date") if sorted_violations else None
        
        # Update department
        await db.accountability_departments.update_one(
            {"department_id": department_id},
            {"$set": {
                "accountability_score": round(overall_score, 1),
                "transparency_grade": grade,
                "use_of_force_score": round(use_of_force_score, 1),
                "complaint_resolution_score": round(complaint_resolution_score, 1),
                "settlement_score": round(settlement_score, 1),
                "officer_accountability_score": round(officer_accountability_score, 1),
                "transparency_score": round(transparency_score, 1),
                "total_violations": total_violations,
                "sustained_violations": sustained,
                "pending_violations": pending,
                "officers_with_violations": officers_with_violations,
                "repeat_offenders": repeat_offenders,
                "total_settlements": total_settlements,
                "avg_settlement": round(avg_settlement, 2),
                "violations_by_type": by_type,
                "violations_by_severity": by_severity,
                "last_incident_date": last_incident,
                "data_last_updated": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    async def recalculate_all_rankings(self):
        """Recalculate state and national rankings for all departments"""
        # Get all departments
        departments = await db.accountability_departments.find(
            {},
            {"_id": 0, "department_id": 1, "state": 1, "accountability_score": 1}
        ).to_list(10000)
        
        # Sort by score for national ranking
        sorted_national = sorted(departments, key=lambda x: x.get("accountability_score", 0), reverse=True)
        
        # Group by state
        by_state = {}
        for d in departments:
            state = d.get("state", "Unknown")
            if state not in by_state:
                by_state[state] = []
            by_state[state].append(d)
        
        # Calculate rankings
        for i, dept in enumerate(sorted_national):
            national_rank = i + 1
            
            state = dept.get("state")
            state_depts = sorted(by_state.get(state, []), key=lambda x: x.get("accountability_score", 0), reverse=True)
            state_rank = next((j + 1 for j, d in enumerate(state_depts) if d["department_id"] == dept["department_id"]), None)
            
            await db.accountability_departments.update_one(
                {"department_id": dept["department_id"]},
                {"$set": {"national_rank": national_rank, "state_rank": state_rank}}
            )


# Create singleton instance
accountability_service = AccountabilityService()
