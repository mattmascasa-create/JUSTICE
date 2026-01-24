"""
Know Your Rights Router - Legal information and rights guidance
"""
from fastapi import APIRouter

router = APIRouter(prefix="/rights", tags=["Know Your Rights"])


# Rights database - formatted for frontend
RIGHTS_INFO = {
    "traffic_stop": {
        "title": "Traffic Stop Rights",
        "summary": "Know your rights during a traffic stop - what you must do and what you can refuse.",
        "amendment": "4th & 5th",
        "icon": "Shield",
        "key_points": [
            "You have the right to remain silent",
            "You do NOT have to consent to a search of your vehicle",
            "You can ask: 'Am I being detained or am I free to go?'",
            "You have the right to refuse field sobriety tests in most states",
            "You must provide license, registration, and insurance when asked"
        ],
        "what_to_say": "Officer, I am exercising my right to remain silent. I do not consent to any searches.",
        "dos": [
            "Keep your hands visible on the steering wheel",
            "Be polite but assertive about your rights",
            "Record the encounter if safe to do so",
            "Note badge numbers and officer names"
        ],
        "donts": [
            "Don't physically resist even if your rights are violated",
            "Don't argue or become confrontational",
            "Don't consent to searches you don't have to allow",
            "Don't make sudden movements"
        ],
        "legal_citations": ["4th Amendment", "5th Amendment", "Terry v. Ohio"]
    },
    "arrest": {
        "title": "Rights During Arrest",
        "summary": "Your constitutional rights during an arrest - know what to say and what not to do.",
        "amendment": "5th & 6th",
        "icon": "Scale",
        "key_points": [
            "You have the right to remain silent (5th Amendment)",
            "You have the right to an attorney (6th Amendment)",
            "You must be read your Miranda rights before interrogation",
            "You have the right to know the charges against you"
        ],
        "what_to_say": "I am exercising my right to remain silent. I want a lawyer.",
        "dos": [
            "State clearly: 'I am exercising my right to remain silent'",
            "State clearly: 'I want a lawyer'",
            "Comply physically with arrest to avoid additional charges",
            "Remember details of the arrest"
        ],
        "donts": [
            "Don't resist arrest physically",
            "Don't answer questions without a lawyer",
            "Don't sign anything without legal counsel",
            "Don't consent to searches"
        ],
        "legal_citations": ["5th Amendment", "6th Amendment", "Miranda v. Arizona"]
    },
    "search": {
        "title": "Search & Seizure Rights",
        "summary": "Protection against unreasonable searches - your 4th Amendment shield.",
        "amendment": "4th",
        "icon": "Shield",
        "key_points": [
            "Police generally need a warrant to search your home",
            "You can refuse consent to any search",
            "You can ask: 'Do you have a warrant?'",
            "Plain view doctrine: visible contraband can be seized",
            "You can refuse to open your door without a warrant"
        ],
        "what_to_say": "I do not consent to this search. Do you have a warrant?",
        "dos": [
            "Clearly state: 'I do not consent to this search'",
            "Ask to see the warrant and check its validity",
            "Document what was searched and seized"
        ],
        "donts": [
            "Don't physically block officers with a warrant",
            "Don't hide or destroy evidence",
            "Don't obstruct justice"
        ],
        "exceptions": [
            "Search incident to lawful arrest",
            "Plain view doctrine",
            "Exigent circumstances (emergency)",
            "Automobile exception",
            "Consent (which you can refuse)"
        ],
        "legal_citations": ["4th Amendment", "Mapp v. Ohio", "Terry v. Ohio"]
    },
    "protest": {
        "title": "First Amendment Protest Rights",
        "summary": "Your rights during protests and demonstrations - freedom of assembly and speech.",
        "amendment": "1st",
        "icon": "Megaphone",
        "key_points": [
            "Right to peaceful assembly (1st Amendment)",
            "Right to photograph and record in public",
            "Right to distribute literature and express views",
            "Freedom of speech protection",
            "Right to be in public spaces"
        ],
        "what_to_say": "I am exercising my First Amendment right to peacefully assemble and record.",
        "dos": [
            "Stay on public property",
            "Follow permit requirements when applicable",
            "Record police interactions",
            "Know your exit routes"
        ],
        "donts": [
            "Don't block traffic or entrances illegally",
            "Don't engage in violence",
            "Don't resist if arrested",
            "Don't destroy property"
        ],
        "legal_citations": ["1st Amendment", "14th Amendment"]
    }
}


@router.get("")
async def get_all_rights_categories():
    """Get all rights with full details"""
    rights_list = []
    
    for category, data in RIGHTS_INFO.items():
        rights_list.append({
            "id": category,
            **data
        })
    
    return {
        "rights": rights_list,
        "categories": list(RIGHTS_INFO.keys()),
        "count": len(RIGHTS_INFO)
    }


@router.get("/{category}")
async def get_rights_by_category(category: str):
    """Get detailed rights information for a category"""
    if category not in RIGHTS_INFO:
        return {"error": "Category not found", "available": list(RIGHTS_INFO.keys())}
    
    return RIGHTS_INFO[category]


@router.get("/quick/{situation}")
async def get_quick_rights_reminder(situation: str):
    """Get quick rights reminder for a situation"""
    reminders = {
        "traffic_stop": "You have the right to remain silent. You do NOT have to consent to a search.",
        "arrest": "State: 'I am exercising my right to remain silent' and 'I want a lawyer'",
        "search": "You can refuse consent. Ask: 'Do you have a warrant?'",
        "protest": "You have the right to record. Stay peaceful and on public property.",
        "questioning": "You do not have to answer questions. You can ask: 'Am I free to go?'"
    }
    
    return {
        "situation": situation,
        "reminder": reminders.get(situation, "You have the right to remain silent and the right to an attorney.")
    }
