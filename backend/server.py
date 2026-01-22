"""
JUSTICE Platform - Server Entry Point (Redirect)

This file redirects to the new modular architecture in /app/backend/app/main.py
The old monolithic code has been backed up to server_backup.py

Supervisor still uses 'server:app', so we simply re-export the app from the new location.
"""
import sys
from pathlib import Path

# Ensure the backend directory is in the path
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Import and re-export the app from the modular structure
from app.main import app

# This allows: uvicorn server:app --host 0.0.0.0 --port 8001
__all__ = ["app"]
