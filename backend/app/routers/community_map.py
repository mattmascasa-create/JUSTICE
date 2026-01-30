"""
Community Incident Mapping Router
Public-facing API for incident visualization and community awareness
"""
from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from app.db.database import db
from app.routers.auth import get_current_user

router = APIRouter(prefix="/community-map", tags=["Community Incident Map"])


@router.get("/incidents")
async def get_public_incidents(
    lat: Optional[float] = Query(None, description="Center latitude"),
    lon: Optional[float] = Query(None, description="Center longitude"),
    radius_miles: float = Query(default=10, le=50, description="Search radius in miles"),
    days: int = Query(default=90, le=365, description="Days of history"),
    incident_types: Optional[str] = Query(None, description="Comma-separated incident types"),
    limit: int = Query(default=500, le=1000)
):
    """
    Get anonymized public incident data for map display.
    No authentication required - all data is anonymized.
    """
    
    # Build query
    query = {}
    
    # Time filter
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get encounters with location data (anonymized)
    incidents = []
    
    # Fetch from encounters collection
    cursor = db.encounters.find(
        {"status": {"$in": ["ended", "completed"]}},
        {
            "_id": 0,
            "encounter_id": 1,
            "encounter_type": 1,
            "latitude": 1,
            "longitude": 1,
            "location": 1,
            "started_at": 1,
            "violations_detected": 1,
            "address": 1
        }
    ).limit(limit)
    
    async for enc in cursor:
        # Get coordinates
        enc_lat = enc.get("location", {}).get("latitude") or enc.get("latitude")
        enc_lon = enc.get("location", {}).get("longitude") or enc.get("longitude")
        
        if not enc_lat or not enc_lon:
            continue
        
        # Slightly randomize location for privacy (within ~100m)
        import random
        enc_lat += random.uniform(-0.001, 0.001)
        enc_lon += random.uniform(-0.001, 0.001)
        
        # Filter by radius if center provided
        if lat and lon:
            from math import radians, sin, cos, sqrt, atan2
            R = 3959  # Earth radius in miles
            
            lat1, lon1 = radians(lat), radians(lon)
            lat2, lon2 = radians(enc_lat), radians(enc_lon)
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance = R * c
            
            if distance > radius_miles:
                continue
        
        # Filter by incident type
        if incident_types:
            types_list = [t.strip() for t in incident_types.split(",")]
            if enc.get("encounter_type") not in types_list:
                continue
        
        incidents.append({
            "id": enc.get("encounter_id"),
            "type": enc.get("encounter_type", "unknown"),
            "lat": round(enc_lat, 4),
            "lon": round(enc_lon, 4),
            "date": enc.get("started_at"),
            "violations": enc.get("violations_detected", []),
            "has_violations": len(enc.get("violations_detected", [])) > 0,
            "area": _get_area_name(enc.get("address"))
        })
    
    # Also add complaints from accountability portal
    complaints_cursor = db.complaints.find(
        {"status": {"$ne": "dismissed"}},
        {
            "_id": 0,
            "complaint_id": 1,
            "violation_type": 1,
            "location": 1,
            "incident_date": 1,
            "status": 1
        }
    ).limit(limit // 2)
    
    async for complaint in complaints_cursor:
        comp_loc = complaint.get("location", {})
        comp_lat = comp_loc.get("latitude")
        comp_lon = comp_loc.get("longitude")
        
        if not comp_lat or not comp_lon:
            continue
        
        # Randomize for privacy
        import random
        comp_lat += random.uniform(-0.001, 0.001)
        comp_lon += random.uniform(-0.001, 0.001)
        
        incidents.append({
            "id": complaint.get("complaint_id"),
            "type": "complaint",
            "lat": round(comp_lat, 4),
            "lon": round(comp_lon, 4),
            "date": complaint.get("incident_date"),
            "violations": [complaint.get("violation_type")] if complaint.get("violation_type") else [],
            "has_violations": True,
            "area": None,
            "complaint_status": complaint.get("status")
        })
    
    return {
        "success": True,
        "incidents": incidents,
        "count": len(incidents),
        "filters": {
            "radius_miles": radius_miles,
            "days": days,
            "incident_types": incident_types
        }
    }


@router.get("/hotspots")
async def get_incident_hotspots(
    days: int = Query(default=90, le=365)
):
    """
    Get aggregated hotspot data showing areas with high incident concentration.
    """
    
    # Aggregate incidents by approximate location (grid cells)
    hotspots = {}
    
    cursor = db.encounters.find(
        {"status": {"$in": ["ended", "completed"]}},
        {"_id": 0, "latitude": 1, "longitude": 1, "location": 1, "violations_detected": 1}
    ).limit(1000)
    
    async for enc in cursor:
        lat = enc.get("location", {}).get("latitude") or enc.get("latitude")
        lon = enc.get("location", {}).get("longitude") or enc.get("longitude")
        
        if not lat or not lon:
            continue
        
        # Create grid cell (approx 1km x 1km)
        grid_lat = round(lat, 2)
        grid_lon = round(lon, 2)
        key = f"{grid_lat},{grid_lon}"
        
        if key not in hotspots:
            hotspots[key] = {
                "lat": grid_lat,
                "lon": grid_lon,
                "incident_count": 0,
                "violation_count": 0,
                "types": {}
            }
        
        hotspots[key]["incident_count"] += 1
        hotspots[key]["violation_count"] += len(enc.get("violations_detected", []))
    
    # Convert to list and sort by incident count
    hotspot_list = sorted(
        hotspots.values(),
        key=lambda x: x["incident_count"],
        reverse=True
    )[:50]  # Top 50 hotspots
    
    # Calculate intensity (0-1 scale)
    max_count = max((h["incident_count"] for h in hotspot_list), default=1)
    for h in hotspot_list:
        h["intensity"] = round(h["incident_count"] / max_count, 2)
    
    return {
        "success": True,
        "hotspots": hotspot_list,
        "count": len(hotspot_list)
    }


@router.get("/statistics")
async def get_map_statistics():
    """
    Get overall statistics for the community map.
    """
    
    # Count incidents
    total_encounters = await db.encounters.count_documents(
        {"status": {"$in": ["ended", "completed"]}}
    )
    
    total_complaints = await db.complaints.count_documents({})
    
    # Get violation breakdown
    pipeline = [
        {"$match": {"violations_detected": {"$exists": True, "$ne": []}}},
        {"$unwind": "$violations_detected"},
        {"$group": {"_id": "$violations_detected", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    violation_breakdown = []
    async for doc in db.encounters.aggregate(pipeline):
        violation_breakdown.append({
            "violation": doc["_id"],
            "count": doc["count"]
        })
    
    # Get encounter type breakdown
    type_pipeline = [
        {"$match": {"status": {"$in": ["ended", "completed"]}}},
        {"$group": {"_id": "$encounter_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    
    type_breakdown = []
    async for doc in db.encounters.aggregate(type_pipeline):
        type_breakdown.append({
            "type": doc["_id"],
            "count": doc["count"]
        })
    
    return {
        "success": True,
        "statistics": {
            "total_incidents": total_encounters + total_complaints,
            "total_encounters": total_encounters,
            "total_complaints": total_complaints,
            "violation_breakdown": violation_breakdown,
            "encounter_types": type_breakdown
        }
    }


@router.get("/officer-locations")
async def get_officer_incident_locations(
    officer_id: Optional[str] = Query(None),
    badge_number: Optional[str] = Query(None),
    days: int = Query(default=365, le=730)
):
    """
    Get locations of incidents involving a specific officer.
    Helps identify patterns of behavior in specific areas.
    """
    
    if not officer_id and not badge_number:
        return {"error": "Provide officer_id or badge_number", "locations": []}
    
    # Find the officer
    query = {}
    if officer_id:
        query["officer_id"] = officer_id
    elif badge_number:
        query["badge_number"] = badge_number
    
    officer = await db.officers.find_one(query, {"_id": 0})
    
    if not officer:
        return {"error": "Officer not found", "locations": []}
    
    # Find encounters with this officer
    locations = []
    
    cursor = db.encounters.find(
        {"officers.badge_number": officer.get("badge_number")},
        {"_id": 0, "encounter_id": 1, "latitude": 1, "longitude": 1, 
         "location": 1, "started_at": 1, "violations_detected": 1}
    ).limit(100)
    
    async for enc in cursor:
        lat = enc.get("location", {}).get("latitude") or enc.get("latitude")
        lon = enc.get("location", {}).get("longitude") or enc.get("longitude")
        
        if lat and lon:
            locations.append({
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "date": enc.get("started_at"),
                "violations": enc.get("violations_detected", [])
            })
    
    return {
        "success": True,
        "officer": {
            "name": officer.get("name"),
            "badge_number": officer.get("badge_number"),
            "department": officer.get("department"),
            "accountability_score": officer.get("accountability_score")
        },
        "locations": locations,
        "count": len(locations)
    }


# ============== Community Reporting ==============

@router.post("/report")
async def submit_community_report(
    report_type: str = Query(..., description="Type: safety_tip, incident, concern, positive"),
    description: str = Query(..., min_length=10, max_length=1000),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    address: Optional[str] = Query(None, max_length=200),
    anonymous: bool = Query(default=True),
    contact_email: Optional[str] = Query(None)
):
    """
    Submit a community report or safety tip.
    Can be anonymous or with contact info for follow-up.
    """
    import uuid
    import random
    
    report_id = f"report_{uuid.uuid4().hex[:12]}"
    
    # Slightly randomize location for privacy if provided
    if latitude and longitude:
        latitude += random.uniform(-0.002, 0.002)
        longitude += random.uniform(-0.002, 0.002)
    
    report = {
        "report_id": report_id,
        "report_type": report_type,
        "description": description,
        "location": {
            "latitude": round(latitude, 4) if latitude else None,
            "longitude": round(longitude, 4) if longitude else None,
            "address": address
        },
        "anonymous": anonymous,
        "contact_email": contact_email if not anonymous else None,
        "status": "pending",  # pending, approved, rejected
        "created_at": datetime.now(timezone.utc).isoformat(),
        "votes": 0,
        "verified": False
    }
    
    await db.community_reports.insert_one(report)
    
    return {
        "success": True,
        "report_id": report_id,
        "message": "Thank you for your report. It will be reviewed and added to the map if approved.",
        "status": "pending"
    }


@router.get("/reports")
async def get_community_reports(
    status: str = Query(default="approved", description="Filter by status"),
    report_type: Optional[str] = Query(None),
    days: int = Query(default=90, le=365),
    limit: int = Query(default=100, le=500)
):
    """
    Get approved community reports for map display.
    """
    
    query = {"status": status}
    
    if report_type:
        query["report_type"] = report_type
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    reports = []
    cursor = db.community_reports.find(
        query,
        {"_id": 0, "contact_email": 0}  # Exclude sensitive data
    ).sort("created_at", -1).limit(limit)
    
    async for report in cursor:
        # Only include reports with location
        if report.get("location", {}).get("latitude"):
            reports.append({
                "report_id": report.get("report_id"),
                "report_type": report.get("report_type"),
                "description": report.get("description")[:200],  # Truncate for privacy
                "lat": report.get("location", {}).get("latitude"),
                "lon": report.get("location", {}).get("longitude"),
                "area": report.get("location", {}).get("address"),
                "date": report.get("created_at"),
                "votes": report.get("votes", 0),
                "verified": report.get("verified", False)
            })
    
    return {
        "success": True,
        "reports": reports,
        "count": len(reports)
    }


@router.post("/reports/{report_id}/vote")
async def vote_community_report(report_id: str):
    """
    Upvote a community report to increase visibility.
    No auth required - simple community validation.
    """
    
    result = await db.community_reports.update_one(
        {"report_id": report_id, "status": "approved"},
        {"$inc": {"votes": 1}}
    )
    
    if result.modified_count == 0:
        return {"success": False, "message": "Report not found or not approved"}
    
    return {"success": True, "message": "Vote recorded"}


@router.get("/report-types")
async def get_report_types():
    """Get available report types with descriptions"""
    return {
        "types": [
            {
                "value": "safety_tip",
                "label": "Safety Tip",
                "description": "Share safety advice for a specific area",
                "icon": "shield"
            },
            {
                "value": "incident",
                "label": "Incident Report",
                "description": "Report a police encounter or civil rights concern",
                "icon": "alert-triangle"
            },
            {
                "value": "concern",
                "label": "Area Concern",
                "description": "Flag an area with known issues or patterns",
                "icon": "map-pin"
            },
            {
                "value": "positive",
                "label": "Positive Interaction",
                "description": "Share a positive experience with law enforcement",
                "icon": "thumbs-up"
            }
        ]
    }


def _get_area_name(address: Optional[str]) -> Optional[str]:
    """Extract general area name from address for privacy"""
    if not address:
        return None
    
    # Try to extract city/neighborhood
    parts = address.split(",")
    if len(parts) >= 2:
        return parts[-2].strip()  # Usually city
    return None

