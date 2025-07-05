"""
Logging configuration and utilities
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
import json
from flask import request, g
import traceback

class CustomJSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add request context if available (safely handle Flask context)
        try:
            if hasattr(g, 'request_id'):
                log_entry['request_id'] = g.request_id
            
            if request:
                log_entry['request'] = {
                    'method': request.method,
                    'url': request.url,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', 'Unknown')[:100]  # Truncate long user agents
                }
        except RuntimeError:
            # Outside Flask request context, skip request info
            pass
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'exc_info', 'exc_text', 'stack_info']:
                log_entry['extra'] = log_entry.get('extra', {})
                log_entry['extra'][key] = value
        
        return json.dumps(log_entry)

def setup_logging(app):
    """Setup logging configuration for the Flask app"""
    
    # Get log level from config
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO').upper())
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler with colored output for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if app.config.get('FLASK_ENV') == 'development':
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_format)
    else:
        console_handler.setFormatter(CustomJSONFormatter())
    
    root_logger.addHandler(console_handler)
    
    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(CustomJSONFormatter())
    root_logger.addHandler(file_handler)
    
    # Separate file handler for errors
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'error.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(CustomJSONFormatter())
    root_logger.addHandler(error_handler)
    
    # Security log handler
    security_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'security.log'),
        maxBytes=10*1024*1024,  # 10MB
        backupCount=10
    )
    security_handler.setLevel(logging.WARNING)
    security_handler.setFormatter(CustomJSONFormatter())
    
    # Create security logger
    security_logger = logging.getLogger('security')
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.WARNING)
    
    # Suppress some noisy loggers in production
    if app.config.get('FLASK_ENV') == 'production':
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    app.logger.info('Logging configuration completed', extra={
        'log_level': app.config.get('LOG_LEVEL', 'INFO'),
        'environment': app.config.get('FLASK_ENV', 'development')
    })

def get_logger(name):
    """Get a logger instance with the given name"""
    return logging.getLogger(name)

def log_api_call(endpoint, method, status_code, duration_ms, **kwargs):
    """Log API call details"""
    logger = get_logger('api')
    logger.info('API call completed', extra={
        'endpoint': endpoint,
        'method': method,
        'status_code': status_code,
        'duration_ms': duration_ms,
        **kwargs
    })

def log_exchange_operation(exchange_name, operation, symbol=None, success=True, error=None, **kwargs):
    """Log exchange operations"""
    logger = get_logger('exchange')
    level = logging.INFO if success else logging.ERROR
    
    logger.log(level, f'Exchange operation: {operation}', extra={
        'exchange': exchange_name,
        'operation': operation,
        'symbol': symbol,
        'success': success,
        'error': str(error) if error else None,
        **kwargs
    })

def log_security_event(event_type, severity='info', **kwargs):
    """Log security events"""
    logger = get_logger('security')
    
    severity_map = {
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    
    level = severity_map.get(severity.lower(), logging.INFO)
    logger.log(level, f'Security event: {event_type}', extra={
        'event_type': event_type,
        'severity': severity,
        **kwargs
    })

def log_performance_metric(metric_name, value, unit='ms', **kwargs):
    """Log performance metrics"""
    logger = get_logger('performance')
    logger.info(f'Performance metric: {metric_name}', extra={
        'metric_name': metric_name,
        'value': value,
        'unit': unit,
        **kwargs
    })

class RequestIDMiddleware:
    """Middleware to add unique request IDs"""
    
    def __init__(self, app):
        self.app = app
        
    def __call__(self, environ, start_response):
        import uuid
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        environ['REQUEST_ID'] = request_id
        
        def new_start_response(status, response_headers):
            response_headers.append(('X-Request-ID', request_id))
            return start_response(status, response_headers)
        
        return self.app(environ, new_start_response)