from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.middlewares import rate_limit_middleware

# Get settings
settings = get_settings()

app = FastAPI(
    title="Gemini MCP Server",
    description="Model Context Protocol server for Google Gemini 2.5 Pro via Vertex AI",
    version="0.1.0"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.middleware("http")(rate_limit_middleware)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Include API routes
app.include_router(router)

@app.get("/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok", 
        "version": app.version,
        "model": settings.VERTEX_MODEL_NAME,
        "project": settings.GCP_PROJECT_ID,
        "region": settings.GCP_REGION,
        "rate_limit": f"{settings.RATE_LIMIT_RPM} requests per minute",
        "preferred_context_size": f"{settings.PREFERRED_CONTEXT_SIZE} tokens",
        "max_context_size": f"{settings.MAX_CONTEXT_SIZE} tokens"
    }

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting Gemini MCP Server with Vertex AI")
    logger.info(f"Model: {settings.VERTEX_MODEL_NAME}")
    logger.info(f"Project: {settings.GCP_PROJECT_ID}, Region: {settings.GCP_REGION}")
    logger.info(f"Rate limit: {settings.RATE_LIMIT_RPM} RPM")
    logger.info(f"Context window: preferred {settings.PREFERRED_CONTEXT_SIZE}, max {settings.MAX_CONTEXT_SIZE}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Gemini MCP Server")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=settings.DEBUG)
