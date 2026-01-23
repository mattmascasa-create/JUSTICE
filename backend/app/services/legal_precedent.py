"""
Legal Precedent Matching Service - Find similar cases and predict outcomes
"""
import os
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict
import uuid

from app.db.database import db

logger = logging.getLogger(__name__)

# Sample case law database (in production, this would connect to a legal database API)
LANDMARK_CASES = [
    {
        "case_name": "Terry v. Ohio",
        "year": 1968,
        "citation": "392 U.S. 1",
        "issue": "Stop and frisk, reasonable suspicion",
        "amendment": "4th",
        "holding": "Police may stop and frisk if they have reasonable suspicion",
        "keywords": ["stop", "frisk", "pat down", "reasonable suspicion", "weapons"]
    },
    {
        "case_name": "Miranda v. Arizona",
        "year": 1966,
        "citation": "384 U.S. 436",
        "issue": "Right to remain silent, right to attorney",
        "amendment": "5th/6th",
        "holding": "Suspects must be informed of their rights before custodial interrogation",
        "keywords": ["arrest", "custody", "interrogation", "rights", "lawyer", "silent"]
    },
    {
        "case_name": "Mapp v. Ohio",
        "year": 1961,
        "citation": "367 U.S. 643",
        "issue": "Exclusionary rule",
        "amendment": "4th",
        "holding": "Evidence obtained through illegal search is inadmissible",
        "keywords": ["search", "warrant", "evidence", "exclusion", "illegal"]
    },
    {
        "case_name": "Graham v. Connor",
        "year": 1989,
        "citation": "490 U.S. 386",
        "issue": "Excessive force standard",
        "amendment": "4th",
        "holding": "Force claims judged by objective reasonableness standard",
        "keywords": ["force", "excessive", "reasonable", "seizure", "injury"]
    },
    {
        "case_name": "Tennessee v. Garner",
        "year": 1985,
        "citation": "471 U.S. 1",
        "issue": "Deadly force",
        "amendment": "4th",
        "holding": "Deadly force only justified when suspect poses immediate threat",
        "keywords": ["deadly", "shoot", "fleeing", "threat", "escape"]
    },
    {
        "case_name": "Whren v. United States",
        "year": 1996,
        "citation": "517 U.S. 806",
        "issue": "Pretextual stops",
        "amendment": "4th",
        "holding": "Traffic stops valid if officer has probable cause regardless of motive",
        "keywords": ["traffic", "stop", "pretext", "racial", "profiling"]
    },
    {
        "case_name": "Rodriguez v. United States",
        "year": 2015,
        "citation": "575 U.S. 348",
        "issue": "Traffic stop duration",
        "amendment": "4th",
        "holding": "Police cannot extend traffic stops beyond time needed for original purpose",
        "keywords": ["traffic", "detain", "delay", "dog", "sniff", "extend"]
    },
    {
        "case_name": "Monell v. Department of Social Services",
        "year": 1978,
        "citation": "436 U.S. 658",
        "issue": "Municipal liability",
        "amendment": "14th",
        "holding": "Cities can be sued for constitutional violations under official policy",
        "keywords": ["city", "department", "policy", "custom", "training", "pattern"]
    }
]


async def find_matching_precedents(
    encounter_id: str,
    violations: List[Dict],
    transcript: str,
    encounter_type: str = "general"
) -> Dict:
    """
    Find legal precedents matching the encounter and violations.
    Uses AI to analyze and match relevant case law.
    """
    from emergentintegrations.llm.chat import chat, UserMessage, SystemMessage
    
    search_id = f"search_{uuid.uuid4().hex[:12]}"
    
    # Build case law context
    case_law_context = "\n".join([
        f"- {c['case_name']} ({c['year']}): {c['holding']}"
        for c in LANDMARK_CASES
    ])
    
    violations_text = "\n".join([
        f"- {v.get('violation_type', v.get('type', 'Unknown'))}: Severity {v.get('severity', 'N/A')}"
        for v in violations
    ]) if violations else "No violations detected"
    
    system_prompt = """You are an expert civil rights attorney analyzing a police encounter case.
Based on the encounter details and violations, identify:
1. Most relevant legal precedents
2. Similar successful cases
3. Potential legal strategies
4. Predicted outcome probability

Reference these key cases when relevant:
""" + case_law_context + """

Respond in JSON format:
{
    "matching_precedents": [
        {
            "case_name": "Terry v. Ohio",
            "citation": "392 U.S. 1",
            "year": 1968,
            "relevance_score": 95,
            "applicable_to": "stop and frisk without reasonable suspicion",
            "how_it_helps": "Establishes that officer needed reasonable suspicion",
            "key_quote": "Relevant quote from the case"
        }
    ],
    "similar_successful_cases": [
        {
            "description": "Description of similar case that was won",
            "outcome": "Settlement/Verdict amount if known",
            "similarity_score": 85
        }
    ],
    "legal_strategies": [
        {
            "strategy": "42 USC 1983 Civil Rights Claim",
            "description": "Sue for violation of constitutional rights",
            "strength": "strong",
            "considerations": ["Need to prove policy or custom", "Qualified immunity defense"]
        }
    ],
    "outcome_prediction": {
        "probability_of_success": 70,
        "likely_range_if_successful": "$10,000 - $50,000",
        "factors_helping": ["Clear video evidence", "Documented violation"],
        "factors_hurting": ["Qualified immunity", "No physical injury"],
        "recommended_approach": "settlement" or "litigation"
    },
    "summary": "Brief case assessment"
}"""

    user_prompt = f"""ENCOUNTER TYPE: {encounter_type}
DETECTED VIOLATIONS:
{violations_text}

TRANSCRIPT EXCERPT:
{transcript[:3000]}

Analyze this encounter and match relevant legal precedents."""

    try:
        response = await chat(
            api_key=os.environ.get("EMERGENT_API_KEY"),
            messages=[
                SystemMessage(content=system_prompt),
                UserMessage(content=user_prompt)
            ],
            model="gpt-5.2",
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        import json
        result = json.loads(response.content)
        result["search_id"] = search_id
        result["encounter_id"] = encounter_id
        result["searched_at"] = datetime.now(timezone.utc).isoformat()
        
        # Store the search result
        await db.precedent_searches.insert_one({
            **result,
            "created_at": datetime.now(timezone.utc)
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Precedent search error: {e}")
        return {
            "search_id": search_id,
            "error": str(e),
            "matching_precedents": [],
            "summary": "Search failed - please try again"
        }


async def get_case_law_by_amendment(amendment: str) -> List[Dict]:
    """Get relevant case law for a specific amendment"""
    
    matching_cases = [
        case for case in LANDMARK_CASES
        if amendment in case["amendment"]
    ]
    
    return matching_cases


async def search_case_law(keywords: List[str]) -> List[Dict]:
    """Search case law by keywords"""
    
    results = []
    keywords_lower = [k.lower() for k in keywords]
    
    for case in LANDMARK_CASES:
        case_keywords = [k.lower() for k in case["keywords"]]
        matches = sum(1 for kw in keywords_lower if any(kw in ck for ck in case_keywords))
        
        if matches > 0:
            results.append({
                **case,
                "relevance_score": matches * 20  # Simple scoring
            })
    
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results


async def estimate_case_value(
    violations: List[Dict],
    has_injury: bool = False,
    has_arrest: bool = False,
    has_video: bool = True
) -> Dict:
    """Estimate potential case value based on violations and circumstances"""
    
    base_value = 0
    multipliers = 1.0
    
    # Calculate base value from violations
    for violation in violations:
        severity = violation.get("severity", 5)
        if severity >= 8:
            base_value += 25000
        elif severity >= 6:
            base_value += 10000
        elif severity >= 4:
            base_value += 5000
        else:
            base_value += 2000
    
    # Apply multipliers
    if has_injury:
        multipliers *= 2.5
    if has_arrest:
        multipliers *= 1.5
    if has_video:
        multipliers *= 1.3
    
    estimated_value = base_value * multipliers
    
    return {
        "low_estimate": int(estimated_value * 0.5),
        "mid_estimate": int(estimated_value),
        "high_estimate": int(estimated_value * 2),
        "factors": {
            "violation_count": len(violations),
            "has_injury": has_injury,
            "has_arrest": has_arrest,
            "has_video": has_video
        },
        "disclaimer": "This is a rough estimate only. Actual case values vary significantly based on jurisdiction, specific facts, and many other factors. Consult an attorney for accurate assessment."
    }
