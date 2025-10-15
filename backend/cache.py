# backend/cache.py

from functools import lru_cache
import hashlib
import json
from typing import Optional, Dict

# Simple in-memory cache
_plan_cache: Dict[str, Dict] = {}

def get_cache_key(goal: str, timeframe: Optional[str], start_date: Optional[str]) -> str:
    """Generate cache key from request parameters"""
    cache_str = f"{goal}:{timeframe}:{start_date}"
    return hashlib.md5(cache_str.encode()).hexdigest()

def get_cached_plan(goal: str, timeframe: Optional[str], start_date: Optional[str]) -> Optional[Dict]:
    """Get cached plan if available"""
    key = get_cache_key(goal, timeframe, start_date)
    return _plan_cache.get(key)

def cache_plan(goal: str, timeframe: Optional[str], start_date: Optional[str], plan_data: Dict):
    """Cache a generated plan"""
    key = get_cache_key(goal, timeframe, start_date)
    _plan_cache[key] = plan_data
    
    # Limit cache size
    if len(_plan_cache) > 100:
        # Remove oldest entry (simple FIFO)
        first_key = next(iter(_plan_cache))
        del _plan_cache[first_key]

def clear_cache():
    """Clear all cached plans"""
    _plan_cache.clear()

def get_cache_stats() -> Dict:
    """Get cache statistics"""
    return {
        "cached_plans": len(_plan_cache),
        "max_cache_size": 100
    }