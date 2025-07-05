"""
Production-safe error handlers
"""
from flask import jsonify, current_app
from werkzeug.exceptions import HTTPException
import traceback
from utils.logger import get_logger

logger = get_logger(__name__)

def init_error_handlers(app):
    """Initialize error handlers for the Flask app"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 'Bad Request',
            'message': 'The request could not be understood or was missing required parameters.'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'error': 'Unauthorized',
            'message': 'Authentication is required to access this resource.'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'error': 'Forbidden',
            'message': 'You do not have permission to access this resource.'
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'message': 'The requested resource could not be found.'
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'success': False,
            'error': 'Method Not Allowed',
            'message': 'The method is not allowed for the requested URL.'
        }), 405
    
    @app.errorhandler(429)
    def too_many_requests(error):
        return jsonify({
            'success': False,
            'error': 'Too Many Requests',
            'message': 'Rate limit exceeded. Please try again later.'
        }), 429
    
    @app.errorhandler(500)
    def internal_server_error(error):
        # Log the full error for debugging
        logger.error(f"Internal server error: {str(error)}", exc_info=True)
        
        # Return generic message in production
        if current_app.config.get('ENV') == 'production':
            return jsonify({
                'success': False,
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred. Please try again later.'
            }), 500
        else:
            # In development, include more details
            return jsonify({
                'success': False,
                'error': 'Internal Server Error',
                'message': str(error),
                'traceback': traceback.format_exc() if current_app.debug else None
            }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle all HTTP exceptions"""
        response = {
            'success': False,
            'error': error.name,
            'message': error.description
        }
        return jsonify(response), error.code
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle all unexpected exceptions"""
        # Log the full error
        logger.error(f"Unexpected error: {str(error)}", exc_info=True)
        
        # Production: generic message
        if current_app.config.get('ENV') == 'production':
            return jsonify({
                'success': False,
                'error': 'Server Error',
                'message': 'An unexpected error occurred. Our team has been notified.'
            }), 500
        else:
            # Development: include error details
            return jsonify({
                'success': False,
                'error': type(error).__name__,
                'message': str(error),
                'traceback': traceback.format_exc() if current_app.debug else None
            }), 500

def sanitize_error_message(message):
    """Remove sensitive information from error messages"""
    # List of patterns that might contain sensitive info
    sensitive_patterns = [
        'password',
        'api_key',
        'api_secret',
        'secret',
        'token',
        'credential',
        'database',
        'postgresql://',
        'mysql://',
        'mongodb://',
    ]
    
    message_lower = message.lower()
    for pattern in sensitive_patterns:
        if pattern in message_lower:
            return "An error occurred while processing your request."
    
    return message