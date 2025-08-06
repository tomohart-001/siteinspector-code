"""
Centralized Error Handling System
"""
from typing import Dict, Any, Optional, Tuple, List
from utils.logger import app_logger


class ErrorCategories:
    """Error category constants"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NETWORK = "network"
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    CALCULATION = "calculation"
    FILE_PROCESSING = "file_processing"
    UNKNOWN = "unknown"


class ErrorSeverity:
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorHandler:
    """Centralized error handling with categorization"""

    @staticmethod
    def handle_error(error: Exception,
                    category: str = ErrorCategories.UNKNOWN,
                    severity: str = ErrorSeverity.MEDIUM,
                    context: Optional[Dict[str, Any]] = None,
                    user_message: Optional[str] = None) -> Dict[str, Any]:
        """Handle errors with proper categorization and logging"""

        error_context = {
            'category': category,
            'severity': severity,
            'error_type': type(error).__name__,
            'error_message': str(error)
        }

        if context:
            error_context.update(context)

        # Log error based on severity
        if severity == ErrorSeverity.CRITICAL:
            app_logger.critical(f"Critical error in {category}", error, error_context)
        elif severity == ErrorSeverity.HIGH:
            app_logger.error(f"High severity error in {category}", error, error_context)
        else:
            app_logger.warning(f"Error in {category}", error, error_context)

        # Generate user-friendly response
        return {
            'success': False,
            'error': str(error),
            'category': category,
            'severity': severity,
            'user_message': user_message or ErrorHandler._get_default_user_message(category),
            'context': error_context
        }

    @staticmethod
    def _get_default_user_message(category: str) -> str:
        """Get default user message based on error category"""
        messages = {
            ErrorCategories.VALIDATION: "Please check your input and try again.",
            ErrorCategories.AUTHENTICATION: "Please log in to continue.",
            ErrorCategories.AUTHORIZATION: "You don't have permission to perform this action.",
            ErrorCategories.NETWORK: "Network error. Please check your connection and try again.",
            ErrorCategories.DATABASE: "Database error. Please try again later.",
            ErrorCategories.EXTERNAL_API: "External service error. Please try again later.",
            ErrorCategories.CALCULATION: "Calculation error. Please verify your inputs.",
            ErrorCategories.FILE_PROCESSING: "File processing error. Please check your file and try again.",
            ErrorCategories.UNKNOWN: "An unexpected error occurred. Please try again."
        }
        return messages.get(category, messages[ErrorCategories.UNKNOWN])

    @staticmethod
    def handle_validation_error(message: str, field: Optional[str] = None) -> Tuple[Dict[str, Any], int]:
        """Handle validation errors specifically"""
        response = {
            'success': False,
            'error': 'validation_error',
            'message': message,
            'user_message': message
        }

        if field:
            response['field'] = field

        app_logger.warning(f"Validation error: {message}", context={'field': field})
        return response, 400

    @staticmethod
    def handle_buildable_area_error(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle buildable area calculation errors"""
        return ErrorHandler.handle_error(
            error,
            category=ErrorCategories.CALCULATION,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            user_message="Failed to calculate buildable area. Please verify your site data and try again."
        )

    @staticmethod
    def handle_site_data_error(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle site data errors"""
        return ErrorHandler.handle_error(
            error,
            category=ErrorCategories.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            user_message="Site data validation failed. Please check your site selection and try again."
        )

    @staticmethod
    def handle_edge_classification_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle edge classification errors"""
        return ErrorHandler.handle_error(
            error,
            category=ErrorCategories.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            user_message="Edge classification failed. Please check your inputs and try again."
        )

    @staticmethod
    def create_success_response(data: Dict[str, Any], message: str = "Operation completed successfully") -> Dict[str, Any]:
        """Create a success response"""
        return {
            'success': True,
            'data': data,
            'message': message
        }

    @staticmethod
    def log_user_action(action: str, success: bool, details: Dict[str, Any] = None):
        """Log user actions for analytics"""
        log_data = {
            'action': action,
            'success': success,
            'details': details or {}
        }
        
        if success:
            app_logger.info(f"User action: {action}", context=log_data)
        else:
            app_logger.warning(f"Failed user action: {action}", context=log_data)


class ValidationError(Exception):
    """Custom validation exception"""
    pass


class AuthenticationError(Exception):
    """Custom authentication exception"""
    pass


class CalculationError(Exception):
    """Custom calculation exception"""
    pass


class SiteInspectorError(Exception):
    """Custom site inspector exception"""
    pass


class GeometryError(Exception):
    """Custom geometry exception"""
    pass


def safe_execute(func, *args, error_handler=None, context=None, **kwargs):
    """Safely execute a function with error handling"""
    try:
        result = func(*args, **kwargs)
        return result, None
    except Exception as error:
        if error_handler:
            return None, error_handler(error, context)
        else:
            return None, ErrorHandler.handle_error(error)


def validate_request_data(data: Dict, required_fields: List[str]) -> Optional[ValidationError]:
    """Validate request data has required fields"""
    if not data:
        return ValidationError("Request data is required")

    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

    return None