# backend/middleware.py

import time
import logging
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
from metrics import metrics

logger = logging.getLogger(__name__)

class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Start timer
        start_time = time.time()
        
        # Log request
        logger.info(f"→ {request.method} {request.url.path}")
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            metrics.record_request(request.url.path, duration, response.status_code)
            
            # Log response
            logger.info(f"← {request.method} {request.url.path} - {response.status_code} ({duration:.2f}s)")
            
            # Add custom headers
            response.headers["X-Process-Time"] = str(duration)
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(f"ERROR: {request.method} {request.url.path} - ERROR ({duration:.2f}s): {e}")
            metrics.record_request(request.url.path, duration, 500)
            raise

# Simple in-memory rate limiter
request_counts = defaultdict(list)

def check_rate_limit(client_id: str, max_requests: int = 10, window_minutes: int = 1) -> bool:
    """Check if client has exceeded rate limit"""
    now = datetime.now()
    window_start = now - timedelta(minutes=window_minutes)
    
    # Clean old requests
    request_counts[client_id] = [
        req_time for req_time in request_counts[client_id]
        if req_time > window_start
    ]
    
    # Check limit
    if len(request_counts[client_id]) >= max_requests:
        return False
    
    # Add current request
    request_counts[client_id].append(now)
    return True

def rate_limit_check(client_id: str = "default", max_requests: int = 10) -> None:
    """Rate limiting decorator function"""
    if not check_rate_limit(client_id, max_requests=max_requests, window_minutes=1):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later."
        )