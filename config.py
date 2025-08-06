
import os

class Config:
    # Existing configuration...
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'"
    }
    
    # Session Security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Environment variables
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')



"""
Centralized Configuration Management
"""
import os
from typing import Optional, Dict, Any
from utils.logger import app_logger


class ConfigValidator:
    """Configuration validation utilities"""
    
    @staticmethod
    def validate_required_env_vars(required_vars: Dict[str, str]) -> bool:
        """Validate required environment variables exist"""
        missing_vars = []
        for var_name, description in required_vars.items():
            if not os.getenv(var_name):
                missing_vars.append(f"{var_name} ({description})")
        
        if missing_vars:
            app_logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            return False
        return True


class Config:
    """Application configuration with validation"""
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
    
    # API Keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///engineroom.db')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO' if not DEBUG else 'DEBUG')
    
    # External APIs
    NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
    OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
    
    # Application Settings
    MAX_CONVERSATIONS_PER_USER = 2
    SESSION_TIMEOUT_HOURS = 24
    
    # File Upload
    MAX_FILE_SIZE_MB = 10
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'dwg'}
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate critical configuration"""
        required_vars = {
            'OPENAI_API_KEY': 'OpenAI API key for AI functionality'
        }
        
        if not ConfigValidator.validate_required_env_vars(required_vars):
            return False
            
        # Additional validation
        if len(cls.SECRET_KEY) < 16:
            app_logger.warning("SECRET_KEY is too short for production use")
            
        return True
    
    @classmethod
    def get_config_summary(cls) -> Dict[str, Any]:
        """Get configuration summary for logging"""
        return {
            'environment': cls.ENVIRONMENT,
            'debug': cls.DEBUG,
            'log_level': cls.LOG_LEVEL,
            'max_conversations': cls.MAX_CONVERSATIONS_PER_USER,
            'database_type': 'sqlite' if 'sqlite' in cls.DATABASE_URL else 'other'
        }
