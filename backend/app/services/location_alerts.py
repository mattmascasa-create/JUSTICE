"""
Location-Based Coaching Alerts - Proactive notifications near problematic precincts
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime, timezone
from math import radians, cos, sin, asin, sqrt

from app.db.database import db

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on earth (in km)
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    return c * r


class LocationAlertService:
    """
    Service for generating location-based coaching alerts
    when users are near problematic police departments.
    """
    
    # Known problematic precinct locations (lat, lon, dept_id, dept_name, state)
    # In production, this would be pulled from the accountability database
    PRECINCT_LOCATIONS = [
        # Sample data - these would come from the accountability database
        {"lat": 34.0522, "lon": -118.2437, "dept_id": "dept_los_angeles_ca", "name": "Los Angeles PD", "state": "CA"},
        {"lat": 41.8781, "lon": -87.6298, "dept_id": "dept_chicago_il", "name": "Chicago PD", "state": "IL"},
        {"lat": 40.7128, "lon": -74.0060, "dept_id": "dept_new_york_ny", "name": "NYPD", "state": "NY"},
        {"lat": 29.7604, "lon": -95.3698, "dept_id": "dept_houston_tx", "name": "Houston PD", "state": "TX"},
        {"lat": 33.7490, "lon": -84.3880, "dept_id": "dept_atlanta_ga", "name": "Atlanta PD", "state": "GA"},
        {"lat": 25.7617, "lon": -80.1918, "dept_id": "dept_miami_fl", "name": "Miami PD", "state": "FL"},
        {"lat": 47.6062, "lon": -122.3321, "dept_id": "dept_seattle_wa", "name": "Seattle PD", "state": "WA"},
        {"lat": 39.7392, "lon": -104.9903, "dept_id": "dept_denver_co", "name": "Denver PD", "state": "CO"},
    ]
    
    # Alert threshold radius in km
    ALERT_RADIUS_KM = 5.0
    
    async def check_location_alerts(
        self, 
        latitude: float, 
        longitude: float,
        user_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Check if user is near any problematic precincts and generate alerts.
        
        Returns list of alerts for nearby departments with low accountability scores.
        """
        alerts = []
        
        # First check static precincts
        for precinct in self.PRECINCT_LOCATIONS:
            distance = haversine_distance(
                latitude, longitude,
                precinct["lat"], precinct["lon"]
            )
            
            if distance <= self.ALERT_RADIUS_KM:
                # Check accountability score from database
                dept_data = await self._get_department_data(precinct["dept_id"])
                
                if dept_data and dept_data.get("accountability_score", 100) < 60:
                    alert = await self._generate_alert(
                        precinct, 
                        dept_data, 
                        distance,
                        user_id
                    )
                    alerts.append(alert)
        
        # Also check departments from database with coordinates
        db_depts = await self._get_nearby_departments(latitude, longitude)
        for dept in db_depts:
            if dept["department_id"] not in [a.get("department_id") for a in alerts]:
                alert = await self._generate_alert_from_db(dept, user_id)
                alerts.append(alert)
        
        # Sort by warning level (highest first)
        alerts.sort(key=lambda x: x.get("priority", 0), reverse=True)
        
        return alerts
    
    async def _get_department_data(self, dept_id: str) -> Optional[Dict]:
        """Get department accountability data from database"""
        try:
            dept = await db.departments.find_one(
                {"department_id": dept_id},
                {"_id": 0}
            )
            return dept
        except Exception as e:
            logger.error(f"Error fetching department data: {e}")
            return None
    
    async def _get_nearby_departments(
        self, 
        latitude: float, 
        longitude: float
    ) -> List[Dict]:
        """
        Get departments from database that are within alert radius.
        Requires departments to have lat/lon stored.
        """
        # This would use geospatial queries in production
        # For now, return empty as coordinates aren't stored
        return []
    
    async def _generate_alert(
        self,
        precinct: Dict,
        dept_data: Dict,
        distance: float,
        user_id: Optional[str]
    ) -> Dict:
        """Generate an alert for a nearby problematic precinct"""
        
        score = dept_data.get("accountability_score", 50)
        violation_count = dept_data.get("total_violations", 0)
        
        # Determine warning level based on score
        if score < 30:
            warning_level = "critical"
            priority = 4
            message = f"⚠️ HIGH ALERT: You are {distance:.1f}km from {precinct['name']}, which has a CRITICAL accountability score of {score}/100."
        elif score < 45:
            warning_level = "high"
            priority = 3
            message = f"🔴 CAUTION: You are near {precinct['name']} ({distance:.1f}km), which has {violation_count} recorded violations."
        elif score < 60:
            warning_level = "elevated"
            priority = 2
            message = f"🟡 NOTICE: {precinct['name']} is nearby ({distance:.1f}km) with an accountability score of {score}/100."
        else:
            warning_level = "normal"
            priority = 1
            message = f"📍 You are near {precinct['name']} ({distance:.1f}km)."
        
        alert = {
            "alert_id": f"loc_{precinct['dept_id']}_{datetime.now(timezone.utc).timestamp():.0f}",
            "type": "location_alert",
            "department_id": precinct["dept_id"],
            "department_name": precinct["name"],
            "state": precinct["state"],
            "distance_km": round(distance, 2),
            "accountability_score": score,
            "violation_count": violation_count,
            "warning_level": warning_level,
            "priority": priority,
            "message": message,
            "coaching_tips": self._get_coaching_tips(warning_level),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Log the alert
        if user_id:
            await self._log_alert(user_id, alert)
        
        return alert
    
    async def _generate_alert_from_db(self, dept: Dict, user_id: Optional[str]) -> Dict:
        """Generate alert from database department record"""
        score = dept.get("accountability_score", 50)
        
        if score < 30:
            warning_level = "critical"
        elif score < 45:
            warning_level = "high"
        elif score < 60:
            warning_level = "elevated"
        else:
            warning_level = "normal"
        
        return {
            "alert_id": f"loc_{dept['department_id']}_{datetime.now(timezone.utc).timestamp():.0f}",
            "type": "location_alert",
            "department_id": dept["department_id"],
            "department_name": dept.get("name", "Unknown"),
            "state": dept.get("state", ""),
            "accountability_score": score,
            "warning_level": warning_level,
            "coaching_tips": self._get_coaching_tips(warning_level),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _get_coaching_tips(self, warning_level: str) -> List[str]:
        """Get coaching tips based on warning level"""
        base_tips = [
            "Keep your phone charged and recording-ready",
            "Have emergency contacts set up in the app",
            "Know your rights before any interaction"
        ]
        
        if warning_level == "critical":
            return [
                "🚨 Enable auto-recording when starting the app",
                "📱 Share your live location with trusted contacts",
                "🎥 Consider starting 'stealth recording' mode",
                "👮 Do not consent to searches without a warrant",
                "🗣️ Invoke your right to remain silent if questioned"
            ] + base_tips
        elif warning_level == "high":
            return [
                "📱 Have the Encounter Mode ready to activate",
                "👥 Inform someone of your location",
                "📝 Note officer badge numbers if you interact",
                "🎤 Enable voice commands for hands-free control"
            ] + base_tips
        elif warning_level == "elevated":
            return [
                "📲 Keep the JUSTICE app accessible",
                "🔋 Ensure your phone is charged",
                "📍 Enable location sharing if needed"
            ] + base_tips
        else:
            return base_tips
    
    async def _log_alert(self, user_id: str, alert: Dict):
        """Log the alert for analytics"""
        try:
            await db.location_alerts.insert_one({
                "user_id": user_id,
                "alert": alert,
                "created_at": datetime.now(timezone.utc)
            })
        except Exception as e:
            logger.error(f"Error logging location alert: {e}")
    
    async def get_user_alert_history(
        self, 
        user_id: str, 
        limit: int = 20
    ) -> List[Dict]:
        """Get user's location alert history"""
        cursor = db.location_alerts.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit)
        
        return await cursor.to_list(limit)


# Singleton instance
location_alert_service = LocationAlertService()
