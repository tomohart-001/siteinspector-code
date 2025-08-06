
"""
Response Service
Standardized API response formatting
"""
from typing import Dict, Any, Optional, Union, List
from utils.logger import app_logger
from .base_service import BaseService


class ResponseService(BaseService):
    """Service for standardizing API responses"""
    
    def __init__(self):
        super().__init__("ResponseService")
    
    def success(self, data: Any = None, message: str = "Success", status_code: int = 200) -> tuple[Dict[str, Any], int]:
        """Create a successful response"""
        response = {
            'success': True,
            'message': message,
            'status_code': status_code
        }
        
        if data is not None:
            if isinstance(data, dict):
                response.update(data)
            else:
                response['data'] = data
        
        return response, status_code
    
    def error(self, message: str, status_code: int = 400, error_code: str = None, details: Any = None) -> tuple[Dict[str, Any], int]:
        """Create an error response"""
        response = {
            'success': False,
            'error': message,
            'status_code': status_code
        }
        
        if error_code:
            response['error_code'] = error_code
        
        if details:
            response['details'] = details
            
        self._log_operation(f"Error response", f"{status_code}: {message}")
        return response, status_code
    
    def validation_error(self, message: str, field: str = None) -> tuple[Dict[str, Any], int]:
        """Create a validation error response"""
        details = {'field': field} if field else None
        return self.error(message, 400, 'VALIDATION_ERROR', details)
    
    def not_found(self, resource: str = "Resource") -> tuple[Dict[str, Any], int]:
        """Create a not found response"""
        return self.error(f"{resource} not found", 404, 'NOT_FOUND')
    
    def unauthorized(self, message: str = "Authentication required") -> tuple[Dict[str, Any], int]:
        """Create an unauthorized response"""
        return self.error(message, 401, 'UNAUTHORIZED')
    
    def forbidden(self, message: str = "Access denied") -> tuple[Dict[str, Any], int]:
        """Create a forbidden response"""
        return self.error(message, 403, 'FORBIDDEN')
    
    def internal_error(self, message: str = "Internal server error") -> tuple[Dict[str, Any], int]:
        """Create an internal server error response"""
        return self.error(message, 500, 'INTERNAL_ERROR')
    
    def paginated_response(self, data: List[Any], page: int, per_page: int, total: int, message: str = "Success") -> tuple[Dict[str, Any], int]:
        """Create a paginated response"""
        total_pages = (total + per_page - 1) // per_page
        
        response_data = {
            'items': data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }
        
        return self.success(response_data, message)


# Global instance
response_service = ResponseService()
