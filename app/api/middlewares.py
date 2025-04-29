from fastapi import Request
import time
import logging
import asyncio
from app.core.config import get_settings
from app.core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)
rate_limiter = RateLimiter()

async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to all API requests"""
    settings = get_settings()
    
    if settings.ENABLE_RATE_LIMITING and '/v1/' in request.url.path:
        await rate_limiter.acquire()
        
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Add processing time header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response
