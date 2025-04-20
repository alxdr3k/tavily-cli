"""Logging configuration for the Tavily CLI."""

import logging
import os
import sys
from typing import Optional


class ColorFormatter(logging.Formatter):
    """Logging formatter with colored output for terminal."""

    COLORS = {
        'DEBUG': '\033[94m',  # Blue
        'INFO': '\033[92m',   # Green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',  # Red
        'CRITICAL': '\033[91;1m',  # Bold Red
        'RESET': '\033[0m',  # Reset
    }

    def __init__(self, fmt: Optional[str] = None, use_colors: bool = True):
        """Initialize the formatter with optional color support."""
        super().__init__(fmt)
        self.use_colors = use_colors and sys.stdout.isatty()

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with optional coloring."""
        log_message = super().format(record)
        if self.use_colors:
            level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            return f"{level_color}{log_message}{self.COLORS['RESET']}"
        return log_message


def setup_logger(name: str = "tavily_cli") -> logging.Logger:
    """Configure and return a logger with the specified name.

    Args:
        name: The name of the logger to configure

    Returns:
        A configured logger instance
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:  # Only add handlers if they don't exist
        logger.setLevel(logging.INFO)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Determine if colors should be used
        use_colors = os.environ.get("NO_COLOR") is None
        
        # Create formatter
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        formatter = ColorFormatter(log_format, use_colors=use_colors)
        
        # Add formatter to handler
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
    
    return logger


# Default logger instance
logger = setup_logger()

