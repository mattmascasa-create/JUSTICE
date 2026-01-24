"""
Know Your Rights Training Service
Interactive learning with scenarios, quizzes, and gamification
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List

from app.db.database import db


# ============== Training Content Data ==============

RIGHTS_CATEGORIES = [
    {
        "id": "traffic_stop",
        "title": "Traffic Stops",
        "description": "Know your rights during vehicle stops",
        "icon": "car",
        "color": "blue"
    },
    {
        "id": "pedestrian_stop",
        "title": "Pedestrian Stops",
        "description": "Walking while being stopped by police",
        "icon": "footprints",
        "color": "green"
    },
    {
        "id": "home_search",
        "title": "Home Searches",
        "description": "Your rights when police come to your door",
        "icon": "home",
        "color": "purple"
    },
    {
        "id": "recording_rights",
        "title": "Recording Police",
        "description": "Your right to film law enforcement",
        "icon": "video",
        "color": "red"
    },
    {
        "id": "arrest_procedures",
        "title": "Arrest Procedures",
        "description": "What to do if you're being arrested",
        "icon": "handcuffs",
        "color": "orange"
    },
    {
        "id": "immigration",
        "title": "Immigration Encounters",
        "description": "Rights during immigration-related stops",
        "icon": "globe",
        "color": "teal"
    }
]

SCENARIOS = [
    # Traffic Stop Scenarios
    {
        "id": "traffic_1",
        "category": "traffic_stop",
        "title": "The Routine Traffic Stop",
        "difficulty": "beginner",
        "points": 10,
        "situation": "You're pulled over for a broken taillight. The officer asks to search your vehicle.",
        "question": "What is the best response?",
        "options": [
            {"id": "a", "text": "Sure, go ahead and search", "correct": False, "explanation": "You have the right to refuse consent to a search. Never voluntarily give up your rights."},
            {"id": "b", "text": "I do not consent to searches, but I won't physically resist", "correct": True, "explanation": "This is the correct response. Clearly state you don't consent, but never physically resist."},
            {"id": "c", "text": "You need a warrant!", "correct": False, "explanation": "While warrants are often required, saying this confrontationally can escalate the situation. Calmly decline consent instead."},
            {"id": "d", "text": "What are you looking for?", "correct": False, "explanation": "This doesn't assert your rights. Clearly state that you do not consent to searches."}
        ],
        "key_rights": ["4th Amendment - Protection against unreasonable searches", "Right to refuse consent"],
        "tips": ["Stay calm and polite", "Keep hands visible", "Don't argue - assert rights calmly"]
    },
    {
        "id": "traffic_2",
        "category": "traffic_stop",
        "title": "License and Registration",
        "difficulty": "beginner",
        "points": 10,
        "situation": "An officer asks for your license, registration, and where you're coming from.",
        "question": "What are you legally required to provide?",
        "options": [
            {"id": "a", "text": "All three - license, registration, and answer questions", "correct": False, "explanation": "You must provide documents, but you have the right to remain silent about where you're going."},
            {"id": "b", "text": "License and registration only", "correct": True, "explanation": "Correct! You must provide documents but can politely decline to answer questions about your travels."},
            {"id": "c", "text": "Nothing - you have the right to remain silent", "correct": False, "explanation": "During a traffic stop, you must provide license and registration. Silence applies to questioning, not document requests."},
            {"id": "d", "text": "Only your name", "correct": False, "explanation": "Traffic stops require license and registration. Just your name is not sufficient."}
        ],
        "key_rights": ["5th Amendment - Right to remain silent", "Must provide license/registration when driving"],
        "tips": ["Provide documents promptly", "You can say 'I prefer not to answer questions'"]
    },
    {
        "id": "traffic_3",
        "category": "traffic_stop",
        "title": "The Smell Test",
        "difficulty": "intermediate",
        "points": 20,
        "situation": "The officer claims to smell marijuana and wants to search your car without your consent.",
        "question": "What should you do?",
        "options": [
            {"id": "a", "text": "Let them search since they have probable cause", "correct": False, "explanation": "Even if they claim probable cause, you should still verbally decline consent. This preserves your rights if challenged in court."},
            {"id": "b", "text": "Verbally state you don't consent, but don't physically resist if they proceed", "correct": True, "explanation": "Correct! Always verbally decline consent. If they search anyway, don't resist - challenge it in court later."},
            {"id": "c", "text": "Block the officer from searching", "correct": False, "explanation": "Never physically resist. This can lead to additional charges and danger."},
            {"id": "d", "text": "Demand to see a warrant", "correct": False, "explanation": "Officers can search without a warrant if they have probable cause. State your non-consent and document everything."}
        ],
        "key_rights": ["Right to refuse consent even when probable cause is claimed", "Challenge searches in court, not on the street"],
        "tips": ["Say: 'I do not consent to this search'", "Start recording if possible", "Note badge numbers and what was said"]
    },
    # Recording Rights Scenarios
    {
        "id": "recording_1",
        "category": "recording_rights",
        "title": "Filming the Police",
        "difficulty": "beginner",
        "points": 10,
        "situation": "You're witnessing police activity and start recording. An officer tells you to stop filming and put your phone away.",
        "question": "What is your right in this situation?",
        "options": [
            {"id": "a", "text": "You must comply and stop recording", "correct": False, "explanation": "The First Amendment protects your right to record police performing their duties in public."},
            {"id": "b", "text": "You have the right to record, but should do so from a safe distance without interfering", "correct": True, "explanation": "Correct! You can record police in public spaces as long as you don't interfere with their duties."},
            {"id": "c", "text": "You can record but must provide your phone if asked", "correct": False, "explanation": "Police cannot seize your phone without a warrant, and you don't have to hand it over."},
            {"id": "d", "text": "Recording police is illegal", "correct": False, "explanation": "Recording police in public is legal and protected by the First Amendment."}
        ],
        "key_rights": ["1st Amendment - Right to record public officials", "Glik v. Cunniffe (2011) - Recording police is protected"],
        "tips": ["Keep a safe distance", "Don't interfere with police activity", "Use cloud backup for your recording"]
    },
    {
        "id": "recording_2",
        "category": "recording_rights",
        "title": "Phone Seizure",
        "difficulty": "intermediate",
        "points": 20,
        "situation": "After recording an incident, an officer demands your phone as 'evidence.'",
        "question": "What should you do?",
        "options": [
            {"id": "a", "text": "Hand over the phone immediately", "correct": False, "explanation": "Police generally need a warrant to seize your phone. You can refuse."},
            {"id": "b", "text": "Delete the video quickly", "correct": False, "explanation": "Deleting evidence could be considered obstruction of justice."},
            {"id": "c", "text": "State that you don't consent to the seizure but won't physically resist", "correct": True, "explanation": "Correct! Clearly state you don't consent. If they take it anyway, don't resist - challenge it legally."},
            {"id": "d", "text": "Throw the phone to a friend", "correct": False, "explanation": "This could be seen as interference and lead to additional problems."}
        ],
        "key_rights": ["4th Amendment - Protection against seizure", "Riley v. California (2014) - Warrant required for phone searches"],
        "tips": ["Set up automatic cloud backup", "Know your phone's emergency lock features", "Get badge numbers and witness info"]
    },
    # Home Search Scenarios
    {
        "id": "home_1",
        "category": "home_search",
        "title": "Police at Your Door",
        "difficulty": "beginner",
        "points": 10,
        "situation": "Police knock on your door and ask to come inside to 'look around.'",
        "question": "What is your best response?",
        "options": [
            {"id": "a", "text": "Let them in - refusing looks suspicious", "correct": False, "explanation": "Exercising your rights is never suspicious. You have strong 4th Amendment protections at home."},
            {"id": "b", "text": "Step outside and close the door, then ask if they have a warrant", "correct": True, "explanation": "Correct! Your home has the strongest 4th Amendment protection. Ask for a warrant."},
            {"id": "c", "text": "Ignore them completely", "correct": False, "explanation": "While you can choose not to answer, it's better to communicate that you're invoking your rights."},
            {"id": "d", "text": "Only let them check one room", "correct": False, "explanation": "Partial consent is still consent. Don't let them in without a warrant."}
        ],
        "key_rights": ["4th Amendment - Strongest at home", "Can refuse entry without a warrant", "Payton v. New York (1980)"],
        "tips": ["Speak through the door or step outside", "Ask: 'Do you have a warrant?'", "If they have a warrant, ask to see it"]
    },
    # Arrest Scenarios
    {
        "id": "arrest_1",
        "category": "arrest_procedures",
        "title": "Being Arrested",
        "difficulty": "beginner",
        "points": 10,
        "situation": "An officer says you're under arrest. What should you do?",
        "question": "What is the correct course of action?",
        "options": [
            {"id": "a", "text": "Run away if you're innocent", "correct": False, "explanation": "Never run. This can result in additional charges and danger."},
            {"id": "b", "text": "Comply physically, state you're invoking your right to remain silent and want an attorney", "correct": True, "explanation": "Correct! Comply with the arrest, but clearly invoke your Miranda rights."},
            {"id": "c", "text": "Explain why you're innocent", "correct": False, "explanation": "Anything you say can be used against you. Wait for your attorney."},
            {"id": "d", "text": "Demand to know the charges before complying", "correct": False, "explanation": "While you can ask, refusing to comply until told can escalate the situation."}
        ],
        "key_rights": ["5th Amendment - Right to remain silent", "6th Amendment - Right to an attorney", "Miranda rights"],
        "tips": ["Say: 'I am invoking my right to remain silent and want an attorney'", "Don't resist physically", "Remember details for later"]
    },
    # Pedestrian Stop Scenarios
    {
        "id": "pedestrian_1",
        "category": "pedestrian_stop",
        "title": "Stop and Identify",
        "difficulty": "intermediate",
        "points": 20,
        "situation": "While walking, an officer stops you and demands to see your ID.",
        "question": "What are your obligations?",
        "options": [
            {"id": "a", "text": "You must always show ID when asked", "correct": False, "explanation": "ID requirements vary by state. In many states, you only need to identify yourself if the officer has reasonable suspicion of a crime."},
            {"id": "b", "text": "Ask 'Am I being detained?' and 'Am I free to go?'", "correct": True, "explanation": "Correct! These questions help establish whether you're legally required to stay and identify yourself."},
            {"id": "c", "text": "Refuse to speak at all", "correct": False, "explanation": "In some states, refusing to identify during a lawful detention can itself be a violation."},
            {"id": "d", "text": "Provide fake information", "correct": False, "explanation": "Providing false information to police is illegal and will create more problems."}
        ],
        "key_rights": ["4th Amendment - Freedom from unreasonable seizure", "Terry v. Ohio (1968) - Stop and frisk rules", "State-specific ID laws"],
        "tips": ["Know your state's stop-and-identify laws", "Ask if you're being detained", "Ask if you're free to go"]
    }
]

BADGES = [
    {"id": "first_lesson", "name": "First Steps", "description": "Complete your first lesson", "icon": "star", "points_required": 10},
    {"id": "traffic_expert", "name": "Traffic Expert", "description": "Complete all traffic stop scenarios", "icon": "car", "points_required": 0, "category": "traffic_stop"},
    {"id": "recording_pro", "name": "Recording Pro", "description": "Complete all recording rights scenarios", "icon": "video", "points_required": 0, "category": "recording_rights"},
    {"id": "home_defender", "name": "Home Defender", "description": "Complete all home search scenarios", "icon": "home", "points_required": 0, "category": "home_search"},
    {"id": "point_collector_100", "name": "Century", "description": "Earn 100 points", "icon": "trophy", "points_required": 100},
    {"id": "point_collector_500", "name": "Scholar", "description": "Earn 500 points", "icon": "award", "points_required": 500},
    {"id": "perfect_score", "name": "Perfect Score", "description": "Complete a scenario without mistakes", "icon": "check-circle", "points_required": 0},
    {"id": "streak_7", "name": "Week Warrior", "description": "7-day learning streak", "icon": "flame", "points_required": 0},
]


class RightsTrainingService:
    """Service for Know Your Rights training and gamification"""

    def get_categories(self) -> List[Dict]:
        """Get all training categories"""
        return RIGHTS_CATEGORIES

    def get_scenarios(self, category: Optional[str] = None) -> List[Dict]:
        """Get scenarios, optionally filtered by category"""
        if category:
            return [s for s in SCENARIOS if s["category"] == category]
        return SCENARIOS

    def get_scenario(self, scenario_id: str) -> Optional[Dict]:
        """Get a specific scenario"""
        for s in SCENARIOS:
            if s["id"] == scenario_id:
                return s
        return None

    async def get_user_progress(self, user_id: str) -> Dict:
        """Get user's training progress"""
        progress = await db.training_progress.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        
        if not progress:
            progress = {
                "user_id": user_id,
                "total_points": 0,
                "level": 1,
                "completed_scenarios": [],
                "badges": [],
                "streak_days": 0,
                "last_activity": None,
                "category_progress": {}
            }
            await db.training_progress.insert_one(progress)
        
        # Calculate level from points
        progress["level"] = self._calculate_level(progress["total_points"])
        progress["next_level_points"] = self._points_for_level(progress["level"] + 1)
        
        return progress

    def _calculate_level(self, points: int) -> int:
        """Calculate level from points"""
        level = 1
        while self._points_for_level(level + 1) <= points:
            level += 1
        return level

    def _points_for_level(self, level: int) -> int:
        """Points required for a given level"""
        return int(50 * (level ** 1.5))

    async def submit_answer(
        self, 
        user_id: str, 
        scenario_id: str, 
        answer_id: str
    ) -> Dict:
        """Submit an answer to a scenario"""
        scenario = self.get_scenario(scenario_id)
        if not scenario:
            return {"success": False, "error": "Scenario not found"}
        
        # Find the selected option
        selected_option = None
        correct_option = None
        for opt in scenario["options"]:
            if opt["id"] == answer_id:
                selected_option = opt
            if opt["correct"]:
                correct_option = opt
        
        if not selected_option:
            return {"success": False, "error": "Invalid answer"}
        
        is_correct = selected_option["correct"]
        points_earned = scenario["points"] if is_correct else 0
        
        # Get current progress
        progress = await self.get_user_progress(user_id)
        
        # Check if already completed
        already_completed = scenario_id in progress["completed_scenarios"]
        if already_completed:
            points_earned = 0  # No points for re-doing
        
        # Update progress
        update_data = {
            "last_activity": datetime.now(timezone.utc).isoformat()
        }
        
        if is_correct and not already_completed:
            update_data["$inc"] = {"total_points": points_earned}
            update_data["$addToSet"] = {"completed_scenarios": scenario_id}
            
            # Update category progress
            category = scenario["category"]
            cat_key = f"category_progress.{category}"
            if category not in progress.get("category_progress", {}):
                update_data["$set"] = {cat_key: {"completed": 1, "total_points": points_earned}}
            else:
                update_data["$inc"][f"{cat_key}.completed"] = 1
                update_data["$inc"][f"{cat_key}.total_points"] = points_earned
        
        # Update streak
        await self._update_streak(user_id, progress)
        
        # Apply update
        if "$inc" in update_data or "$addToSet" in update_data or "$set" in update_data:
            await db.training_progress.update_one(
                {"user_id": user_id},
                {k: v for k, v in update_data.items() if k.startswith("$")}
            )
        
        await db.training_progress.update_one(
            {"user_id": user_id},
            {"$set": {"last_activity": update_data["last_activity"]}}
        )
        
        # Check for new badges
        new_badges = await self._check_badges(user_id, scenario_id, is_correct)
        
        return {
            "success": True,
            "correct": is_correct,
            "points_earned": points_earned,
            "explanation": selected_option["explanation"],
            "correct_answer": correct_option,
            "key_rights": scenario["key_rights"],
            "tips": scenario["tips"],
            "new_badges": new_badges,
            "already_completed": already_completed
        }

    async def _update_streak(self, user_id: str, progress: Dict):
        """Update user's learning streak"""
        last_activity = progress.get("last_activity")
        now = datetime.now(timezone.utc)
        
        if last_activity:
            last_date = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
            days_diff = (now.date() - last_date.date()).days
            
            if days_diff == 1:
                # Continue streak
                await db.training_progress.update_one(
                    {"user_id": user_id},
                    {"$inc": {"streak_days": 1}}
                )
            elif days_diff > 1:
                # Reset streak
                await db.training_progress.update_one(
                    {"user_id": user_id},
                    {"$set": {"streak_days": 1}}
                )
        else:
            # First activity
            await db.training_progress.update_one(
                {"user_id": user_id},
                {"$set": {"streak_days": 1}}
            )

    async def _check_badges(
        self, 
        user_id: str, 
        scenario_id: str, 
        is_correct: bool
    ) -> List[Dict]:
        """Check and award new badges"""
        progress = await self.get_user_progress(user_id)
        new_badges = []
        current_badges = set(progress.get("badges", []))
        
        for badge in BADGES:
            if badge["id"] in current_badges:
                continue
            
            earned = False
            
            # Point-based badges
            if badge.get("points_required", 0) > 0:
                if progress["total_points"] >= badge["points_required"]:
                    earned = True
            
            # Category completion badges
            elif badge.get("category"):
                category_scenarios = [s["id"] for s in SCENARIOS if s["category"] == badge["category"]]
                completed = set(progress.get("completed_scenarios", []))
                if all(s in completed for s in category_scenarios):
                    earned = True
            
            # First lesson badge
            elif badge["id"] == "first_lesson" and len(progress.get("completed_scenarios", [])) >= 1:
                earned = True
            
            # Perfect score badge
            elif badge["id"] == "perfect_score" and is_correct:
                earned = True
            
            # Streak badge
            elif badge["id"] == "streak_7" and progress.get("streak_days", 0) >= 7:
                earned = True
            
            if earned:
                new_badges.append(badge)
                await db.training_progress.update_one(
                    {"user_id": user_id},
                    {"$addToSet": {"badges": badge["id"]}}
                )
        
        return new_badges

    def get_badges(self) -> List[Dict]:
        """Get all available badges"""
        return BADGES

    async def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top learners"""
        cursor = db.training_progress.find(
            {},
            {"_id": 0, "user_id": 1, "total_points": 1, "level": 1, "badges": 1}
        ).sort("total_points", -1).limit(limit)
        
        leaders = await cursor.to_list(limit)
        
        # Get user names
        for leader in leaders:
            user = await db.users.find_one(
                {"user_id": leader["user_id"]},
                {"name": 1, "email": 1}
            )
            if user:
                leader["name"] = user.get("name") or user.get("email", "").split("@")[0]
            leader["level"] = self._calculate_level(leader.get("total_points", 0))
            leader["badge_count"] = len(leader.get("badges", []))
        
        return leaders


# Global service instance
rights_training_service = RightsTrainingService()
