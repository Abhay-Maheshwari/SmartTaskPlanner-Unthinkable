# backend/logging_config.py

import logging
import sys
from datetime import datetime
import json

class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

def setup_logging(log_level=logging.INFO):
    """Configure application logging"""
    
    # Create logger
    logger = logging.getLogger("taskflow")
    logger.setLevel(log_level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # File handler for errors
    try:
        error_handler = logging.FileHandler("errors.log")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        logger.addHandler(error_handler)
    except Exception as e:
        # If we can't create file handler, just continue with console
        logger.warning(f"Could not create file handler: {e}")
    
    return logger

# Initialize logger
logger = setup_logging()

# Example usage functions
def log_request(method: str, path: str, status_code: int, duration: float):
    """Log HTTP request"""
    logger.info(f"Request completed", extra={
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration * 1000, 2)
    })

def log_llm_call(model: str, tokens: int, duration: float, success: bool = True):
    """Log LLM API call"""
    level = logging.INFO if success else logging.ERROR
    logger.log(level, f"LLM call {'completed' if success else 'failed'}", extra={
        "model": model,
        "tokens": tokens,
        "duration_ms": round(duration * 1000, 2),
        "success": success
    })

def log_cache_operation(operation: str, key: str, hit: bool = None):
    """Log cache operations"""
    logger.info(f"Cache {operation}", extra={
        "cache_key_hash": key[:16] + "..." if len(key) > 16 else key,
        "cache_hit": hit if hit is not None else "N/A"
    })

def log_database_operation(operation: str, table: str, duration: float, success: bool = True):
    """Log database operations"""
    level = logging.INFO if success else logging.ERROR
    logger.log(level, f"Database {operation}", extra={
        "table": table,
        "duration_ms": round(duration * 1000, 2),
        "success": success
    })