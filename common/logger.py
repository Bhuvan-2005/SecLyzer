"""
Centralized logging system for SecLyzer
Provides structured JSON logging with correlation IDs
"""
import logging
import json
import sys
import os
from datetime import datetime, timezone
from typing import Optional
import uuid

class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs JSON logs"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation ID if present
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
            
        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
            
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


def setup_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Set up a logger with JSON formatting
    
    Args:
        name: Logger name (usually module name)
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to env var or INFO
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Get log level from environment or parameter
    if level is None:
        level = os.getenv('SECLYZER_LOG_LEVEL', 'INFO')
    
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_correlation_id() -> str:
    """Generate a unique correlation ID for request tracing"""
    return str(uuid.uuid4())


class CorrelationLogger:
    """Logger wrapper that adds correlation IDs to all log messages"""
    
    def __init__(self, logger: logging.Logger, correlation_id: Optional[str] = None):
        self.logger = logger
        self.correlation_id = correlation_id or get_correlation_id()
    
    def _log(self, level, message, **kwargs):
        extra = {'correlation_id': self.correlation_id}
        if kwargs:
            extra['extra_data'] = kwargs
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)


# Convenience function for quick logger setup
def get_logger(name: str, correlation_id: Optional[str] = None) -> CorrelationLogger:
    """
    Get a correlation-aware logger
    
    Args:
        name: Logger name
        correlation_id: Optional correlation ID for request tracing
        
    Returns:
        CorrelationLogger instance
    """
    base_logger = setup_logger(name)
    return CorrelationLogger(base_logger, correlation_id)
