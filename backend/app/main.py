"""
JUSTICE Platform - Main Application Entry Point (Refactored)

This is the new modular entry point for the JUSTICE API.
It uses the organized router structure from /app/backend/app/

To use this instead of server.py, update the supervisor config to point here.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

# Import routers
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.cases import router as cases_router
from app.routers.evidence import router as evidence_router
from app.routers.analytics import router as analytics_router
from app.routers.sos import router as sos_router
from app.routers.attorneys import router as attorneys_router
from app.routers.ai_chat import router as ai_chat_router
from app.routers.encounters import router as encounters_router
from app.routers.community import router as community_router
from app.routers.rights import router as rights_router

# Import config
from app.core.config import IPFS_ENABLED, S3_ENABLED, UPLOADS_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown events"""
    # Startup
    print("🚀 JUSTICE Platform Starting (Modular Architecture v5.2)...")
    print(f"   IPFS Enabled: {IPFS_ENABLED}")
    print(f"   S3 Enabled: {S3_ENABLED}")
    yield
    # Shutdown
    print("👋 JUSTICE Platform Shutting down...")


# Create FastAPI application
app = FastAPI(
    title="JUSTICE API",
    description="Civil Rights Defense System - Protecting citizens during police encounters",
    version="5.2.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploads
app.mount("/api/files", StaticFiles(directory=str(UPLOADS_DIR)), name="files")

# Include routers with /api prefix
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(cases_router, prefix="/api")
app.include_router(evidence_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(sos_router, prefix="/api")
app.include_router(attorneys_router, prefix="/api")
app.include_router(ai_chat_router, prefix="/api")
app.include_router(encounters_router, prefix="/api")
app.include_router(community_router, prefix="/api")
app.include_router(rights_router, prefix="/api")


# Root endpoint
@app.get("/")
async def root():
    return {
        "name": "JUSTICE API",
        "version": "5.2.0",
        "status": "operational",
        "docs": "/docs"
    }


# For running with uvicorn directly (development)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
