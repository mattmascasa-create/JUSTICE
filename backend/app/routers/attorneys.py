"""
Attorneys Router - Attorney directory and profiles
"""
import uuid
from typing import List, Optional
from fastapi import APIRouter, HTTPException

from app.db.database import db
from app.models.schemas import AttorneyProfile

router = APIRouter(prefix="/attorneys", tags=["Attorneys"])


async def seed_sample_attorneys():
    """Seed sample attorney data for the directory"""
    sample_attorneys = [
        {
            "attorney_id": f"atty_{uuid.uuid4().hex[:12]}",
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "name": "Sarah Mitchell, Esq.",
            "email": "sarah.mitchell@civilrights.law",
            "bar_number": "CA123456",
            "state": "California",
            "specializations": ["Civil Rights", "Police Misconduct", "4th Amendment"],
            "rating": 4.9,
            "success_rate": 87.5,
            "cases_won": 156,
            "total_cases": 178,
            "years_experience": 15,
            "hourly_rate": 350.0,
            "bio": "Former ACLU staff attorney with 15 years of experience in civil rights litigation.",
            "verified": True,
            "available_for_emergency": True,
            "picture": "https://images.pexels.com/photos/4427497/pexels-photo-4427497.jpeg"
        },
        {
            "attorney_id": f"atty_{uuid.uuid4().hex[:12]}",
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "name": "Marcus Johnson, Esq.",
            "email": "mjohnson@constitutionaldefense.org",
            "bar_number": "NY789012",
            "state": "New York",
            "specializations": ["Constitutional Law", "1st Amendment", "Excessive Force"],
            "rating": 4.8,
            "success_rate": 82.3,
            "cases_won": 203,
            "total_cases": 247,
            "years_experience": 20,
            "hourly_rate": 400.0,
            "bio": "Constitutional law expert and former federal public defender.",
            "verified": True,
            "available_for_emergency": True,
            "picture": "https://images.pexels.com/photos/5668858/pexels-photo-5668858.jpeg"
        },
        {
            "attorney_id": f"atty_{uuid.uuid4().hex[:12]}",
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "name": "Elena Rodriguez, Esq.",
            "email": "erodriguez@immigrationrights.org",
            "bar_number": "TX345678",
            "state": "Texas",
            "specializations": ["Immigration Rights", "Civil Rights", "14th Amendment"],
            "rating": 4.7,
            "success_rate": 79.8,
            "cases_won": 89,
            "total_cases": 112,
            "years_experience": 12,
            "hourly_rate": 275.0,
            "bio": "Bilingual civil rights attorney specializing in immigration-related cases.",
            "verified": True,
            "available_for_emergency": True,
            "picture": "https://images.pexels.com/photos/5668772/pexels-photo-5668772.jpeg"
        }
    ]
    
    for attorney in sample_attorneys:
        existing = await db.attorneys.find_one({"email": attorney["email"]})
        if not existing:
            await db.attorneys.insert_one(attorney)


@router.get("", response_model=List[AttorneyProfile])
async def get_attorneys(
    state: Optional[str] = None,
    specialization: Optional[str] = None,
    available_emergency: Optional[bool] = None,
    min_rating: Optional[float] = None
):
    """Get attorneys from directory with filters"""
    query = {"verified": True}
    
    if state:
        query["state"] = state
    if specialization:
        query["specializations"] = {"$in": [specialization]}
    if available_emergency:
        query["available_for_emergency"] = True
    if min_rating:
        query["rating"] = {"$gte": min_rating}
    
    attorneys = await db.attorneys.find(query, {"_id": 0}).sort("rating", -1).to_list(100)
    
    # Seed sample data if empty
    if not attorneys:
        await seed_sample_attorneys()
        attorneys = await db.attorneys.find(query, {"_id": 0}).sort("rating", -1).to_list(100)
    
    return [AttorneyProfile(**a) for a in attorneys]


@router.get("/{attorney_id}", response_model=AttorneyProfile)
async def get_attorney(attorney_id: str):
    """Get specific attorney by ID"""
    attorney = await db.attorneys.find_one({"attorney_id": attorney_id}, {"_id": 0})
    
    if not attorney:
        raise HTTPException(status_code=404, detail="Attorney not found")
    
    return AttorneyProfile(**attorney)


@router.get("/specializations/list")
async def get_specializations():
    """Get list of available specializations"""
    return {
        "specializations": [
            "Civil Rights",
            "Police Misconduct",
            "Constitutional Law",
            "4th Amendment",
            "5th Amendment",
            "1st Amendment",
            "14th Amendment",
            "Excessive Force",
            "Wrongful Arrest",
            "Immigration Rights",
            "Disability Rights",
            "Employment Discrimination"
        ]
    }


@router.get("/states/list")
async def get_states():
    """Get list of states with attorneys"""
    states = await db.attorneys.distinct("state")
    return {"states": states if states else ["California", "New York", "Texas", "Florida", "Illinois"]}
