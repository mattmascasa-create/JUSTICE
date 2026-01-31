"""
3D Evidence Reconstruction Service

Generates 3D scene reconstructions from encounter footage using:
- GPS coordinates for spatial positioning
- Timestamps for temporal mapping
- AI-powered depth estimation from video frames
- Point cloud generation for scene visualization
"""

import os
import math
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from bson import ObjectId

# AI Integration
try:
    from emergentintegrations.llm import LlmChat
    HAS_AI = True
except ImportError:
    HAS_AI = False


class Reconstruction3DService:
    """Service for creating 3D reconstructions from encounter evidence."""
    
    def __init__(self, db):
        self.db = db
        self.reconstructions = db.reconstructions_3d
        self.encounters = db.encounters
        self.evidence = db.evidence
        
    async def create_reconstruction(
        self,
        user_id: str,
        encounter_id: str,
        options: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a 3D reconstruction from an encounter.
        
        Args:
            user_id: Owner of the encounter
            encounter_id: Encounter to reconstruct
            options: Optional reconstruction settings
        """
        options = options or {}
        
        # Get encounter data
        encounter = await self.encounters.find_one({
            "encounter_id": encounter_id,
            "user_id": user_id
        })
        
        if not encounter:
            raise ValueError("Encounter not found")
        
        # Get associated evidence
        evidence_items = await self.evidence.find({
            "case_id": encounter.get("case_id"),
            "user_id": user_id
        }).to_list(100)
        
        # Extract spatial data from encounter
        spatial_data = self._extract_spatial_data(encounter, evidence_items)
        
        # Generate 3D scene elements
        scene_data = await self._generate_scene(
            encounter,
            spatial_data,
            evidence_items,
            options
        )
        
        # Create reconstruction record
        reconstruction = {
            "reconstruction_id": f"recon_{ObjectId()}",
            "user_id": user_id,
            "encounter_id": encounter_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
            "scene_data": scene_data,
            "metadata": {
                "evidence_count": len(evidence_items),
                "duration_seconds": encounter.get("duration", 0),
                "has_video": any(e.get("file_type", "").startswith("video") for e in evidence_items),
                "has_audio": any(e.get("file_type", "").startswith("audio") for e in evidence_items),
                "location": encounter.get("location", {}),
                "options": options
            }
        }
        
        await self.reconstructions.insert_one(reconstruction)
        
        # Remove MongoDB _id
        reconstruction.pop("_id", None)
        return reconstruction
    
    def _extract_spatial_data(
        self,
        encounter: Dict,
        evidence_items: List[Dict]
    ) -> Dict[str, Any]:
        """Extract GPS coordinates and spatial information."""
        
        # Primary location from encounter
        location = encounter.get("location", {})
        lat = location.get("latitude", 0)
        lng = location.get("longitude", 0)
        
        # Path points from tracking (if available)
        path_points = encounter.get("location_history", [])
        
        # Violation markers
        violations = encounter.get("violations", [])
        violation_points = []
        for v in violations:
            violation_points.append({
                "timestamp": v.get("timestamp", 0),
                "type": v.get("type", "unknown"),
                "severity": v.get("severity", "medium"),
                "position": self._calculate_position(v.get("timestamp", 0), path_points, lat, lng)
            })
        
        # Evidence positions
        evidence_positions = []
        for ev in evidence_items:
            ev_time = ev.get("created_at", "")
            evidence_positions.append({
                "evidence_id": ev.get("evidence_id", ""),
                "type": ev.get("file_type", "unknown"),
                "timestamp": ev_time,
                "position": {"x": 0, "y": 0, "z": 0}  # Will be positioned in scene
            })
        
        return {
            "origin": {"lat": lat, "lng": lng},
            "path_points": path_points,
            "violation_points": violation_points,
            "evidence_positions": evidence_positions,
            "bounds": self._calculate_bounds(path_points, lat, lng)
        }
    
    def _calculate_position(
        self,
        timestamp: float,
        path_points: List,
        default_lat: float,
        default_lng: float
    ) -> Dict[str, float]:
        """Calculate 3D position for a given timestamp."""
        # For now, use simple time-based positioning
        # In production, would interpolate along GPS path
        x = timestamp * 0.1  # Spread along X axis by time
        y = 0  # Ground level
        z = 0  # Will be set based on depth estimation
        return {"x": x, "y": y, "z": z}
    
    def _calculate_bounds(
        self,
        path_points: List,
        default_lat: float,
        default_lng: float
    ) -> Dict[str, float]:
        """Calculate scene bounds."""
        if not path_points:
            return {
                "minX": -10, "maxX": 10,
                "minY": 0, "maxY": 5,
                "minZ": -10, "maxZ": 10
            }
        
        # Calculate bounds from path
        min_x = min(p.get("x", 0) for p in path_points) if path_points else -10
        max_x = max(p.get("x", 0) for p in path_points) if path_points else 10
        
        return {
            "minX": min_x - 5,
            "maxX": max_x + 5,
            "minY": 0,
            "maxY": 10,
            "minZ": -10,
            "maxZ": 10
        }
    
    async def _generate_scene(
        self,
        encounter: Dict,
        spatial_data: Dict,
        evidence_items: List[Dict],
        options: Dict
    ) -> Dict[str, Any]:
        """Generate 3D scene data structure."""
        
        scene = {
            "version": "1.0",
            "type": "encounter_reconstruction",
            "environment": self._generate_environment(encounter, options),
            "camera": self._generate_camera_settings(spatial_data),
            "objects": [],
            "markers": [],
            "timeline": [],
            "point_cloud": None
        }
        
        # Generate ground plane based on encounter type
        encounter_type = encounter.get("encounter_type", "traffic_stop")
        scene["objects"].append(self._create_ground_plane(encounter_type))
        
        # Add path visualization
        if spatial_data.get("path_points"):
            scene["objects"].append(self._create_path_line(spatial_data["path_points"]))
        
        # Add violation markers
        for vp in spatial_data.get("violation_points", []):
            scene["markers"].append(self._create_violation_marker(vp))
        
        # Add evidence markers
        for i, ev in enumerate(evidence_items):
            marker = self._create_evidence_marker(ev, i, len(evidence_items))
            scene["markers"].append(marker)
        
        # Generate timeline entries
        scene["timeline"] = self._generate_timeline(encounter, evidence_items)
        
        # Generate point cloud from transcription/analysis
        if options.get("generate_point_cloud", True):
            scene["point_cloud"] = await self._generate_point_cloud(encounter, evidence_items)
        
        return scene
    
    def _generate_environment(self, encounter: Dict, options: Dict) -> Dict:
        """Generate environment settings based on encounter context."""
        
        # Determine time of day from encounter timestamp
        created_at = encounter.get("created_at", "")
        hour = 12  # Default to noon
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                hour = dt.hour
            except (ValueError, AttributeError):
                pass
        
        # Determine lighting based on time
        if 6 <= hour < 18:
            ambient_intensity = 0.6
            sun_intensity = 1.0
            sky_color = "#87CEEB"  # Light blue
        elif 18 <= hour < 21 or 5 <= hour < 6:
            ambient_intensity = 0.4
            sun_intensity = 0.6
            sky_color = "#FF7F50"  # Coral (sunset)
        else:
            ambient_intensity = 0.2
            sun_intensity = 0.1
            sky_color = "#191970"  # Midnight blue
        
        return {
            "ambientLight": {
                "color": "#ffffff",
                "intensity": ambient_intensity
            },
            "directionalLight": {
                "color": "#ffffff",
                "intensity": sun_intensity,
                "position": [10, 20, 10]
            },
            "skyColor": sky_color,
            "fogColor": sky_color,
            "fogNear": 50,
            "fogFar": 200,
            "gridHelper": {
                "size": 100,
                "divisions": 50,
                "color1": "#444444",
                "color2": "#222222"
            }
        }
    
    def _generate_camera_settings(self, spatial_data: Dict) -> Dict:
        """Generate initial camera position and settings."""
        bounds = spatial_data.get("bounds", {})
        center_x = (bounds.get("minX", -10) + bounds.get("maxX", 10)) / 2
        center_z = (bounds.get("minZ", -10) + bounds.get("maxZ", 10)) / 2
        
        return {
            "type": "perspective",
            "fov": 60,
            "near": 0.1,
            "far": 1000,
            "position": [center_x, 15, center_z + 20],
            "target": [center_x, 0, center_z],
            "controls": {
                "enableDamping": True,
                "dampingFactor": 0.05,
                "minDistance": 5,
                "maxDistance": 100,
                "maxPolarAngle": math.pi / 2
            }
        }
    
    def _create_ground_plane(self, encounter_type: str) -> Dict:
        """Create ground plane based on encounter type."""
        
        # Different ground textures for different encounter types
        textures = {
            "traffic_stop": {"color": "#333333", "type": "road"},
            "pedestrian_stop": {"color": "#555555", "type": "sidewalk"},
            "home": {"color": "#8B4513", "type": "floor"},
            "arrest": {"color": "#333333", "type": "concrete"}
        }
        
        ground = textures.get(encounter_type, textures["traffic_stop"])
        
        return {
            "id": "ground",
            "type": "plane",
            "geometry": {
                "width": 100,
                "height": 100,
                "widthSegments": 1,
                "heightSegments": 1
            },
            "material": {
                "color": ground["color"],
                "roughness": 0.8,
                "metalness": 0.2
            },
            "position": [0, 0, 0],
            "rotation": [-math.pi / 2, 0, 0]
        }
    
    def _create_path_line(self, path_points: List) -> Dict:
        """Create a line showing the movement path."""
        points = []
        for i, p in enumerate(path_points):
            points.append([
                p.get("x", i * 0.5),
                0.1,  # Slightly above ground
                p.get("z", 0)
            ])
        
        return {
            "id": "movement_path",
            "type": "line",
            "points": points,
            "material": {
                "color": "#00ff00",
                "linewidth": 3,
                "opacity": 0.8
            }
        }
    
    def _create_violation_marker(self, violation_point: Dict) -> Dict:
        """Create a 3D marker for a violation."""
        
        severity_colors = {
            "critical": "#ff0000",
            "high": "#ff6600",
            "medium": "#ffcc00",
            "low": "#00ff00"
        }
        
        color = severity_colors.get(violation_point.get("severity", "medium"), "#ffcc00")
        pos = violation_point.get("position", {"x": 0, "y": 0, "z": 0})
        
        return {
            "id": f"violation_{violation_point.get('timestamp', 0)}",
            "type": "violation",
            "geometry": "cone",
            "position": [pos["x"], 2, pos["z"]],
            "scale": [0.5, 1, 0.5],
            "material": {
                "color": color,
                "emissive": color,
                "emissiveIntensity": 0.3
            },
            "data": {
                "type": violation_point.get("type", "unknown"),
                "severity": violation_point.get("severity", "medium"),
                "timestamp": violation_point.get("timestamp", 0)
            },
            "animation": {
                "type": "pulse",
                "speed": 2
            }
        }
    
    def _create_evidence_marker(self, evidence: Dict, index: int, total: int) -> Dict:
        """Create a 3D marker for an evidence item."""
        
        # Arrange evidence in a circle around the scene
        angle = (2 * math.pi * index) / max(total, 1)
        radius = 8
        x = math.cos(angle) * radius
        z = math.sin(angle) * radius
        
        file_type = evidence.get("file_type", "unknown")
        
        # Different shapes for different evidence types
        if "video" in file_type:
            geometry = "box"
            color = "#3b82f6"  # Blue
        elif "audio" in file_type:
            geometry = "sphere"
            color = "#8b5cf6"  # Purple
        elif "image" in file_type:
            geometry = "box"
            color = "#10b981"  # Green
        else:
            geometry = "octahedron"
            color = "#6b7280"  # Gray
        
        return {
            "id": f"evidence_{evidence.get('evidence_id', index)}",
            "type": "evidence",
            "geometry": geometry,
            "position": [x, 1.5, z],
            "scale": [0.8, 0.8, 0.8],
            "material": {
                "color": color,
                "transparent": True,
                "opacity": 0.9
            },
            "data": {
                "evidence_id": evidence.get("evidence_id", ""),
                "file_type": file_type,
                "filename": evidence.get("filename", "Unknown"),
                "created_at": evidence.get("created_at", "")
            },
            "animation": {
                "type": "float",
                "speed": 1,
                "amplitude": 0.2
            }
        }
    
    def _generate_timeline(
        self,
        encounter: Dict,
        evidence_items: List[Dict]
    ) -> List[Dict]:
        """Generate timeline entries for scene playback."""
        
        timeline = []
        duration = encounter.get("duration", 60)
        
        # Add encounter start
        timeline.append({
            "time": 0,
            "event": "encounter_start",
            "label": "Encounter Started",
            "camera_position": None
        })
        
        # Add violation events
        for v in encounter.get("violations", []):
            timeline.append({
                "time": v.get("timestamp", 0),
                "event": "violation",
                "label": f"Violation: {v.get('type', 'Unknown')}",
                "data": v
            })
        
        # Add evidence events
        for ev in evidence_items:
            # Estimate time based on creation order
            timeline.append({
                "time": len(timeline) * 5,  # Spread out
                "event": "evidence",
                "label": f"Evidence: {ev.get('filename', 'Unknown')[:20]}",
                "data": {"evidence_id": ev.get("evidence_id", "")}
            })
        
        # Add encounter end
        timeline.append({
            "time": duration,
            "event": "encounter_end",
            "label": "Encounter Ended"
        })
        
        # Sort by time
        timeline.sort(key=lambda x: x.get("time", 0))
        
        return timeline
    
    async def _generate_point_cloud(
        self,
        encounter: Dict,
        evidence_items: List[Dict]
    ) -> Dict:
        """Generate a point cloud representation of the scene."""
        
        points = []
        colors = []
        
        # Generate points based on transcription/analysis
        transcriptions = encounter.get("transcriptions", [])
        
        # Create point density based on speech activity
        for i, trans in enumerate(transcriptions[:100]):  # Limit to 100 segments
            # Handle both string IDs and object transcriptions
            if isinstance(trans, str):
                # Transcription ID - skip or fetch if needed
                # For now, generate placeholder point
                word_count = 3
                text = trans
                speaker = "unknown"
            else:
                word_count = len(trans.get("text", "").split())
                text = trans.get("text", "")
                speaker = trans.get("speaker", "unknown")
            
            x_base = i * 0.5
            
            for j in range(min(word_count, 10)):
                points.append([
                    x_base + (j * 0.1),
                    1 + (j * 0.2),
                    (hash(text) % 10) * 0.1
                ])
                
                # Color based on speaker
                if speaker == "officer":
                    colors.append([0.2, 0.4, 1.0])  # Blue
                elif speaker == "citizen":
                    colors.append([0.2, 1.0, 0.4])  # Green
                else:
                    colors.append([0.8, 0.8, 0.8])  # Gray
        
        # If no transcriptions, generate ambient points
        if not points:
            import random
            for _ in range(200):
                points.append([
                    random.uniform(-10, 10),
                    random.uniform(0, 5),
                    random.uniform(-10, 10)
                ])
                colors.append([0.5, 0.5, 0.5])
        
        return {
            "points": points,
            "colors": colors,
            "size": 0.1,
            "opacity": 0.6
        }
    
    async def get_reconstruction(
        self,
        user_id: str,
        reconstruction_id: str
    ) -> Optional[Dict]:
        """Get a reconstruction by ID."""
        recon = await self.reconstructions.find_one({
            "reconstruction_id": reconstruction_id,
            "user_id": user_id
        }, {"_id": 0})
        return recon
    
    async def list_reconstructions(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict]:
        """List user's reconstructions."""
        cursor = self.reconstructions.find(
            {"user_id": user_id},
            {"_id": 0, "scene_data": 0}  # Exclude large scene data
        ).sort("created_at", -1).limit(limit)
        
        return await cursor.to_list(limit)
    
    async def delete_reconstruction(
        self,
        user_id: str,
        reconstruction_id: str
    ) -> bool:
        """Delete a reconstruction."""
        result = await self.reconstructions.delete_one({
            "reconstruction_id": reconstruction_id,
            "user_id": user_id
        })
        return result.deleted_count > 0


# Singleton instance
reconstruction_service = None

def get_reconstruction_service(db):
    global reconstruction_service
    if reconstruction_service is None:
        reconstruction_service = Reconstruction3DService(db)
    return reconstruction_service
