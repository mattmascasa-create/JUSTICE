"""
Officer Detection Service - AI-powered extraction of officer information from audio/transcripts
"""
import os
import re
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.db.database import db
from app.core.config import EMERGENT_LLM_KEY

logger = logging.getLogger(__name__)


class OfficerDetectionService:
    """
    Automatically detect and extract officer information from:
    - Audio recordings (via transcription)
    - Transcript text
    
    Extracts:
    - Badge numbers
    - Officer names
    - Department information
    - Unit/division numbers
    - Partner information
    """
    
    # Common patterns for badge number mentions
    BADGE_PATTERNS = [
        r"badge\s*(?:number|#|num)?\s*(?:is\s*)?(\d{3,7})",
        r"officer\s+(\d{4,6})",
        r"my\s+badge\s+(?:is\s+)?(\d{3,7})",
        r"badge\s+(\d{3,7})",
        r"#(\d{4,6})\b",
        r"number\s+(\d{4,6})\b",
    ]
    
    # Department name patterns
    DEPARTMENT_PATTERNS = [
        r"([\w\s]+)\s+police\s+department",
        r"([\w\s]+)\s+pd\b",
        r"([\w\s]+)\s+sheriff(?:'s)?\s+(?:department|office)",
        r"department\s+of\s+([\w\s]+)",
    ]
    
    # Officer name patterns (after "Officer" or "Deputy")
    NAME_PATTERNS = [
        r"(?:officer|deputy|sergeant|detective|corporal|lieutenant)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:i'm|i am|this is)\s+(?:officer|deputy)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"my\s+name\s+is\s+(?:officer\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    ]
    
    async def detect_from_transcript(self, transcript: str, encounter_id: Optional[str] = None) -> Dict:
        """
        Extract officer information from transcript text using pattern matching + AI.
        """
        detection_id = f"det_{uuid.uuid4().hex[:12]}"
        
        # Step 1: Pattern-based extraction (fast, no API cost)
        pattern_results = self._extract_with_patterns(transcript)
        
        # Step 2: AI-enhanced extraction (more accurate, handles natural speech)
        ai_results = await self._extract_with_ai(transcript)
        
        # Step 3: Merge and deduplicate results
        merged = self._merge_detections(pattern_results, ai_results)
        
        # Step 4: Cross-reference with accountability database
        enriched = await self._enrich_from_database(merged)
        
        result = {
            "detection_id": detection_id,
            "encounter_id": encounter_id,
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "officers": enriched,
            "officer_count": len(enriched),
            "confidence": self._calculate_overall_confidence(enriched),
            "raw_extractions": {
                "pattern_based": pattern_results,
                "ai_enhanced": ai_results
            }
        }
        
        # Store detection result
        if encounter_id:
            await db.officer_detections.insert_one({
                **result,
                "created_at": datetime.now(timezone.utc)
            })
            
            # Update encounter with detected officers
            await db.encounters.update_one(
                {"encounter_id": encounter_id},
                {"$set": {"detected_officers": enriched}}
            )
        
        return result
    
    def _extract_with_patterns(self, text: str) -> Dict:
        """Fast pattern-based extraction"""
        results = {
            "badge_numbers": [],
            "officer_names": [],
            "departments": [],
            "confidence": 0.0
        }
        
        text_lower = text.lower()
        
        # Extract badge numbers
        for pattern in self.BADGE_PATTERNS:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                badge = match.strip()
                if badge and badge not in results["badge_numbers"]:
                    results["badge_numbers"].append(badge)
        
        # Extract departments
        for pattern in self.DEPARTMENT_PATTERNS:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                dept = match.strip().title()
                if dept and len(dept) > 2 and dept not in results["departments"]:
                    results["departments"].append(dept)
        
        # Extract officer names (case sensitive)
        for pattern in self.NAME_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                name = match.strip()
                if name and len(name) > 2 and name not in results["officer_names"]:
                    results["officer_names"].append(name)
        
        # Calculate confidence based on what was found
        found_items = len(results["badge_numbers"]) + len(results["officer_names"]) + len(results["departments"])
        results["confidence"] = min(found_items * 0.25, 0.8)  # Cap at 80% for pattern-only
        
        return results
    
    async def _extract_with_ai(self, transcript: str) -> Dict:
        """AI-powered extraction for more nuanced detection"""
        if not EMERGENT_LLM_KEY or len(transcript) < 50:
            return {"badge_numbers": [], "officer_names": [], "departments": [], "confidence": 0.0}
        
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            llm = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"officer_detect_{uuid.uuid4().hex[:8]}",
                system_message="""You are an expert at analyzing police encounter transcripts to extract officer identification information. 
Extract any mentions of:
- Badge numbers (even if partially heard or informal)
- Officer names (including nicknames, last names only, or informal references)
- Department names
- Unit or division numbers
- Partner or backup officer mentions"""
            ).with_model("openai", "gpt-4o")
            
            prompt = f"""Analyze this police encounter transcript and extract ALL officer identification information:

TRANSCRIPT:
{transcript[:3000]}  # Limit to avoid token issues

Return ONLY valid JSON:
{{
    "officers": [
        {{
            "badge_number": "string or null",
            "name": "string or null",
            "rank": "string or null (Officer, Sergeant, Detective, etc.)",
            "department": "string or null",
            "unit": "string or null",
            "confidence": 0.0 to 1.0,
            "evidence_quote": "exact quote where this info was found"
        }}
    ],
    "department_mentions": ["list of department names mentioned"],
    "additional_officers_referenced": ["any other officers mentioned but not fully identified"],
    "overall_confidence": 0.0 to 1.0
}}"""
            
            response = await llm.send_message(UserMessage(text=prompt))
            
            if response:
                # Parse response
                content = str(response).strip()
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
                
                parsed = json.loads(content)
                
                # Convert to standard format
                return {
                    "badge_numbers": [o.get("badge_number") for o in parsed.get("officers", []) if o.get("badge_number")],
                    "officer_names": [o.get("name") for o in parsed.get("officers", []) if o.get("name")],
                    "departments": parsed.get("department_mentions", []),
                    "officers_detailed": parsed.get("officers", []),
                    "confidence": parsed.get("overall_confidence", 0.5)
                }
                
        except Exception as e:
            logger.error(f"AI officer detection error: {e}")
        
        return {"badge_numbers": [], "officer_names": [], "departments": [], "confidence": 0.0}
    
    def _merge_detections(self, pattern_results: Dict, ai_results: Dict) -> List[Dict]:
        """Merge pattern and AI results into unified officer list"""
        officers = []
        
        # Start with AI detailed results if available
        ai_officers = ai_results.get("officers_detailed", [])
        for officer in ai_officers:
            officers.append({
                "badge_number": officer.get("badge_number"),
                "name": officer.get("name"),
                "rank": officer.get("rank", "Officer"),
                "department": officer.get("department"),
                "unit": officer.get("unit"),
                "confidence": officer.get("confidence", 0.5),
                "source": "ai",
                "evidence_quote": officer.get("evidence_quote")
            })
        
        # Add pattern-detected badges not already found
        existing_badges = {o.get("badge_number") for o in officers if o.get("badge_number")}
        for badge in pattern_results.get("badge_numbers", []):
            if badge not in existing_badges:
                officers.append({
                    "badge_number": badge,
                    "name": None,
                    "rank": "Officer",
                    "department": pattern_results.get("departments", [None])[0] if pattern_results.get("departments") else None,
                    "unit": None,
                    "confidence": 0.6,
                    "source": "pattern"
                })
        
        # Add pattern-detected names not already found
        existing_names = {o.get("name") for o in officers if o.get("name")}
        for name in pattern_results.get("officer_names", []):
            if name not in existing_names:
                officers.append({
                    "badge_number": None,
                    "name": name,
                    "rank": "Officer",
                    "department": pattern_results.get("departments", [None])[0] if pattern_results.get("departments") else None,
                    "unit": None,
                    "confidence": 0.5,
                    "source": "pattern"
                })
        
        # If no officers found, create placeholder with just department
        if not officers and pattern_results.get("departments"):
            officers.append({
                "badge_number": None,
                "name": None,
                "rank": "Officer",
                "department": pattern_results["departments"][0],
                "unit": None,
                "confidence": 0.3,
                "source": "pattern"
            })
        
        return officers
    
    async def _enrich_from_database(self, officers: List[Dict]) -> List[Dict]:
        """Cross-reference detected officers with accountability database"""
        enriched = []
        
        for officer in officers:
            badge = officer.get("badge_number")
            
            if badge:
                # Search for officer in accountability database
                db_officer = await db.officers.find_one(
                    {"badge_number": badge},
                    {"_id": 0}
                )
                
                if db_officer:
                    # Found match - enrich with accountability data
                    enriched.append({
                        **officer,
                        "database_match": True,
                        "officer_id": db_officer.get("officer_id"),
                        "full_name": db_officer.get("full_name"),
                        "department_id": db_officer.get("department_id"),
                        "department_name": db_officer.get("department_name"),
                        "accountability_score": db_officer.get("accountability_score"),
                        "total_violations": db_officer.get("total_violations", 0),
                        "warning_level": self._get_warning_level(db_officer.get("accountability_score", 100)),
                        "confidence": min(officer.get("confidence", 0.5) + 0.3, 1.0)  # Boost confidence
                    })
                    continue
            
            # No database match - return original
            enriched.append({
                **officer,
                "database_match": False,
                "warning_level": {"level": "unknown", "message": "Officer not in accountability database"}
            })
        
        return enriched
    
    def _get_warning_level(self, score: float) -> Dict:
        """Get warning level based on accountability score"""
        if score >= 80:
            return {"level": "low", "color": "green", "message": "Officer has good accountability record"}
        elif score >= 60:
            return {"level": "medium", "color": "yellow", "message": "Exercise normal caution"}
        elif score >= 40:
            return {"level": "elevated", "color": "orange", "message": "Officer has documented issues - record interaction"}
        else:
            return {"level": "high", "color": "red", "message": "Multiple violations on record - strongly recommend recording"}
    
    def _calculate_overall_confidence(self, officers: List[Dict]) -> float:
        """Calculate overall detection confidence"""
        if not officers:
            return 0.0
        
        # Average confidence of all detected officers
        confidences = [o.get("confidence", 0.5) for o in officers]
        avg_confidence = sum(confidences) / len(confidences)
        
        # Bonus for database matches
        db_matches = sum(1 for o in officers if o.get("database_match"))
        match_bonus = (db_matches / len(officers)) * 0.2
        
        return min(avg_confidence + match_bonus, 1.0)
    
    async def detect_from_audio(self, audio_file_path: str, encounter_id: Optional[str] = None) -> Dict:
        """
        Detect officers from audio file by transcribing first.
        """
        from app.services.ai_service import transcribe_audio
        
        # Transcribe audio
        transcript = await transcribe_audio(audio_file_path)
        
        if not transcript:
            return {
                "detection_id": f"det_{uuid.uuid4().hex[:12]}",
                "encounter_id": encounter_id,
                "error": "Failed to transcribe audio",
                "officers": [],
                "officer_count": 0,
                "confidence": 0.0
            }
        
        # Detect from transcript
        result = await self.detect_from_transcript(transcript, encounter_id)
        result["transcript_length"] = len(transcript)
        
        return result


# Singleton instance
officer_detection = OfficerDetectionService()
