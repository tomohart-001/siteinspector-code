"""
Enhanced Logging System
"""
import logging
import sys
import traceback
from typing import Optional, Dict, Any
from datetime import datetime


class CustomFormatter(logging.Formatter):
    """Custom formatter with colors and better structure"""

    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }

    def format(self, record):
        # Add color to level name
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"

        # Add module context
        if hasattr(record, 'module'):
            record.module_context = f"[{record.module}]"
        else:
            record.module_context = ""

        return super().format(record)


class EnhancedLogger:
    """Enhanced logger with context and error tracking"""

    def __init__(self, name: str, level: str = 'INFO'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = CustomFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(module_context)s %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def debug(self, message: str, context: Optional[Dict[str, Any]] = None):
        self._log('DEBUG', message, context)

    def info(self, message: str, context: Optional[Dict[str, Any]] = None):
        self._log('INFO', message, context)

    def warning(self, message: str, context: Optional[Dict[str, Any]] = None, extra_context: Optional[Dict[str, Any]] = None):
        # Combine contexts if both are provided
        combined_context = context or {}
        if extra_context:
            combined_context.update(extra_context)
        self._log('WARNING', message, combined_context)

    def error(self, message: str, error: Optional[Exception] = None, context: Optional[Dict[str, Any]] = None):
        if error:
            context = context or {}
            context.update({
                'error_type': type(error).__name__,
                'error_message': str(error),
                'traceback': traceback.format_exc()
            })
        self._log('ERROR', message, context)

    def critical(self, message: str, context: Optional[Dict[str, Any]] = None):
        self._log('CRITICAL', message, context)

    def _log(self, level: str, message: str, context: Optional[Dict[str, Any]] = None):
        extra = {}
        if context:
            extra['context'] = context
            message = f"{message} | Context: {context}"

        getattr(self.logger, level.lower())(message, extra=extra)


def setup_logger(name: str, level: str = 'INFO') -> EnhancedLogger:
    """Setup enhanced logger"""
    return EnhancedLogger(name, level)


# Global application logger
app_logger = setup_logger('engineroom')