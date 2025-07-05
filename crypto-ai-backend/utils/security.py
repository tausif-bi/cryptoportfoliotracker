"""
Security utilities for the Flask application
"""
from functools import wraps
from flask import request, jsonify, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import hashlib
import secrets
import time

# Rate limiting configuration
def get_limiter():
    """Initialize rate limiter"""
    return Limiter(
        key_func=get_remote_address,
        default_limits=["1000 per hour"]
    )

def add_security_headers(response):
    """Add security headers to all responses"""
    # Only add security headers in production or if explicitly enabled
    if current_app.config.get('ENV') == 'production' or current_app.config.get('ENABLE_SECURITY_HEADERS'):
        # Prevent clickjacking attacks
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS filter in browsers
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Enforce HTTPS in production
        if current_app.config.get('PREFERRED_URL_SCHEME') == 'https':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' wss: https:;"
        )
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (formerly Feature Policy)
        response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    
    return response

def validate_api_key(api_key):
    """Validate API key format and basic security requirements"""
    if not api_key:
        return False, "API key is required"
    
    if len(api_key) < 10:
        return False, "API key too short"
    
    if len(api_key) > 500:
        return False, "API key too long"
    
    # Check for suspicious patterns
    suspicious_patterns = ['<script', 'javascript:', 'data:', 'vbscript:']
    for pattern in suspicious_patterns:
        if pattern.lower() in api_key.lower():
            return False, "Invalid characters in API key"
    
    return True, "Valid"

def hash_sensitive_data(data):
    """Hash sensitive data for logging purposes"""
    if not data:
        return "N/A"
    
    # Return first 4 and last 4 characters with hashed middle
    if len(data) <= 8:
        return "****"
    
    start = data[:4]
    end = data[-4:]
    middle_hash = hashlib.sha256(data[4:-4].encode()).hexdigest()[:8]
    
    return f"{start}...{middle_hash}...{end}"

def generate_secure_token(length=32):
    """Generate a secure random token"""
    return secrets.token_urlsafe(length)

def validate_request_size(max_size_mb=10):
    """Decorator to limit request size"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            content_length = request.content_length
            if content_length and content_length > max_size_mb * 1024 * 1024:
                return jsonify({
                    'success': False, 
                    'error': f'Request too large. Maximum size: {max_size_mb}MB'
                }), 413
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_security_event(event_type, details, severity='info'):
    """Log security-related events"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    remote_addr = request.remote_addr if request else 'unknown'
    user_agent = request.headers.get('User-Agent', 'unknown') if request else 'unknown'
    
    log_entry = {
        'timestamp': timestamp,
        'event_type': event_type,
        'severity': severity,
        'remote_addr': remote_addr,
        'user_agent': user_agent,
        'details': details
    }
    
    # In production, you would send this to a proper logging service
    print(f"SECURITY_EVENT: {log_entry}")

def check_request_integrity():
    """Check basic request integrity"""
    # Check for common attack patterns in headers
    suspicious_headers = ['x-forwarded-for', 'x-real-ip', 'x-originating-ip']
    for header in suspicious_headers:
        value = request.headers.get(header)
        if value and ('script' in value.lower() or '<' in value or '>' in value):
            log_security_event('suspicious_header', f'{header}: {value}', 'warning')
            return False
    
    # Check User-Agent
    user_agent = request.headers.get('User-Agent', '')
    if len(user_agent) > 1000:  # Suspiciously long user agent
        log_security_event('suspicious_user_agent', f'Length: {len(user_agent)}', 'warning')
        return False
    
    return True

def require_valid_request(f):
    """Decorator to validate basic request integrity"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_request_integrity():
            return jsonify({
                'success': False, 
                'error': 'Request failed security validation'
            }), 400
        return f(*args, **kwargs)
    return decorated_function