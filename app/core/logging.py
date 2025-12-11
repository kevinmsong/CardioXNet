"""Logging configuration for CardioXNet."""

import logging
import sys
from pathlib import Path
from typing import Optional
from app.core.config import get_settings


def setup_logging(log_file: Optional[str] = None) -> logging.Logger:
    """
    Configure application logging.
    
    Args:
        log_file: Optional log file path. If None, logs only to console.
        
    Returns:
        Configured logger instance
    """
    settings = get_settings()
    
    # Create logger
    logger = logging.getLogger("cardioxnet")
    logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(settings.log_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(getattr(logging, settings.log_level.upper()))
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"cardioxnet.{name}")
