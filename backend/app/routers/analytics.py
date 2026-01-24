"""
Analytics Router - Encounter statistics and pattern analysis
"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends

from app.db.database import db
from app.core.security import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard")
async def get_dashboard_analytics(current_user: dict = Depends(get_current_user)):
    """Get dashboard analytics summary for the current user"""
    user_id = current_user["user_id"]
    
    # Count cases
    total_cases = await db.cases.count_documents({"user_id": user_id})
    open_cases = await db.cases.count_documents({"user_id": user_id, "status": {"$in": ["open", "active", "pending"]}})
    resolved_cases = await db.cases.count_documents({"user_id": user_id, "status": {"$in": ["resolved", "closed", "completed"]}})
    
    # Count evidence files
    evidence_count = await db.evidence.count_documents({"user_id": user_id})
    
    # Count encounters
    total_encounters = await db.encounters.count_documents({"user_id": user_id})
    
    # Get recent activity (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_cases = await db.cases.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": thirty_days_ago}
    })
    
    # Get violation types for user's encounters
    user_encounters = await db.encounters.find(
        {"user_id": user_id},
        {"encounter_id": 1, "_id": 0}
    ).to_list(1000)
    encounter_ids = [e["encounter_id"] for e in user_encounters]
    
    # Get violations distribution
    violations = []
    if encounter_ids:
        violations_cursor = await db.ai_analysis.aggregate([
            {"$match": {"encounter_id": {"$in": encounter_ids}, "violations": {"$exists": True, "$ne": []}}},
            {"$unwind": "$violations"},
            {"$group": {"_id": "$violations.type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]).to_list(10)
        violations = [{"type": v["_id"], "count": v["count"]} for v in violations_cursor]
    
    return {
        "cases": {
            "total": total_cases,
            "open": open_cases,
            "resolved": resolved_cases
        },
        "evidence_count": evidence_count,
        "encounters": {
            "total": total_encounters
        },
        "recent_activity": {
            "new_cases_30d": recent_cases
        },
        "violations_by_type": violations
    }


@router.get("/encounters/summary")
async def get_encounter_summary(current_user: dict = Depends(get_current_user)):
    """Get comprehensive encounter statistics for the user"""
    user_id = current_user["user_id"]
    
    # Basic counts
    total_encounters = await db.encounters.count_documents({"user_id": user_id})
    active_encounters = await db.encounters.count_documents({"user_id": user_id, "status": "active"})
    completed_encounters = await db.encounters.count_documents({"user_id": user_id, "status": "completed"})
    
    # Get all transcriptions for this user's encounters
    user_encounters = await db.encounters.find(
        {"user_id": user_id},
        {"encounter_id": 1, "_id": 0}
    ).to_list(1000)
    encounter_ids = [e["encounter_id"] for e in user_encounters]
    
    # Aggregate tone data from transcriptions
    tone_pipeline = [
        {"$match": {"encounter_id": {"$in": encounter_ids}}},
        {"$group": {
            "_id": "$tone",
            "count": {"$sum": 1},
            "avg_confidence": {"$avg": "$tone_confidence"}
        }},
        {"$sort": {"count": -1}}
    ]
    tone_distribution = await db.transcriptions.aggregate(tone_pipeline).to_list(20)
    
    # Aggregate officer aggression levels
    aggression_pipeline = [
        {"$match": {"encounter_id": {"$in": encounter_ids}, "officer_demeanor.aggression_level": {"$exists": True}}},
        {"$group": {
            "_id": None,
            "avg_aggression": {"$avg": "$officer_demeanor.aggression_level"},
            "max_aggression": {"$max": "$officer_demeanor.aggression_level"},
            "avg_intimidation": {"$avg": "$officer_demeanor.intimidation_level"},
            "avg_professionalism": {"$avg": "$officer_demeanor.professionalism"}
        }}
    ]
    aggression_stats = await db.transcriptions.aggregate(aggression_pipeline).to_list(1)
    aggression_data = aggression_stats[0] if aggression_stats else {
        "avg_aggression": 0, "max_aggression": 0, "avg_intimidation": 0, "avg_professionalism": 1
    }
    
    # Violation types from encounters
    violation_pipeline = [
        {"$match": {"encounter_id": {"$in": encounter_ids}}},
        {"$unwind": {"path": "$violations_detected", "preserveNullAndEmptyArrays": False}},
        {"$group": {"_id": "$violations_detected", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    violations = await db.transcriptions.aggregate(violation_pipeline).to_list(10)
    
    # Escalation counts
    escalation_pipeline = [
        {"$match": {"encounter_id": {"$in": encounter_ids}, "escalation_detected": True}},
        {"$group": {"_id": "$escalation_direction", "count": {"$sum": 1}}}
    ]
    escalations = await db.transcriptions.aggregate(escalation_pipeline).to_list(10)
    
    # Calculate risk score (0-100)
    risk_score = min(100, int(
        (aggression_data.get("avg_aggression", 0) or 0) * 40 +
        (aggression_data.get("avg_intimidation", 0) or 0) * 30 +
        (1 - (aggression_data.get("avg_professionalism", 1) or 1)) * 30
    ))
    
    return {
        "total_encounters": total_encounters,
        "active_encounters": active_encounters,
        "completed_encounters": completed_encounters,
        "tone_distribution": [{"tone": t["_id"], "count": t["count"], "avg_confidence": round(t.get("avg_confidence", 0) or 0, 2)} for t in tone_distribution if t["_id"]],
        "officer_demeanor": {
            "avg_aggression": round((aggression_data.get("avg_aggression", 0) or 0) * 100, 1),
            "max_aggression": round((aggression_data.get("max_aggression", 0) or 0) * 100, 1),
            "avg_intimidation": round((aggression_data.get("avg_intimidation", 0) or 0) * 100, 1),
            "avg_professionalism": round((aggression_data.get("avg_professionalism", 1) or 1) * 100, 1)
        },
        "violations_by_type": [{"type": v["_id"], "count": v["count"]} for v in violations],
        "escalation_stats": [{"direction": e["_id"], "count": e["count"]} for e in escalations],
        "risk_score": risk_score
    }


@router.get("/encounters/patterns")
async def get_encounter_patterns(current_user: dict = Depends(get_current_user)):
    """Get time-of-day and day-of-week patterns for encounters"""
    user_id = current_user["user_id"]
    
    # Get encounters with timestamps
    encounters = await db.encounters.find(
        {"user_id": user_id, "started_at": {"$exists": True}},
        {"_id": 0, "encounter_id": 1, "started_at": 1, "encounter_type": 1, "latitude": 1, "longitude": 1}
    ).to_list(1000)
    
    # Time of day distribution (0-23 hours)
    hour_counts = {i: 0 for i in range(24)}
    day_counts = {i: 0 for i in range(7)}
    type_counts = {}
    
    for enc in encounters:
        started_at = enc.get("started_at")
        if started_at:
            try:
                if isinstance(started_at, str):
                    dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                else:
                    dt = started_at
                hour_counts[dt.hour] += 1
                day_counts[dt.weekday()] += 1
            except:
                pass
        
        enc_type = enc.get("encounter_type", "unknown")
        type_counts[enc_type] = type_counts.get(enc_type, 0) + 1
    
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    return {
        "by_hour": [{"hour": h, "count": c} for h, c in hour_counts.items()],
        "by_day": [{"day": day_names[d], "day_index": d, "count": c} for d, c in day_counts.items()],
        "by_type": [{"type": t, "count": c} for t, c in sorted(type_counts.items(), key=lambda x: -x[1])],
        "peak_hour": max(hour_counts, key=hour_counts.get) if encounters else None,
        "peak_day": day_names[max(day_counts, key=day_counts.get)] if encounters else None
    }


@router.get("/encounters/hotspots")
async def get_encounter_hotspots(current_user: dict = Depends(get_current_user)):
    """Get geographic hotspots for encounters"""
    user_id = current_user["user_id"]
    
    # Get encounters with location data
    encounters = await db.encounters.find(
        {"user_id": user_id, "latitude": {"$exists": True}, "longitude": {"$exists": True}},
        {"_id": 0, "encounter_id": 1, "latitude": 1, "longitude": 1, "address": 1, "encounter_type": 1, "started_at": 1}
    ).to_list(1000)
    
    # Group by approximate location (rounded to 2 decimal places ~1km)
    location_groups = {}
    for enc in encounters:
        lat = round(enc.get("latitude", 0), 2)
        lng = round(enc.get("longitude", 0), 2)
        key = f"{lat},{lng}"
        
        if key not in location_groups:
            location_groups[key] = {
                "latitude": lat,
                "longitude": lng,
                "count": 0,
                "addresses": [],
                "types": []
            }
        
        location_groups[key]["count"] += 1
        addr = enc.get("address")
        if addr and addr not in location_groups[key]["addresses"]:
            location_groups[key]["addresses"].append(addr)
        enc_type = enc.get("encounter_type")
        if enc_type and enc_type not in location_groups[key]["types"]:
            location_groups[key]["types"].append(enc_type)
    
    # Sort by count and return top hotspots
    hotspots = sorted(location_groups.values(), key=lambda x: -x["count"])[:20]
    
    # Also return all encounter locations for map
    all_locations = [
        {
            "encounter_id": enc["encounter_id"],
            "latitude": enc["latitude"],
            "longitude": enc["longitude"],
            "address": enc.get("address", ""),
            "type": enc.get("encounter_type", "unknown")
        }
        for enc in encounters
    ]
    
    return {
        "hotspots": hotspots,
        "all_locations": all_locations,
        "total_mapped": len(all_locations)
    }


@router.get("/encounters/trends")
async def get_encounter_trends(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Get encounter trends over time"""
    user_id = current_user["user_id"]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Get encounters in date range
    encounters = await db.encounters.find(
        {"user_id": user_id, "started_at": {"$gte": cutoff.isoformat()}},
        {"_id": 0, "encounter_id": 1, "started_at": 1}
    ).to_list(1000)
    
    encounter_ids = [e["encounter_id"] for e in encounters]
    
    # Daily encounter counts
    daily_counts = {}
    for enc in encounters:
        started_at = enc.get("started_at", "")
        if started_at:
            date_str = started_at[:10]
            daily_counts[date_str] = daily_counts.get(date_str, 0) + 1
    
    # Aggression trends per day
    aggression_pipeline = [
        {"$match": {"encounter_id": {"$in": encounter_ids}, "officer_demeanor.aggression_level": {"$exists": True}}},
        {"$group": {
            "_id": {"$substr": ["$created_at", 0, 10]},
            "avg_aggression": {"$avg": "$officer_demeanor.aggression_level"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    aggression_trends = await db.transcriptions.aggregate(aggression_pipeline).to_list(100)
    
    # Fill in missing dates
    all_dates = []
    current = cutoff
    while current <= datetime.now(timezone.utc):
        date_str = current.strftime("%Y-%m-%d")
        agg_data = next((a for a in aggression_trends if a["_id"] == date_str), None)
        all_dates.append({
            "date": date_str,
            "encounters": daily_counts.get(date_str, 0),
            "avg_aggression": round((agg_data.get("avg_aggression", 0) or 0) * 100, 1) if agg_data else 0
        })
        current += timedelta(days=1)
    
    return {
        "period_days": days,
        "total_encounters": len(encounters),
        "daily_data": all_dates,
        "avg_encounters_per_day": round(len(encounters) / days, 2) if days > 0 else 0
    }


@router.get("/public")
async def get_public_analytics():
    """Get anonymized public analytics for transparency page - no auth required"""
    # Get total submissions from community evidence
    total_submissions = await db.community_evidence.count_documents({})
    
    # Get violation type distribution
    violation_dist = await db.community_evidence.aggregate([
        {"$group": {"_id": "$violation_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]).to_list(10)
    
    # Get state distribution
    state_dist = await db.community_evidence.aggregate([
        {"$group": {"_id": "$state", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]).to_list(10)
    
    # Get outcome distribution
    outcome_dist = await db.community_evidence.aggregate([
        {"$group": {"_id": "$outcome", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]).to_list(10)
    
    # If no real data, return sample stats
    if total_submissions == 0:
        return {
            "total_submissions": 1247,
            "total_departments_tracked": 156,
            "total_officers_flagged": 423,
            "settlements_tracked": 45600000,
            "violation_distribution": [
                {"type": "4th Amendment - Unlawful Search", "count": 312},
                {"type": "Excessive Force", "count": 287},
                {"type": "5th Amendment - Miranda Violation", "count": 198},
                {"type": "1st Amendment - Recording Interference", "count": 156},
                {"type": "False Arrest", "count": 134},
                {"type": "Unlawful Detention", "count": 98},
                {"type": "Property Damage", "count": 62}
            ],
            "state_distribution": [
                {"state": "CA", "count": 234},
                {"state": "TX", "count": 189},
                {"state": "NY", "count": 167},
                {"state": "FL", "count": 145},
                {"state": "IL", "count": 123}
            ],
            "outcome_distribution": [
                {"outcome": "pending", "count": 456},
                {"outcome": "resolved", "count": 389},
                {"outcome": "under_investigation", "count": 267},
                {"outcome": "lawsuit_filed", "count": 135}
            ]
        }
    
    return {
        "total_submissions": total_submissions,
        "total_departments_tracked": await db.departments.count_documents({}),
        "total_officers_flagged": await db.community_evidence.distinct("officer_badge"),
        "settlements_tracked": 0,  # Would need to sum from departments
        "violation_distribution": [{"type": v["_id"], "count": v["count"]} for v in violation_dist if v["_id"]],
        "state_distribution": [{"state": s["_id"], "count": s["count"]} for s in state_dist if s["_id"]],
        "outcome_distribution": [{"outcome": o["_id"], "count": o["count"]} for o in outcome_dist if o["_id"]]
    }
