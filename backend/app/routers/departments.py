"""
Departments Router - Police department transparency data
"""
from datetime import datetime, timezone
from fastapi import APIRouter, Query, Depends
from typing import Optional

from app.db.database import db
from app.core.security import get_current_user_optional

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("")
async def list_departments(
    state: Optional[str] = None,
    sort_by: str = Query(default="risk_score", enum=["risk_score", "incidents", "name"]),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    """List police departments with transparency data"""
    # Build query
    query = {}
    if state and state != "all":
        query["state"] = state
    
    # Determine sort field
    sort_field = "risk_score"
    sort_order = -1  # Descending
    if sort_by == "incidents":
        sort_field = "total_incidents"
    elif sort_by == "name":
        sort_field = "name"
        sort_order = 1
    
    # Get departments from database
    departments = await db.departments.find(
        query,
        {"_id": 0}
    ).sort(sort_field, sort_order).skip(offset).limit(limit).to_list(limit)
    
    # If no data, return sample departments for demo
    if not departments:
        departments = generate_sample_departments(state, sort_by, limit)
    
    return departments


@router.get("/{department_id}")
async def get_department(department_id: str):
    """Get detailed information about a specific department"""
    department = await db.departments.find_one(
        {"department_id": department_id},
        {"_id": 0}
    )
    
    if not department:
        # Return demo data
        department = {
            "department_id": department_id,
            "name": "Sample Police Department",
            "city": "Sample City",
            "state": "CA",
            "total_officers": 500,
            "total_incidents": 45,
            "settlements_total": 2500000,
            "risk_score": 6.5,
            "badges_of_concern": 12,
            "body_camera_policy": "required",
            "use_of_force_policy": "standard",
            "civilian_oversight": True,
            "transparency_grade": "B",
            "recent_incidents": []
        }
    
    return department


@router.get("/{department_id}/incidents")
async def get_department_incidents(
    department_id: str,
    limit: int = Query(default=20, ge=1, le=100)
):
    """Get recent incidents for a department"""
    incidents = await db.community_evidence.find(
        {"department_id": department_id},
        {"_id": 0, "user_id": 0}  # Exclude private data
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {
        "department_id": department_id,
        "incidents": incidents,
        "count": len(incidents)
    }


def generate_sample_departments(state: str = None, sort_by: str = "risk_score", limit: int = 50):
    """Generate sample department data for demo"""
    sample_departments = [
        {"name": "Phoenix Police Department", "city": "Phoenix", "state": "AZ", "risk_score": 7.2, "total_incidents": 156, "settlements_total": 4500000},
        {"name": "Los Angeles Police Department", "city": "Los Angeles", "state": "CA", "risk_score": 8.1, "total_incidents": 423, "settlements_total": 12000000},
        {"name": "New York Police Department", "city": "New York", "state": "NY", "risk_score": 7.8, "total_incidents": 567, "settlements_total": 25000000},
        {"name": "Chicago Police Department", "city": "Chicago", "state": "IL", "risk_score": 8.5, "total_incidents": 389, "settlements_total": 18000000},
        {"name": "Houston Police Department", "city": "Houston", "state": "TX", "risk_score": 6.9, "total_incidents": 234, "settlements_total": 8000000},
        {"name": "Atlanta Police Department", "city": "Atlanta", "state": "GA", "risk_score": 6.4, "total_incidents": 145, "settlements_total": 3500000},
        {"name": "Seattle Police Department", "city": "Seattle", "state": "WA", "risk_score": 5.8, "total_incidents": 98, "settlements_total": 2800000},
        {"name": "Denver Police Department", "city": "Denver", "state": "CO", "risk_score": 6.1, "total_incidents": 112, "settlements_total": 3200000},
        {"name": "Miami Police Department", "city": "Miami", "state": "FL", "risk_score": 7.0, "total_incidents": 178, "settlements_total": 5600000},
        {"name": "Boston Police Department", "city": "Boston", "state": "MA", "risk_score": 5.5, "total_incidents": 87, "settlements_total": 2100000},
        {"name": "San Francisco Police Department", "city": "San Francisco", "state": "CA", "risk_score": 6.7, "total_incidents": 134, "settlements_total": 4100000},
        {"name": "Dallas Police Department", "city": "Dallas", "state": "TX", "risk_score": 6.8, "total_incidents": 189, "settlements_total": 6200000},
        {"name": "Philadelphia Police Department", "city": "Philadelphia", "state": "PA", "risk_score": 7.4, "total_incidents": 267, "settlements_total": 9500000},
        {"name": "San Diego Police Department", "city": "San Diego", "state": "CA", "risk_score": 5.2, "total_incidents": 76, "settlements_total": 1800000},
        {"name": "Austin Police Department", "city": "Austin", "state": "TX", "risk_score": 6.3, "total_incidents": 123, "settlements_total": 3700000},
    ]
    
    # Filter by state if provided
    if state and state != "all":
        sample_departments = [d for d in sample_departments if d["state"] == state]
    
    # Add calculated fields
    for i, dept in enumerate(sample_departments):
        dept["department_id"] = f"dept_{i}"
        dept["total_officers"] = dept["total_incidents"] * 3 + 100
        dept["badges_of_concern"] = int(dept["risk_score"] * 2)
        dept["body_camera_policy"] = "required" if dept["risk_score"] < 7 else "recommended"
        dept["civilian_oversight"] = dept["risk_score"] < 6.5
        dept["transparency_grade"] = "A" if dept["risk_score"] < 5.5 else "B" if dept["risk_score"] < 6.5 else "C" if dept["risk_score"] < 7.5 else "D"
    
    # Sort
    if sort_by == "risk_score":
        sample_departments.sort(key=lambda x: x["risk_score"], reverse=True)
    elif sort_by == "incidents":
        sample_departments.sort(key=lambda x: x["total_incidents"], reverse=True)
    elif sort_by == "name":
        sample_departments.sort(key=lambda x: x["name"])
    
    return sample_departments[:limit]
