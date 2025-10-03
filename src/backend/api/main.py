"""
FastAPI main application for Well-Bot backend.
Provides REST API endpoints alongside the MCP tools server.
"""

import os
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import sys
from pathlib import Path

# Add the backend directory to Python path for imports
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from routes.health import router as health_router

# Load environment variables
load_dotenv()

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title="Well-Bot API",
    description="REST API for Well-Bot wellness assistant",
    version="1.0.0"
)

# Configure CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)

logger.info("FastAPI application initialized")


@app.get("/")
def root():
    """Root endpoint with basic API information."""
    return {
        "service": "Well-Bot API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/healthz",
            "readiness": "/readyz"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8080"))
    
    logger.info("Starting FastAPI server", host=host, port=port)
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
