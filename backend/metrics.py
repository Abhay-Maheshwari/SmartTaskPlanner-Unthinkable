# backend/metrics.py

from collections import defaultdict
from datetime import datetime
from typing import Dict, List

class MetricsCollector:
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_duration = 0.0
        self.endpoint_stats = defaultdict(lambda: {"count": 0, "total_duration": 0.0})
        self.llm_calls = 0
        self.llm_tokens = 0
        self.cache_hits = 0
        self.cache_misses = 0
    
    def record_request(self, endpoint: str, duration: float, status_code: int):
        """Record a request"""
        self.request_count += 1
        self.total_duration += duration
        
        self.endpoint_stats[endpoint]["count"] += 1
        self.endpoint_stats[endpoint]["total_duration"] += duration
        
        if status_code >= 400:
            self.error_count += 1
    
    def record_llm_call(self, tokens: int = 0):
        """Record an LLM API call"""
        self.llm_calls += 1
        self.llm_tokens += tokens
    
    def record_cache_hit(self):
        """Record a cache hit"""
        self.cache_hits += 1
    
    def record_cache_miss(self):
        """Record a cache miss"""
        self.cache_misses += 1
    
    def get_stats(self) -> Dict:
        """Get current statistics"""
        avg_duration = self.total_duration / self.request_count if self.request_count > 0 else 0
        error_rate = self.error_count / self.request_count if self.request_count > 0 else 0
        cache_hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        
        return {
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": round(error_rate * 100, 2),
            "avg_response_time_ms": round(avg_duration * 1000, 2),
            "llm_calls": self.llm_calls,
            "llm_tokens_used": self.llm_tokens,
            "cache_hit_rate": round(cache_hit_rate * 100, 2),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "endpoint_stats": dict(self.endpoint_stats)
        }
    
    def reset(self):
        """Reset all metrics"""
        self.__init__()

# Global metrics instance
metrics = MetricsCollector()