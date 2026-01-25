"""
Court-Grade AI Analysis API - Enhanced legal analysis endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Dict, List
from pydantic import BaseModel
from datetime import datetime, timezone

from app.db.database import db
from app.services.court_grade_ai import court_grade_ai, CourtGradeAnalysis
from app.routers.auth import get_current_user

router = APIRouter(prefix="/court-grade", tags=["Court-Grade AI"])


class AnalyzeRequest(BaseModel):
    encounter_id: str
    transcript: str
    encounter_type: str = "general"
    use_existing_analysis: bool = True  # If true, enhance existing analysis


class EnhanceAnalysisRequest(BaseModel):
    analysis_id: str
    include_citations: bool = True
    include_guardrails: bool = True


@router.post("/analyze")
async def court_grade_analyze(
    request: AnalyzeRequest,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """
    Perform court-grade analysis on an encounter transcript.
    
    Features:
    - RAG-enhanced legal citations from verified knowledge base
    - Guardrail checks for accuracy and bias
    - Confidence scoring with detailed breakdown
    - Court admissibility assessment
    """
    # Check if there's an existing basic analysis to enhance
    existing = None
    if request.use_existing_analysis:
        existing = await db.violation_analyses.find_one(
            {"encounter_id": request.encounter_id},
            {"_id": 0}
        )
    
    try:
        result = await court_grade_ai.analyze_encounter_court_grade(
            encounter_id=request.encounter_id,
            transcript=request.transcript,
            encounter_type=request.encounter_type,
            existing_analysis=existing
        )
        
        # Convert dataclass to dict
        from dataclasses import asdict
        return {
            "success": True,
            "analysis": asdict(result),
            "message": "Court-grade analysis complete"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/analysis/{analysis_id}")
async def get_court_grade_analysis(
    analysis_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Get a specific court-grade analysis by ID"""
    analysis = await db.court_grade_analyses.find_one(
        {"analysis_id": analysis_id},
        {"_id": 0}
    )
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return {"success": True, "analysis": analysis}


@router.get("/encounter/{encounter_id}/analyses")
async def get_encounter_analyses(
    encounter_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Get all court-grade analyses for an encounter"""
    analyses = await db.court_grade_analyses.find(
        {"encounter_id": encounter_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(10)
    
    return {
        "success": True,
        "encounter_id": encounter_id,
        "analyses": analyses,
        "count": len(analyses)
    }


@router.get("/knowledge-base/violation/{violation_type}")
async def get_violation_definition(
    violation_type: str,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Get legal definition and elements of a violation type"""
    definition = court_grade_ai.get_violation_definition(violation_type)
    
    if not definition:
        # Try alternative formats
        alt_type = violation_type.replace("-", "_").lower()
        definition = court_grade_ai.get_violation_definition(alt_type)
    
    if not definition:
        raise HTTPException(status_code=404, detail=f"Unknown violation type: {violation_type}")
    
    return {
        "success": True,
        "violation_type": violation_type,
        "definition": definition
    }


@router.get("/knowledge-base/amendment/{amendment}")
async def get_amendment_info(
    amendment: str,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Get full information about a constitutional amendment"""
    info = court_grade_ai.get_amendment_info(amendment)
    
    if not info:
        raise HTTPException(status_code=404, detail=f"Unknown amendment: {amendment}")
    
    return {
        "success": True,
        "amendment": amendment,
        "info": info
    }


@router.get("/knowledge-base/amendments")
async def list_amendments(
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """List all amendments in the knowledge base"""
    amendments = list(court_grade_ai.knowledge_base["constitutional_amendments"].keys())
    
    return {
        "success": True,
        "amendments": amendments,
        "statutes": list(court_grade_ai.knowledge_base["statutes"].keys()),
        "violation_types": list(court_grade_ai.knowledge_base["violation_definitions"].keys())
    }


@router.get("/guardrails/check/{analysis_id}")
async def rerun_guardrails(
    analysis_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Re-run guardrail checks on an existing analysis"""
    analysis = await db.court_grade_analyses.find_one(
        {"analysis_id": analysis_id},
        {"_id": 0}
    )
    
    if not analysis:
        # Try violation analyses
        analysis = await db.violation_analyses.find_one(
            {"analysis_id": analysis_id},
            {"_id": 0}
        )
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    # Get the original transcript if available
    encounter = await db.encounters.find_one(
        {"encounter_id": analysis.get("encounter_id")},
        {"_id": 0, "transcript": 1}
    )
    transcript = encounter.get("transcript", "") if encounter else ""
    
    # Run guardrails
    from dataclasses import asdict
    guardrails = court_grade_ai._run_guardrails(analysis, transcript)
    
    return {
        "success": True,
        "analysis_id": analysis_id,
        "guardrail_checks": [asdict(g) for g in guardrails],
        "all_passed": all(g.passed or g.severity != "critical" for g in guardrails),
        "checked_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/confidence/explain")
async def explain_confidence_levels() -> Dict:
    """Explain the confidence level system"""
    return {
        "success": True,
        "confidence_levels": {
            "very_high": {
                "range": "90-100%",
                "meaning": "Analysis backed by multiple verified precedents with strong evidence",
                "court_ready": True,
                "expert_review_needed": False
            },
            "high": {
                "range": "75-89%",
                "meaning": "Clear legal basis with good evidence quality",
                "court_ready": True,
                "expert_review_needed": False
            },
            "moderate": {
                "range": "50-74%",
                "meaning": "Reasonable analysis with some ambiguity",
                "court_ready": "Conditional",
                "expert_review_needed": True
            },
            "low": {
                "range": "25-49%",
                "meaning": "Significant uncertainty, limited evidence",
                "court_ready": False,
                "expert_review_needed": True
            },
            "very_low": {
                "range": "0-24%",
                "meaning": "Insufficient evidence for reliable analysis",
                "court_ready": False,
                "expert_review_needed": True
            }
        },
        "breakdown_factors": {
            "evidence_quality": "Percentage of violations with direct transcript quotes",
            "legal_backing": "Whether violations cite specific constitutional/statutory basis",
            "guardrail_score": "Percentage of validation checks passed",
            "citation_strength": "Number and relevance of verified legal precedents"
        }
    }


@router.post("/batch-analyze")
async def batch_court_grade_analyze(
    encounter_ids: List[str],
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """
    Queue multiple encounters for court-grade analysis.
    Returns job ID for status checking.
    """
    if len(encounter_ids) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 encounters per batch")
    
    job_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    
    # Queue the batch job
    await db.analysis_jobs.insert_one({
        "job_id": job_id,
        "encounter_ids": encounter_ids,
        "status": "queued",
        "created_by": current_user.get("user_id"),
        "created_at": datetime.now(timezone.utc),
        "completed_analyses": [],
        "failed_analyses": []
    })
    
    return {
        "success": True,
        "job_id": job_id,
        "encounter_count": len(encounter_ids),
        "message": "Batch analysis queued. Check status with /court-grade/batch/{job_id}"
    }


@router.get("/batch/{job_id}")
async def get_batch_status(
    job_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict:
    """Get status of a batch analysis job"""
    job = await db.analysis_jobs.find_one(
        {"job_id": job_id},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {"success": True, "job": job}
