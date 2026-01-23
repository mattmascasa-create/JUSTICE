"""
Automatic Violation Detection Service - AI-powered constitutional rights violation analysis
"""
import os
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict
import uuid

from app.db.database import db

logger = logging.getLogger(__name__)

# Constitutional amendments reference
AMENDMENTS = {
    "1st": "Freedom of speech, religion, press, assembly, petition",
    "4th": "Protection against unreasonable searches and seizures",
    "5th": "Right against self-incrimination, due process",
    "6th": "Right to counsel, speedy trial, confrontation",
    "8th": "Protection against cruel and unusual punishment",
    "14th": "Equal protection, due process"
}

# Common violation patterns
VIOLATION_PATTERNS = [
    {
        "keywords": ["search", "look through", "check your", "open your"],
        "without": ["warrant", "consent", "probable cause"],
        "violation": "Potential 4th Amendment - Warrantless Search",
        "severity": 7
    },
    {
        "keywords": ["have to tell", "must answer", "required to say"],
        "violation": "Potential 5th Amendment - Compelled Self-Incrimination", 
        "severity": 6
    },
    {
        "keywords": ["grab", "push", "slam", "force", "choke", "taser", "beat"],
        "violation": "Potential 4th/8th Amendment - Excessive Force",
        "severity": 9
    },
    {
        "keywords": ["arrest", "detain", "custody"],
        "without": ["miranda", "rights"],
        "violation": "Potential 5th/6th Amendment - Miranda Violation",
        "severity": 6
    },
    {
        "keywords": ["racial", "because you're", "your kind", "people like you"],
        "violation": "Potential 14th Amendment - Racial Profiling",
        "severity": 8
    }
]


async def analyze_encounter_for_violations(
    encounter_id: str,
    transcript: str,
    encounter_type: str = "general"
) -> Dict:
    """
    Comprehensive AI analysis of encounter transcript for rights violations.
    """
    from emergentintegrations.llm.chat import chat, UserMessage, SystemMessage
    
    analysis_id = f"analysis_{uuid.uuid4().hex[:12]}"
    
    system_prompt = """You are a constitutional law expert and civil rights analyst. 
Analyze this police encounter transcript for potential constitutional rights violations.

For EACH violation found, provide detailed analysis including:
1. Exact quote from transcript
2. Timestamp/position marker
3. Which constitutional right was potentially violated
4. Severity score (1-10, where 10 is most severe)
5. Legal basis and explanation
6. Relevant case law precedent
7. Whether this would likely be admissible as evidence of misconduct

Also provide:
- Overall encounter assessment
- Pattern analysis (systemic issues vs isolated incidents)
- Recommendations for legal action
- Evidence strength rating for potential lawsuit

Respond in JSON format:
{
    "analysis_id": "...",
    "violations": [
        {
            "violation_id": "v1",
            "quote": "exact transcript quote",
            "timestamp_marker": "approximate position",
            "amendment_violated": "4th Amendment",
            "violation_type": "Warrantless Search",
            "severity": 8,
            "legal_basis": "Under Terry v. Ohio...",
            "case_law": ["Terry v. Ohio (1968)", "Mapp v. Ohio (1961)"],
            "admissible": true,
            "explanation": "Detailed explanation..."
        }
    ],
    "overall_assessment": {
        "violation_count": 3,
        "max_severity": 8,
        "pattern_detected": "escalation_of_force",
        "officer_conduct_rating": "concerning",
        "constitutional_compliance": "multiple_violations"
    },
    "recommendations": {
        "immediate_actions": ["File complaint", "Preserve evidence"],
        "legal_options": ["Civil rights lawsuit under 42 USC 1983", "Criminal complaint"],
        "evidence_strength": "strong",
        "estimated_case_viability": 75
    },
    "summary": "Brief summary of findings"
}"""

    user_prompt = f"""ENCOUNTER TYPE: {encounter_type}
ENCOUNTER ID: {encounter_id}

FULL TRANSCRIPT:
{transcript}

Analyze this encounter thoroughly for any constitutional rights violations."""

    try:
        response = await chat(
            api_key=os.environ.get("EMERGENT_API_KEY"),
            messages=[
                SystemMessage(content=system_prompt),
                UserMessage(content=user_prompt)
            ],
            model="gpt-5.2",
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        import json
        analysis = json.loads(response.content)
        analysis["analysis_id"] = analysis_id
        analysis["encounter_id"] = encounter_id
        analysis["analyzed_at"] = datetime.now(timezone.utc).isoformat()
        analysis["transcript_length"] = len(transcript)
        
        # Store the analysis
        await db.violation_analyses.insert_one({
            **analysis,
            "created_at": datetime.now(timezone.utc)
        })
        
        # If violations found, create violation records
        if analysis.get("violations"):
            for violation in analysis["violations"]:
                await db.detected_violations.insert_one({
                    "violation_id": f"viol_{uuid.uuid4().hex[:12]}",
                    "analysis_id": analysis_id,
                    "encounter_id": encounter_id,
                    **violation,
                    "created_at": datetime.now(timezone.utc)
                })
        
        return analysis
        
    except Exception as e:
        logger.error(f"Violation analysis error: {e}")
        return {
            "analysis_id": analysis_id,
            "error": str(e),
            "violations": [],
            "summary": "Analysis failed - please try again"
        }


async def get_quick_violation_flags(transcript: str) -> List[Dict]:
    """
    Quick pattern-matching for immediate violation flags (no AI latency).
    Used for real-time alerts while full analysis runs in background.
    """
    flags = []
    transcript_lower = transcript.lower()
    
    for pattern in VIOLATION_PATTERNS:
        # Check if keywords are present
        keyword_found = any(kw in transcript_lower for kw in pattern["keywords"])
        
        if keyword_found:
            # Check if exception words are NOT present
            if "without" in pattern:
                exception_found = any(exc in transcript_lower for exc in pattern["without"])
                if not exception_found:
                    flags.append({
                        "type": pattern["violation"],
                        "severity": pattern["severity"],
                        "immediate": True
                    })
            else:
                flags.append({
                    "type": pattern["violation"],
                    "severity": pattern["severity"],
                    "immediate": True
                })
    
    return flags


async def generate_violation_report(encounter_id: str) -> Dict:
    """Generate a formal violation report for an encounter"""
    
    # Get the analysis
    analysis = await db.violation_analyses.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0}
    )
    
    if not analysis:
        return {"error": "No analysis found for this encounter"}
    
    # Get encounter details
    encounter = await db.encounters.find_one(
        {"encounter_id": encounter_id},
        {"_id": 0}
    )
    
    # Get user details
    user = await db.users.find_one(
        {"user_id": encounter.get("user_id")},
        {"_id": 0, "name": 1, "email": 1}
    )
    
    report = {
        "report_id": f"report_{uuid.uuid4().hex[:12]}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "encounter_id": encounter_id,
        "encounter_date": encounter.get("started_at"),
        "complainant": {
            "name": user.get("name"),
            "email": user.get("email")
        },
        "location": encounter.get("location"),
        "officer_info": encounter.get("officer_info", {}),
        "violations": analysis.get("violations", []),
        "overall_assessment": analysis.get("overall_assessment", {}),
        "recommendations": analysis.get("recommendations", {}),
        "evidence_summary": {
            "has_video": bool(encounter.get("recording_url")),
            "has_audio": bool(encounter.get("audio_url")),
            "has_transcript": bool(encounter.get("transcript")),
            "witness_count": encounter.get("witness_count", 0)
        }
    }
    
    # Store the report
    await db.violation_reports.insert_one({
        **report,
        "created_at": datetime.now(timezone.utc)
    })
    
    return report


async def get_violation_statistics(user_id: Optional[str] = None) -> Dict:
    """Get violation statistics, optionally filtered by user"""
    
    query = {}
    if user_id:
        query["user_id"] = user_id
    
    total_analyses = await db.violation_analyses.count_documents(query)
    
    # Aggregate violation types
    pipeline = [
        {"$match": query} if query else {"$match": {}},
        {"$unwind": "$violations"},
        {"$group": {
            "_id": "$violations.amendment_violated",
            "count": {"$sum": 1},
            "avg_severity": {"$avg": "$violations.severity"}
        }},
        {"$sort": {"count": -1}}
    ]
    
    violation_types = await db.violation_analyses.aggregate(pipeline).to_list(20)
    
    return {
        "total_analyses": total_analyses,
        "violations_by_type": violation_types
    }
