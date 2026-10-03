"""
NyayGuru AI Pro - Main FastAPI Application
Production-grade AI Legal Assistant for Indian Law.
"""

import os
# CRITICAL: Force CPU-only mode and limit threads
os.environ['OMP_NUM_THREADS'] = '4'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys

from app.config import settings
from app.database import init_db
from app.routes import chat, statutes, documents, cases, booking, stats
# Import models to ensure they are registered with SQLAlchemy
from app.models import Booking  # noqa: F401

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting NyayGuru AI Pro (LIGHT STARTUP)...")
    
    # Initialize database explicitly so tables are created on Render start
    init_db()
    
    # AI Services initialized lazily on first request to avoid port timeout.
    
    logger.info("NyayGuru AI Pro ready for traffic!")
    
    yield
    
    logger.info("Shutting down NyayGuru AI Pro...")


# Create FastAPI app
app = FastAPI(
    title="NYAYASHASTRA",
    description="""
    🏛️ **NYAYASHASTRA - AI-Powered Legal Helper for India**
    
    A production-grade, multi-agent RAG system for delivering precise, 
    verifiable, bilingual (English + Hindi) legal answers related to:
    
    - **Indian Penal Code (IPC)**
    - **Bhartiya Nyaya Sanhita (BNS)**
    - **Indian Regulatory Statutes**
    
    ## Features
    
    - 🤖 **Multi-Agent Intelligence**: 7 specialized AI agents working in orchestration
    - ⚖️ **IPC ↔ BNS Mapping**: Automatic cross-referencing between old and new laws
    - 🌐 **Bilingual Support**: Full English and Hindi language support
    - 📚 **Verified Citations**: Links to official government gazettes only
    - 📄 **Document Analysis**: Upload and summarize court orders & judgments
    - 🏛️ **Case Law Intelligence**: Supreme Court and High Court judgment retrieval
    
    ## Disclaimer
    
    This service is for informational purposes only and does not constitute legal advice.
    Please consult a qualified legal professional for specific legal matters.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS - Allow all origins in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.api_debug else "An unexpected error occurred"
        }
    )


# Include routers
app.include_router(chat.router)
app.include_router(statutes.router)
app.include_router(documents.router)
app.include_router(cases.router)
app.include_router(booking.router)
app.include_router(stats.router)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    from app.services.llm_service import get_llm_service
    llm_service = await get_llm_service()
    
    return {
        "status": "healthy",
        "service": "NYAYASHASTRA",
        "version": "1.0.0",
        "components": {
            "database": "ok",
            "vector_store": "ok",
            "llm": llm_service.get_status()
        }
    }


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "NYAYASHASTRA",
        "tagline": "AI-Powered Legal Helper for India",

        "version": "1.0.0",
        "description": "Multi-agent RAG system for Indian law",
        "features": [
            "IPC & BNS Section Lookup",
            "IPC ↔ BNS Cross-Mapping",
            "Case Law Intelligence",
            "Document Summarization",
            "Bilingual Support (English + Hindi)",
            "Verified Citations"
        ],
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "chat": "/api/chat",
            "statutes": "/api/statutes",
            "documents": "/api/documents"
        }
    }


# Agent info endpoint
@app.get("/api/agents", tags=["agents"])
async def get_all_agents():
    """Get information about all AI agents in the pipeline."""
    from app.agents.orchestrator import get_orchestrator
    orchestrator = get_orchestrator()
    return {
        "agents": orchestrator.get_agent_info(),
        "pipeline_order": [
            "query",
            "statute", 
            "case",
            "regulatory",
            "citation",
            "summary",
            "response"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
        workers=1,  # MEMORY-SAFE: Single worker only
        log_level="info"
    )

# Reload: 2026-01-20 03:42:23.842445