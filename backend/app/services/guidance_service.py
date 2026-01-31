"""
Smart Guidance System - Backend Service

Analyzes user state and provides contextual next-step recommendations
"""

from datetime import datetime, timezone
from typing import Optional, List
from bson import ObjectId

# Priority levels for guidance
PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

# Guidance categories
CATEGORY_SETUP = "setup"
CATEGORY_SAFETY = "safety"
CATEGORY_LEGAL = "legal"
CATEGORY_EVIDENCE = "evidence"
CATEGORY_ACTION = "action"


def get_user_guidance(db, user_id: str, current_page: Optional[str] = None) -> dict:
    """
    Analyze user state and return contextual guidance suggestions.
    """
    user = db.users.find_one({"_id": ObjectId(user_id)}, {"_id": 0, "password": 0})
    if not user:
        return {"suggestions": [], "completion_score": 0}
    
    suggestions = []
    completion_items = []
    
    # ===== PROFILE & SETUP CHECKS =====
    
    # Check emergency contacts
    contacts_count = db.emergency_contacts.count_documents({"user_id": user_id})
    if contacts_count == 0:
        suggestions.append({
            "id": "add_emergency_contacts",
            "title": "Add Emergency Contacts",
            "description": "Set up people who will be notified during an SOS alert. This is critical for your safety.",
            "action_url": "/emergency-contacts",
            "action_label": "Add Contacts",
            "priority": PRIORITY_CRITICAL,
            "category": CATEGORY_SAFETY,
            "icon": "users",
            "estimated_time": "2 min"
        })
    else:
        completion_items.append("emergency_contacts")
    
    # Check if user has verified email (if applicable)
    if not user.get("email_verified", True):
        suggestions.append({
            "id": "verify_email",
            "title": "Verify Your Email",
            "description": "Verify your email to receive important notifications and alerts.",
            "action_url": "/settings",
            "action_label": "Verify Email",
            "priority": PRIORITY_HIGH,
            "category": CATEGORY_SETUP,
            "icon": "mail",
            "estimated_time": "1 min"
        })
    else:
        completion_items.append("email_verified")
    
    # Check attorney connection
    attorney_connections = db.attorney_connections.count_documents({
        "user_id": user_id,
        "status": "active"
    })
    if attorney_connections == 0:
        suggestions.append({
            "id": "connect_attorney",
            "title": "Connect with an Attorney",
            "description": "Having an attorney on standby ensures immediate legal support during encounters.",
            "action_url": "/attorneys",
            "action_label": "Find Attorney",
            "priority": PRIORITY_HIGH,
            "category": CATEGORY_LEGAL,
            "icon": "scale",
            "estimated_time": "5 min"
        })
    else:
        completion_items.append("attorney_connected")
    
    # ===== KNOWLEDGE & TRAINING =====
    
    # Check rights training completion
    training_progress = db.training_progress.find_one({"user_id": user_id})
    modules_completed = training_progress.get("completed_modules", []) if training_progress else []
    
    if len(modules_completed) < 3:
        suggestions.append({
            "id": "complete_training",
            "title": "Complete Rights Training",
            "description": f"You have completed {len(modules_completed)}/5 training modules. Knowledge is your best protection.",
            "action_url": "/training",
            "action_label": "Continue Training",
            "priority": PRIORITY_MEDIUM,
            "category": CATEGORY_LEGAL,
            "icon": "graduation-cap",
            "estimated_time": "10 min",
            "progress": len(modules_completed) / 5 * 100
        })
    else:
        completion_items.append("training_complete")
    
    # ===== ENCOUNTER & EVIDENCE CHECKS =====
    
    # Check recent encounters
    recent_encounters = list(db.encounters.find(
        {"user_id": user_id},
        {"_id": 0, "encounter_id": 1, "status": 1, "created_at": 1, "ai_analysis": 1}
    ).sort("created_at", -1).limit(5))
    
    # Check for encounters needing review
    for enc in recent_encounters:
        if enc.get("status") == "completed" and not enc.get("ai_analysis"):
            suggestions.append({
                "id": f"review_encounter_{enc['encounter_id']}",
                "title": "Review Recent Encounter",
                "description": "Your recent encounter has not been analyzed yet. Review the AI analysis for potential violations.",
                "action_url": f"/encounters/{enc['encounter_id']}",
                "action_label": "Review Now",
                "priority": PRIORITY_HIGH,
                "category": CATEGORY_ACTION,
                "icon": "file-search",
                "estimated_time": "5 min"
            })
            break  # Only show one
    
    # Check for incomplete cases
    incomplete_cases = db.cases.count_documents({
        "user_id": user_id,
        "status": {"$in": ["open", "in_progress"]}
    })
    
    if incomplete_cases > 0:
        case = db.cases.find_one(
            {"user_id": user_id, "status": {"$in": ["open", "in_progress"]}},
            {"_id": 0, "case_id": 1, "title": 1}
        )
        if case:
            case_title = case.get("title", "Untitled")[:30]
            suggestions.append({
                "id": f"continue_case_{case.get('case_id', '')}",
                "title": f"Continue Case: {case_title}",
                "description": f"You have {incomplete_cases} open case(s). Continue building your evidence.",
                "action_url": f"/cases/{case.get('case_id', '')}",
                "action_label": "Open Case",
                "priority": PRIORITY_MEDIUM,
                "category": CATEGORY_LEGAL,
                "icon": "folder-open",
                "estimated_time": "10 min"
            })
    
    # ===== CONTEXTUAL PAGE-SPECIFIC GUIDANCE =====
    
    if current_page:
        page_suggestions = get_page_specific_guidance(db, user_id, current_page, user)
        suggestions.extend(page_suggestions)
    
    # ===== PROACTIVE SUGGESTIONS =====
    
    # If user hasn't done an encounter recently, suggest practice
    if len(recent_encounters) == 0:
        suggestions.append({
            "id": "first_encounter_prep",
            "title": "Prepare for Your First Encounter",
            "description": "Familiarize yourself with the Encounter Mode before you need it in a real situation.",
            "action_url": "/encounter",
            "action_label": "Try Encounter Mode",
            "priority": PRIORITY_MEDIUM,
            "category": CATEGORY_SAFETY,
            "icon": "shield",
            "estimated_time": "3 min"
        })
    
    # Evidence backup reminder
    evidence_count = db.evidence.count_documents({"user_id": user_id})
    backed_up_count = db.evidence.count_documents({"user_id": user_id, "cloud_backup": True})
    
    if evidence_count > 0 and backed_up_count < evidence_count:
        not_backed_up = evidence_count - backed_up_count
        suggestions.append({
            "id": "backup_evidence",
            "title": "Backup Your Evidence",
            "description": f"{not_backed_up} evidence file(s) need cloud backup for safety.",
            "action_url": "/evidence",
            "action_label": "Manage Evidence",
            "priority": PRIORITY_MEDIUM,
            "category": CATEGORY_EVIDENCE,
            "icon": "cloud-upload",
            "estimated_time": "2 min"
        })
    
    # ===== CALCULATE COMPLETION SCORE =====
    
    total_setup_items = 5  # contacts, email, attorney, training, first encounter
    completion_score = min(100, int(len(completion_items) / total_setup_items * 100))
    
    # Sort by priority
    priority_order = {PRIORITY_CRITICAL: 0, PRIORITY_HIGH: 1, PRIORITY_MEDIUM: 2, PRIORITY_LOW: 3}
    suggestions.sort(key=lambda x: priority_order.get(x["priority"], 3))
    
    return {
        "suggestions": suggestions[:5],  # Limit to top 5
        "all_suggestions": suggestions,
        "completion_score": completion_score,
        "completion_items": completion_items,
        "user_stats": {
            "encounters_count": len(recent_encounters),
            "cases_count": incomplete_cases,
            "contacts_count": contacts_count,
            "has_attorney": attorney_connections > 0
        }
    }


def get_page_specific_guidance(db, user_id: str, current_page: str, user: dict) -> List[dict]:
    """
    Get guidance specific to the current page the user is viewing.
    """
    suggestions = []
    
    if current_page == "dashboard":
        # On dashboard, highlight the most important next action
        pass  # Main suggestions cover this
    
    elif current_page == "encounter":
        # Pre-encounter checklist
        contacts_count = db.emergency_contacts.count_documents({"user_id": user_id})
        if contacts_count == 0:
            suggestions.append({
                "id": "encounter_add_contacts",
                "title": "No Emergency Contacts Set",
                "description": "Add contacts before starting - they will be notified if you trigger SOS.",
                "action_url": "/emergency-contacts",
                "action_label": "Add Now",
                "priority": PRIORITY_CRITICAL,
                "category": CATEGORY_SAFETY,
                "icon": "alert-triangle",
                "estimated_time": "2 min",
                "contextual": True
            })
    
    elif current_page == "cases":
        # Suggest creating first case if none exist
        cases_count = db.cases.count_documents({"user_id": user_id})
        if cases_count == 0:
            encounters_count = db.encounters.count_documents({"user_id": user_id})
            if encounters_count > 0:
                suggestions.append({
                    "id": "create_first_case",
                    "title": "Create Your First Case",
                    "description": "Organize your encounters and evidence into a legal case for better tracking.",
                    "action_url": "/cases/new",
                    "action_label": "Create Case",
                    "priority": PRIORITY_MEDIUM,
                    "category": CATEGORY_LEGAL,
                    "icon": "folder-plus",
                    "estimated_time": "5 min",
                    "contextual": True
                })
    
    elif current_page == "evidence":
        # Suggest organizing evidence
        untagged_evidence = db.evidence.count_documents({
            "user_id": user_id,
            "tags": {"$size": 0}
        })
        if untagged_evidence > 0:
            suggestions.append({
                "id": "tag_evidence",
                "title": "Organize Your Evidence",
                "description": f"{untagged_evidence} file(s) need tags for better organization.",
                "action_url": "/evidence",
                "action_label": "Tag Files",
                "priority": PRIORITY_LOW,
                "category": CATEGORY_EVIDENCE,
                "icon": "tag",
                "estimated_time": "3 min",
                "contextual": True
            })
    
    elif "encounters/" in current_page:
        # On encounter report page
        suggestions.append({
            "id": "share_with_attorney",
            "title": "Share with Your Attorney",
            "description": "Your attorney can review this encounter and provide legal advice.",
            "action_url": "/attorneys",
            "action_label": "Share",
            "priority": PRIORITY_MEDIUM,
            "category": CATEGORY_LEGAL,
            "icon": "share",
            "estimated_time": "1 min",
            "contextual": True
        })
    
    return suggestions


def get_onboarding_checklist(db, user_id: str) -> dict:
    """
    Get a comprehensive onboarding checklist for new users.
    """
    checklist_items = [
        {
            "id": "profile",
            "title": "Complete Your Profile",
            "description": "Add your basic information",
            "url": "/settings",
            "check_fn": "profile"
        },
        {
            "id": "emergency_contacts",
            "title": "Add Emergency Contacts",
            "description": "People to notify during emergencies",
            "url": "/emergency-contacts",
            "check_fn": "contacts"
        },
        {
            "id": "know_rights",
            "title": "Learn Your Rights",
            "description": "Complete at least one training module",
            "url": "/training",
            "check_fn": "training"
        },
        {
            "id": "connect_attorney",
            "title": "Connect with an Attorney",
            "description": "Have legal support on standby",
            "url": "/attorneys",
            "check_fn": "attorney"
        },
        {
            "id": "test_encounter",
            "title": "Try Encounter Mode",
            "description": "Familiarize yourself with the recording system",
            "url": "/encounter",
            "check_fn": "encounter"
        }
    ]
    
    # Run checks
    contacts_count = db.emergency_contacts.count_documents({"user_id": user_id})
    training_count = db.training_progress.count_documents({
        "user_id": user_id,
        "completed_modules.0": {"$exists": True}
    })
    attorney_count = db.attorney_connections.count_documents({
        "user_id": user_id,
        "status": "active"
    })
    encounters_count = db.encounters.count_documents({"user_id": user_id})
    
    check_results = {
        "profile": True,  # Assumed complete on registration
        "contacts": contacts_count > 0,
        "training": training_count > 0,
        "attorney": attorney_count > 0,
        "encounter": encounters_count > 0
    }
    
    completed = []
    pending = []
    
    for item in checklist_items:
        item_data = {
            "id": item["id"],
            "title": item["title"],
            "description": item["description"],
            "url": item["url"]
        }
        if check_results.get(item["check_fn"], False):
            item_data["completed"] = True
            completed.append(item_data)
        else:
            item_data["completed"] = False
            pending.append(item_data)
    
    total = len(checklist_items)
    return {
        "completed": completed,
        "pending": pending,
        "progress": len(completed) / total * 100 if total > 0 else 0,
        "total": total,
        "completed_count": len(completed)
    }
