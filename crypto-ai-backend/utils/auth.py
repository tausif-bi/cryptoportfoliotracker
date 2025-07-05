"""
Authentication utilities for JWT-based authentication
"""
import bcrypt
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, create_refresh_token,
    get_jwt_identity, get_jwt, verify_jwt_in_request
)
from models.database import db, User
from utils.logger import get_logger, log_security_event
from utils.exceptions import CryptoPortfolioException

logger = get_logger(__name__)

class AuthenticationError(CryptoPortfolioException):
    """Exception for authentication errors"""
    def __init__(self, message="Authentication failed"):
        super().__init__(message, "AUTHENTICATION_ERROR", 401)

class AuthorizationError(CryptoPortfolioException):
    """Exception for authorization errors"""
    def __init__(self, message="Access denied"):
        super().__init__(message, "AUTHORIZATION_ERROR", 403)

def init_jwt(app):
    """Initialize JWT manager with Flask app"""
    jwt = JWTManager(app)
    
    # JWT Configuration
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
    app.config['JWT_BLACKLIST_ENABLED'] = True
    app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']
    
    # In-memory blacklist (in production, use Redis or database)
    blacklisted_tokens = set()
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        return jti in blacklisted_tokens
    
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        log_security_event('revoked_token_access', severity='warning', 
                          token_jti=jwt_payload['jti'])
        return jsonify({
            'success': False,
            'error': 'TOKEN_REVOKED',
            'message': 'Token has been revoked'
        }), 401
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        log_security_event('expired_token_access', severity='info',
                          token_jti=jwt_payload['jti'])
        return jsonify({
            'success': False,
            'error': 'TOKEN_EXPIRED',
            'message': 'Token has expired'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        log_security_event('invalid_token_access', severity='warning',
                          error=str(error))
        return jsonify({
            'success': False,
            'error': 'INVALID_TOKEN',
            'message': 'Invalid token'
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'success': False,
            'error': 'TOKEN_REQUIRED',
            'message': 'Authentication token required'
        }), 401
    
    return jwt, blacklisted_tokens

class PasswordManager:
    """Handle password hashing and verification"""
    
    @staticmethod
    def hash_password(password):
        """Hash a password using bcrypt"""
        if not password:
            raise ValueError("Password cannot be empty")
        
        # Generate salt and hash password
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        return password_hash.decode('utf-8')
    
    @staticmethod
    def verify_password(password, password_hash):
        """Verify a password against its hash"""
        if not password or not password_hash:
            return False
        
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False
    
    @staticmethod
    def validate_password_strength(password):
        """Validate password meets security requirements"""
        if not password:
            return False, "Password is required"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password must be less than 128 characters"
        
        # Check for at least one letter and one number
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        if not has_letter:
            return False, "Password must contain at least one letter"
        
        if not has_number:
            return False, "Password must contain at least one number"
        
        return True, "Password is valid"

class UserManager:
    """Handle user-related operations"""
    
    @staticmethod
    def create_user(username, email, password):
        """Create a new user"""
        # Validate inputs
        if not username or len(username) < 3:
            raise AuthenticationError("Username must be at least 3 characters long")
        
        if not email or '@' not in email:
            raise AuthenticationError("Valid email address is required")
        
        # Validate password strength
        is_valid, message = PasswordManager.validate_password_strength(password)
        if not is_valid:
            raise AuthenticationError(message)
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            raise AuthenticationError("Username already exists")
        
        if User.query.filter_by(email=email).first():
            raise AuthenticationError("Email already exists")
        
        # Hash password
        password_hash = PasswordManager.hash_password(password)
        
        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            is_active=True
        )
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"Created new user: {username}")
        log_security_event('user_created', severity='info', 
                          user_id=str(user.id), username=username)
        
        return user
    
    @staticmethod
    def authenticate_user(username_or_email, password):
        """Authenticate user credentials"""
        if not username_or_email or not password:
            raise AuthenticationError("Username/email and password are required")
        
        try:
            # Find user by username or email
            user = User.query.filter(
                (User.username == username_or_email) | 
                (User.email == username_or_email)
            ).first()
            
            if not user:
                log_security_event('login_failed', severity='warning',
                                  username_or_email=username_or_email,
                                  reason='user_not_found')
                raise AuthenticationError("Invalid credentials")
            
            if not user.is_active:
                log_security_event('login_failed', severity='warning',
                                  user_id=str(user.id), username=user.username,
                                  reason='account_disabled')
                raise AuthenticationError("Account is disabled")
            
            # Verify password
            if not PasswordManager.verify_password(password, user.password_hash):
                log_security_event('login_failed', severity='warning',
                                  user_id=str(user.id), username=user.username,
                                  reason='invalid_password')
                raise AuthenticationError("Invalid credentials")
            
            # Store user info before any session operations
            user_dict = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'is_active': user.is_active,
                'created_at': user.created_at
            }
            
            # Update last login in a separate transaction to avoid session corruption
            try:
                # Use a fresh query to avoid session conflicts
                update_user = User.query.filter_by(id=user.id).first()
                if update_user:
                    update_user.last_login = datetime.now(timezone.utc)
                    db.session.commit()
                    logger.debug(f"Updated last_login for user {user.username}")
            except Exception as e:
                logger.warning(f"Failed to update last_login for user {user.username}: {str(e)}")
                try:
                    db.session.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback session: {str(rollback_error)}")
                # Continue with authentication even if last_login update fails
            
            # Create a fresh user object from the stored data to avoid session issues
            fresh_user = User()
            for key, value in user_dict.items():
                setattr(fresh_user, key, value)
            
            logger.info(f"User authenticated successfully: {fresh_user.username}")
            log_security_event('login_success', severity='info',
                              user_id=str(fresh_user.id), username=fresh_user.username)
            
            return fresh_user
            
        except AuthenticationError:
            # Re-raise authentication errors
            raise
        except Exception as e:
            # Handle any database or session errors
            logger.error(f"Database error during authentication: {str(e)}")
            try:
                db.session.rollback()
            except:
                pass
            raise AuthenticationError("Authentication service temporarily unavailable")
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        try:
            # Convert to string for comparison
            if not isinstance(user_id, str):
                user_id = str(user_id)
            
            # Use SQL CAST to string for reliable comparison across contexts
            from sqlalchemy import cast, String
            user = User.query.filter(cast(User.id, String) == user_id).first()
            
            if not user or not user.is_active:
                raise AuthenticationError("User not found or inactive")
            return user
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid user ID format: {user_id}, error: {str(e)}")
            raise AuthenticationError("Invalid user ID format")

def create_tokens(user):
    """Create access and refresh tokens for user"""
    additional_claims = {
        'username': user.username,
        'email': user.email,
        'is_active': user.is_active
    }
    
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims=additional_claims
    )
    
    refresh_token = create_refresh_token(
        identity=str(user.id),
        additional_claims=additional_claims
    )
    
    return access_token, refresh_token

def get_current_user():
    """Get current authenticated user"""
    try:
        verify_jwt_in_request()
        
        # Get additional claims from JWT which include username
        from flask_jwt_extended import get_jwt
        jwt_claims = get_jwt()
        username = jwt_claims.get('username')
        
        if username:
            # Use username lookup which we know works reliably
            user = User.query.filter_by(username=username).first()
            if user and user.is_active:
                return user
            else:
                raise AuthenticationError("User not found or inactive")
        else:
            # Fallback to ID-based lookup
            user_id = get_jwt_identity()
            return UserManager.get_user_by_id(user_id)
            
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        raise AuthenticationError("Unable to verify user identity")

def auth_required(optional=False):
    """Decorator that requires valid JWT token"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request(optional=optional)
                if not optional or get_jwt_identity():
                    # Add user to request context
                    request.current_user = get_current_user()
                return f(*args, **kwargs)
            except Exception as e:
                if optional:
                    return f(*args, **kwargs)
                logger.warning(f"Authentication failed for {f.__name__}: {str(e)}")
                raise AuthenticationError("Authentication required")
        
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator that requires admin privileges"""
    @wraps(f)
    @auth_required()
    def decorated_function(*args, **kwargs):
        user = request.current_user
        
        # For now, consider the first user or users with specific usernames as admin
        # In production, you'd have a proper role system
        is_admin = (
            user.username in ['admin', 'default_user'] or 
            user.email.endswith('@admin.local')
        )
        
        if not is_admin:
            log_security_event('unauthorized_admin_access', severity='warning',
                              user_id=str(user.id), username=user.username)
            raise AuthorizationError("Admin privileges required")
        
        return f(*args, **kwargs)
    
    return decorated_function

def revoke_token(jti, blacklisted_tokens):
    """Revoke a token by adding it to blacklist"""
    blacklisted_tokens.add(jti)
    log_security_event('token_revoked', severity='info', token_jti=jti)