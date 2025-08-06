
"""
Error Handlers
Centralized error handling for the application
"""
from flask import Flask, request, jsonify
from utils.logger import setup_logger

logger = setup_logger("ErrorHandlers")


def register_error_handlers(app: Flask):
    """Register application-wide error handlers"""
    
    @app.errorhandler(404)
    def handle_not_found(error):
        logger.warning(f"404 error: {request.url}")
        return jsonify({
            'success': False,
            'error': 'not_found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        logger.error("Internal server error", error)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'An internal server error occurred'
        }), 500
    
    @app.route('/api/log-error', methods=['POST'])
    def log_frontend_error():
        """Log frontend errors for debugging"""
        try:
            error_data = request.get_json()
            if not error_data:
                return jsonify({'status': 'error', 'message': 'No error data provided'}), 400
            
            logger.error(
                f"Frontend Error: {error_data.get('message', 'Unknown error')}",
                context={
                    'frontend_error': True,
                    'level': error_data.get('level', 'ERROR'),
                    'error': error_data.get('error'),
                    'stack': error_data.get('stack'),
                    'context': error_data.get('context'),
                    'url': error_data.get('url'),
                    'userAgent': error_data.get('userAgent'),
                    'timestamp': error_data.get('timestamp')
                }
            )
            return jsonify({'status': 'logged'}), 200
            
        except Exception as e:
            logger.error("Failed to log frontend error", e)
            return jsonify({'status': 'error', 'message': 'Failed to log error'}), 500
