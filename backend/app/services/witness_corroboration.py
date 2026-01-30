"""
AI Witness Corroboration Service
Cross-references user encounter evidence with other reports and public data
to find corroborating evidence from the same location, officer, or timeframe.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import uuid
import math

from app.db.database import db
from app.services.ai_service import generate_response
from app.core.config import EMERGENT_LLM_KEY


class WitnessCorroborationService:
    """
    Service for finding corroborating evidence and witnesses.
    Cross-references encounters with:
    - Other user encounters in the same area/time
    - Officer complaint history
    - Department violation patterns
    - Public incident reports
    """
    
    # Search radius in miles for nearby incidents
    NEARBY_RADIUS_MILES = 2.0
    # Time window for "similar time" incidents (hours)
    TIME_WINDOW_HOURS = 24
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in miles"""
        R = 3959  # Earth's radius in miles
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    async def find_corroborating_evidence(
        self,
        encounter_id: str,
        user_id: str
    ) -> Dict:
        """
        Find all corroborating evidence for a given encounter.
        Returns matches from multiple sources.
        """
        
        # Get the encounter details
        encounter = await db.encounters.find_one(
            {"encounter_id": encounter_id},
            {"_id": 0}
        )
        
        if not encounter:
            return {"error": "Encounter not found", "corroboration": None}
        
        location = encounter.get("location", {})
        lat = location.get("latitude") or encounter.get("latitude")
        lon = location.get("longitude") or encounter.get("longitude")
        encounter_time = encounter.get("started_at")
        officers = encounter.get("officers", [])
        
        # Run all searches in parallel
        results = await asyncio.gather(
            self._find_nearby_encounters(lat, lon, encounter_time, encounter_id, user_id),
            self._find_officer_history(officers),
            self._find_area_incidents(lat, lon, encounter_time),
            self._find_similar_violations(encounter),
            return_exceptions=True
        )
        
        nearby_encounters, officer_history, area_incidents, similar_violations = results
        
        # Handle any exceptions
        if isinstance(nearby_encounters, Exception):
            nearby_encounters = []
        if isinstance(officer_history, Exception):
            officer_history = []
        if isinstance(area_incidents, Exception):
            area_incidents = []
        if isinstance(similar_violations, Exception):
            similar_violations = []
        
        # Calculate corroboration score
        corroboration_score = self._calculate_corroboration_score(
            nearby_encounters, officer_history, area_incidents, similar_violations
        )
        
        # Generate AI analysis of corroboration
        ai_analysis = await self._generate_corroboration_analysis(
            encounter, nearby_encounters, officer_history, area_incidents, similar_violations
        )
        
        corroboration_id = f"corr_{uuid.uuid4().hex[:12]}"
        
        result = {
            "corroboration_id": corroboration_id,
            "encounter_id": encounter_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "corroboration_score": corroboration_score,
            "score_interpretation": self._interpret_score(corroboration_score),
            "nearby_encounters": {
                "count": len(nearby_encounters),
                "matches": nearby_encounters[:5],  # Top 5
                "search_radius_miles": self.NEARBY_RADIUS_MILES
            },
            "officer_history": {
                "officers_found": len(officer_history),
                "total_prior_complaints": sum(o.get("complaint_count", 0) for o in officer_history),
                "officers": officer_history
            },
            "area_incidents": {
                "count": len(area_incidents),
                "incidents": area_incidents[:10],
                "time_window_hours": self.TIME_WINDOW_HOURS
            },
            "similar_violations": {
                "count": len(similar_violations),
                "patterns": similar_violations[:5]
            },
            "ai_analysis": ai_analysis,
            "legal_value": self._assess_legal_value(corroboration_score, nearby_encounters, officer_history)
        }
        
        # Store the corroboration result
        await db.corroborations.insert_one({
            **result,
            "user_id": user_id
        })
        
        return result
    
    async def _find_nearby_encounters(
        self,
        lat: Optional[float],
        lon: Optional[float],
        encounter_time: Optional[str],
        exclude_encounter_id: str,
        exclude_user_id: str
    ) -> List[Dict]:
        """Find encounters from other users in the same area and timeframe"""
        
        if not lat or not lon:
            return []
        
        # Parse encounter time
        if encounter_time:
            if isinstance(encounter_time, str):
                try:
                    enc_dt = datetime.fromisoformat(encounter_time.replace('Z', '+00:00'))
                except:
                    enc_dt = datetime.now(timezone.utc)
            else:
                enc_dt = encounter_time
        else:
            enc_dt = datetime.now(timezone.utc)
        
        time_start = enc_dt - timedelta(hours=self.TIME_WINDOW_HOURS)
        time_end = enc_dt + timedelta(hours=self.TIME_WINDOW_HOURS)
        
        # Find all encounters in the time window
        nearby = []
        cursor = db.encounters.find(
            {
                "encounter_id": {"$ne": exclude_encounter_id},
                "user_id": {"$ne": exclude_user_id},  # Exclude same user
                "status": {"$in": ["active", "ended", "completed"]}
            },
            {"_id": 0, "encounter_id": 1, "location": 1, "latitude": 1, "longitude": 1, 
             "started_at": 1, "encounter_type": 1, "address": 1, "violations_detected": 1}
        ).limit(500)
        
        async for enc in cursor:
            enc_lat = enc.get("location", {}).get("latitude") or enc.get("latitude")
            enc_lon = enc.get("location", {}).get("longitude") or enc.get("longitude")
            
            if enc_lat and enc_lon:
                distance = self._haversine_distance(lat, lon, enc_lat, enc_lon)
                
                if distance <= self.NEARBY_RADIUS_MILES:
                    nearby.append({
                        "encounter_id": enc.get("encounter_id"),
                        "distance_miles": round(distance, 2),
                        "encounter_type": enc.get("encounter_type"),
                        "address": enc.get("address"),
                        "started_at": enc.get("started_at"),
                        "violations_detected": enc.get("violations_detected", []),
                        "relevance": "high" if distance < 0.5 else "medium"
                    })
        
        # Sort by distance
        nearby.sort(key=lambda x: x["distance_miles"])
        return nearby
    
    async def _find_officer_history(self, officers: List[Dict]) -> List[Dict]:
        """Find complaint/violation history for involved officers"""
        
        if not officers:
            return []
        
        officer_histories = []
        
        for officer in officers:
            badge_number = officer.get("badge_number")
            name = officer.get("name", "").lower()
            
            # Search accountability database
            query = {}
            if badge_number:
                query["badge_number"] = badge_number
            elif name:
                query["name"] = {"$regex": name, "$options": "i"}
            else:
                continue
            
            officer_record = await db.officers.find_one(query, {"_id": 0})
            
            if officer_record:
                # Get complaints
                complaints = await db.complaints.find(
                    {"officer_id": officer_record.get("officer_id")}
                ).to_list(100)
                
                officer_histories.append({
                    "officer_name": officer_record.get("name", officer.get("name")),
                    "badge_number": officer_record.get("badge_number", badge_number),
                    "department": officer_record.get("department"),
                    "accountability_score": officer_record.get("accountability_score", 100),
                    "complaint_count": len(complaints),
                    "violation_types": list(set(c.get("violation_type") for c in complaints if c.get("violation_type"))),
                    "disciplinary_actions": officer_record.get("disciplinary_history", []),
                    "risk_level": "high" if officer_record.get("accountability_score", 100) < 70 else 
                                  "medium" if officer_record.get("accountability_score", 100) < 85 else "low"
                })
            else:
                # Officer not in database - note as unknown
                officer_histories.append({
                    "officer_name": officer.get("name", "Unknown"),
                    "badge_number": badge_number,
                    "department": officer.get("department"),
                    "accountability_score": None,
                    "complaint_count": 0,
                    "violation_types": [],
                    "disciplinary_actions": [],
                    "risk_level": "unknown",
                    "note": "Officer not found in accountability database"
                })
        
        return officer_histories
    
    async def _find_area_incidents(
        self,
        lat: Optional[float],
        lon: Optional[float],
        encounter_time: Optional[str]
    ) -> List[Dict]:
        """Find reported incidents in the area from public data"""
        
        if not lat or not lon:
            return []
        
        # Search for incidents reported in the area
        incidents = []
        
        # Check complaints database for area
        cursor = db.complaints.find(
            {},
            {"_id": 0}
        ).limit(200)
        
        async for complaint in cursor:
            comp_loc = complaint.get("location", {})
            comp_lat = comp_loc.get("latitude")
            comp_lon = comp_loc.get("longitude")
            
            if comp_lat and comp_lon:
                distance = self._haversine_distance(lat, lon, comp_lat, comp_lon)
                
                if distance <= self.NEARBY_RADIUS_MILES * 2:  # Wider radius for historical
                    incidents.append({
                        "type": "complaint",
                        "violation_type": complaint.get("violation_type"),
                        "description": complaint.get("description", "")[:200],
                        "date": complaint.get("incident_date"),
                        "distance_miles": round(distance, 2),
                        "status": complaint.get("status")
                    })
        
        # Sort by distance
        incidents.sort(key=lambda x: x.get("distance_miles", 999))
        return incidents
    
    async def _find_similar_violations(self, encounter: Dict) -> List[Dict]:
        """Find encounters with similar violation patterns"""
        
        violations = encounter.get("violations_detected", [])
        if not violations:
            return []
        
        # Search for similar violations
        patterns = []
        
        for violation in violations[:3]:  # Check top 3 violations
            # Find other encounters with same violation
            similar = await db.encounters.find(
                {
                    "encounter_id": {"$ne": encounter.get("encounter_id")},
                    "violations_detected": {"$in": [violation]}
                },
                {"_id": 0, "encounter_id": 1, "violations_detected": 1, "started_at": 1}
            ).limit(10).to_list(10)
            
            if similar:
                patterns.append({
                    "violation_type": violation,
                    "similar_encounters": len(similar),
                    "pattern_strength": "strong" if len(similar) >= 5 else "moderate" if len(similar) >= 2 else "weak",
                    "dates": [s.get("started_at") for s in similar[:3]]
                })
        
        return patterns
    
    def _calculate_corroboration_score(
        self,
        nearby: List,
        officer_history: List,
        area_incidents: List,
        similar_violations: List
    ) -> int:
        """Calculate overall corroboration strength (0-100)"""
        
        score = 0
        
        # Nearby encounters (up to 30 points)
        if nearby:
            score += min(len(nearby) * 10, 30)
        
        # Officer history (up to 30 points)
        for officer in officer_history:
            if officer.get("complaint_count", 0) > 0:
                score += min(officer["complaint_count"] * 5, 15)
            if officer.get("accountability_score") and officer["accountability_score"] < 80:
                score += 10
        score = min(score, 60)  # Cap at 60 so far
        
        # Area incidents (up to 20 points)
        if area_incidents:
            score += min(len(area_incidents) * 4, 20)
        
        # Similar violations (up to 20 points)
        strong_patterns = sum(1 for p in similar_violations if p.get("pattern_strength") == "strong")
        score += min(strong_patterns * 10, 20)
        
        return min(score, 100)
    
    def _interpret_score(self, score: int) -> str:
        """Interpret the corroboration score"""
        if score >= 80:
            return "Very Strong - Multiple sources corroborate this encounter"
        elif score >= 60:
            return "Strong - Significant corroborating evidence found"
        elif score >= 40:
            return "Moderate - Some corroborating evidence exists"
        elif score >= 20:
            return "Limited - Minimal corroborating evidence"
        else:
            return "Weak - Little to no corroborating evidence found"
    
    def _assess_legal_value(
        self,
        score: int,
        nearby: List,
        officer_history: List
    ) -> Dict:
        """Assess the legal value of the corroboration"""
        
        value = {
            "overall": "low",
            "strengths": [],
            "weaknesses": [],
            "recommendations": []
        }
        
        # Assess strengths
        if nearby:
            value["strengths"].append(f"{len(nearby)} other encounters in same area could provide witness testimony")
        
        for officer in officer_history:
            if officer.get("complaint_count", 0) >= 3:
                value["strengths"].append(f"Officer {officer.get('officer_name', 'Unknown')} has {officer['complaint_count']} prior complaints - pattern of behavior")
            if officer.get("accountability_score") and officer["accountability_score"] < 70:
                value["strengths"].append(f"Officer has low accountability score ({officer['accountability_score']}) - credibility concern")
        
        # Determine overall value
        if score >= 60 and len(value["strengths"]) >= 2:
            value["overall"] = "high"
        elif score >= 40 or len(value["strengths"]) >= 1:
            value["overall"] = "medium"
        
        # Recommendations
        if nearby:
            value["recommendations"].append("Consider reaching out to other users who had encounters in the same area")
        if any(o.get("complaint_count", 0) > 0 for o in officer_history):
            value["recommendations"].append("File a formal complaint to add to officer's record")
        value["recommendations"].append("Preserve all evidence with blockchain verification")
        
        return value
    
    async def _generate_corroboration_analysis(
        self,
        encounter: Dict,
        nearby: List,
        officer_history: List,
        area_incidents: List,
        similar_violations: List
    ) -> Optional[str]:
        """Generate AI analysis of the corroboration evidence"""
        
        if not EMERGENT_LLM_KEY:
            return None
        
        try:
            context = f"""
            Encounter Type: {encounter.get('encounter_type')}
            Location: {encounter.get('address', 'Unknown')}
            Violations Detected: {encounter.get('violations_detected', [])}
            
            Corroborating Evidence Found:
            - {len(nearby)} other encounters within {self.NEARBY_RADIUS_MILES} miles
            - {len(officer_history)} officers checked, {sum(o.get('complaint_count', 0) for o in officer_history)} total prior complaints
            - {len(area_incidents)} historical incidents in the area
            - {len(similar_violations)} similar violation patterns found
            """
            
            prompt = f"""As a legal analyst, briefly analyze this corroboration evidence for a civil rights case:

{context}

Provide a 2-3 sentence assessment of:
1. The strength of corroborating evidence
2. Key patterns that support the user's account
3. Recommended next steps for building the case"""

            analysis = await generate_response(prompt, max_tokens=200)
            return analysis
        except Exception as e:
            print(f"AI analysis error: {e}")
            return None
    
    async def get_corroboration_history(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get user's corroboration search history"""
        
        results = await db.corroborations.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("generated_at", -1).limit(limit).to_list(limit)
        
        return results


# Singleton instance
witness_corroboration_service = WitnessCorroborationService()
