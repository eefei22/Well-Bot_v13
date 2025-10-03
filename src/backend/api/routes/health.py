"""
Health check endpoints for Well-Bot API.
Provides liveness and readiness probes.
"""

from fastapi import APIRouter
from datetime import datetime, timezone
import structlog
import sys
from pathlib import Path

# Add the backend directory to Python path for imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from services.database import health_check as db_health

logger = structlog.get_logger()
router = APIRouter()


@router.get("/healthz")
def healthz():
    """
    Liveness probe endpoint.
    Returns basic service status without external dependencies.
    """
    return {
        "status": "ok",
        "service": "api",
        "version": "1.0.0",
        "time": datetime.now(timezone.utc).isoformat()
    }


@router.get("/readyz")
async def readyz():
    """
    Readiness probe endpoint.
    Checks database connectivity and returns detailed status.
    """
    try:
        db_status = await db_health()
        
        # Determine overall readiness based on database health
        overall_status = "ok" if db_status.get("status") == "healthy" else "error"
        
        return {
            "status": overall_status,
            "service": "api",
            "time": datetime.now(timezone.utc).isoformat(),
            "db": db_status
        }
        
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        return {
            "status": "error",
            "service": "api", 
            "time": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
            "db": {"status": "unhealthy", "message": "Health check failed"}
        }
