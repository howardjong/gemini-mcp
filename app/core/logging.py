import logging
import sys
import json
from datetime import datetime
import os

# Try to import jsonlogger, but don't fail if it's not available
try:
    from pythonjsonlogger import jsonlogger
    has_jsonlogger = True
except ImportError:
    has_jsonlogger = False

from app.core.config import get_settings

settings = get_settings()

if has_jsonlogger:
    class CustomJsonFormatter(jsonlogger.JsonFormatter):
        def add_fields(self, log_record, record, message_dict):
            super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
            log_record['timestamp'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['level'] = record.levelname
            log_record['module'] = record.module
            log_record['app'] = settings.APP_NAME

def setup_logging():
    """Setup application logging"""
    log_level = getattr(logging, settings.LOG_LEVEL)
    
    # Remove all handlers associated with the root logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set formatter for handlers
    if has_jsonlogger:
        formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
        
        # Apply formatter to all handlers
        for handler in logging.root.handlers:
            handler.setFormatter(formatter)
    
    # Set log levels for some noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
