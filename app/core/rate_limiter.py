import time
import asyncio
from collections import deque
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter to respect API rate limits"""
    
    def __init__(self, rpm_limit: int = None):
        """Initialize rate limiter
        
        Args:
            rpm_limit: Requests per minute limit (default from settings)
        """
        settings = get_settings()
        self.rpm_limit = rpm_limit or settings.RATE_LIMIT_RPM
        self.window_size = 60  # 1 minute window in seconds
        self.request_timestamps = deque()
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a request, waiting if necessary"""
        if not get_settings().ENABLE_RATE_LIMITING:
            return True
            
        async with self.lock:
            current_time = time.time()
            
            # Remove timestamps outside the current window
            while self.request_timestamps and self.request_timestamps[0] < current_time - self.window_size:
                self.request_timestamps.popleft()
            
            # Check if we're at the rate limit
            if len(self.request_timestamps) >= self.rpm_limit:
                # Calculate time to wait
                oldest = self.request_timestamps[0]
                wait_time = oldest + self.window_size - current_time
                
                if wait_time > 0:
                    logger.warning(f"Rate limit reached. Waiting {wait_time:.2f} seconds")
                    await asyncio.sleep(wait_time)
                    # Recursive call after waiting
                    return await self.acquire()
            
            # Add current timestamp and grant permission
            self.request_timestamps.append(current_time)
            return True
