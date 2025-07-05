"""
Custom exception classes and error handling utilities
"""
import logging
from functools import wraps
from flask import jsonify, request
import time
import traceback

# Custom Exception Classes
class CryptoPortfolioException(Exception):
    """Base exception for crypto portfolio application"""
    def __init__(self, message, error_code=None, status_code=500):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

class ExchangeConnectionError(CryptoPortfolioException):
    """Exception for exchange connection issues"""
    def __init__(self, exchange_name, message="Exchange connection failed"):
        super().__init__(f"{exchange_name}: {message}", "EXCHANGE_CONNECTION_ERROR", 503)
        self.exchange_name = exchange_name

class InvalidCredentialsError(CryptoPortfolioException):
    """Exception for invalid exchange credentials"""
    def __init__(self, exchange_name, message="Invalid credentials"):
        super().__init__(f"{exchange_name}: {message}", "INVALID_CREDENTIALS", 401)
        self.exchange_name = exchange_name

class RateLimitExceededError(CryptoPortfolioException):
    """Exception for rate limit exceeded"""
    def __init__(self, message="Rate limit exceeded"):
        super().__init__(message, "RATE_LIMIT_EXCEEDED", 429)

class DataValidationError(CryptoPortfolioException):
    """Exception for data validation errors"""
    def __init__(self, field, message="Data validation failed"):
        super().__init__(f"{field}: {message}", "DATA_VALIDATION_ERROR", 400)
        self.field = field

class StrategyAnalysisError(CryptoPortfolioException):
    """Exception for strategy analysis errors"""
    def __init__(self, strategy_name, message="Strategy analysis failed"):
        super().__init__(f"{strategy_name}: {message}", "STRATEGY_ANALYSIS_ERROR", 500)
        self.strategy_name = strategy_name

class InsufficientDataError(CryptoPortfolioException):
    """Exception for insufficient data scenarios"""
    def __init__(self, message="Insufficient data for analysis"):
        super().__init__(message, "INSUFFICIENT_DATA", 400)

# Error Handler Decorators
def handle_exceptions(logger=None):
    """Decorator to handle exceptions and return JSON responses"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = f(*args, **kwargs)
                
                # Log successful API call
                duration = (time.time() - start_time) * 1000
                if logger:
                    logger.info(f"API call successful: {f.__name__}", extra={
                        'function': f.__name__,
                        'duration_ms': round(duration, 2),
                        'endpoint': request.endpoint,
                        'method': request.method
                    })
                
                return result
                
            except CryptoPortfolioException as e:
                # Log application-specific errors
                duration = (time.time() - start_time) * 1000
                if logger:
                    logger.warning(f"Application error in {f.__name__}: {e.message}", extra={
                        'function': f.__name__,
                        'error_code': e.error_code,
                        'duration_ms': round(duration, 2),
                        'endpoint': request.endpoint,
                        'method': request.method
                    })
                
                return jsonify({
                    'success': False,
                    'error': e.error_code or 'APPLICATION_ERROR',
                    'message': e.message,
                    'status_code': e.status_code
                }), e.status_code
                
            except Exception as e:
                # Log unexpected errors
                duration = (time.time() - start_time) * 1000
                if logger:
                    logger.error(f"Unexpected error in {f.__name__}: {str(e)}", extra={
                        'function': f.__name__,
                        'error_type': type(e).__name__,
                        'duration_ms': round(duration, 2),
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'traceback': traceback.format_exc()
                    })
                
                # Don't expose internal errors in production
                if request.environ.get('FLASK_ENV') == 'production':
                    error_message = "An internal error occurred"
                else:
                    error_message = str(e)
                
                return jsonify({
                    'success': False,
                    'error': 'INTERNAL_ERROR',
                    'message': error_message
                }), 500
        
        return decorated_function
    return decorator

def handle_exchange_errors(exchange_name):
    """Decorator specifically for exchange-related operations"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                error_message = str(e).lower()
                
                # Map common CCXT errors to custom exceptions
                if 'invalid api' in error_message or 'authentication' in error_message:
                    raise InvalidCredentialsError(exchange_name, "Invalid API credentials")
                elif 'rate limit' in error_message or 'too many requests' in error_message:
                    raise RateLimitExceededError(f"Rate limit exceeded for {exchange_name}")
                elif 'network' in error_message or 'connection' in error_message:
                    raise ExchangeConnectionError(exchange_name, "Network connection failed")
                elif 'insufficient' in error_message:
                    raise InsufficientDataError(f"Insufficient data from {exchange_name}")
                else:
                    raise ExchangeConnectionError(exchange_name, f"Exchange error: {str(e)}")
        
        return decorated_function
    return decorator

def validate_required_fields(required_fields):
    """Decorator to validate required fields in request data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            data = getattr(request, 'validated_json', None) or request.json or {}
            
            missing_fields = []
            for field in required_fields:
                if field not in data or data[field] is None:
                    missing_fields.append(field)
            
            if missing_fields:
                raise DataValidationError(
                    ', '.join(missing_fields), 
                    f"Required fields missing: {', '.join(missing_fields)}"
                )
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def retry_on_failure(max_retries=3, delay=1, backoff=2):
    """Decorator to retry operations on failure"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return f(*args, **kwargs)
                except (ExchangeConnectionError, RateLimitExceededError) as e:
                    retries += 1
                    if retries >= max_retries:
                        raise e
                    
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Retry {retries}/{max_retries} for {f.__name__}: {str(e)}")
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
                except Exception as e:
                    # Don't retry on other types of errors
                    raise e
            
            return None
        
        return decorated_function
    return decorator

# Global exception to JSON conversion
def exception_to_dict(e):
    """Convert exception to dictionary for JSON serialization"""
    return {
        'type': type(e).__name__,
        'message': str(e),
        'args': e.args
    }