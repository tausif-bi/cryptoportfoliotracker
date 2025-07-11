from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, create_access_token
from utils.auth import UserManager, PasswordManager, create_tokens, revoke_token, auth_required
from utils.validators import UserRegistrationSchema, UserLoginSchema, PasswordChangeSchema, validate_json_input
from utils.security import get_limiter, require_valid_request, validate_request_size
from utils.exceptions import handle_exceptions
from utils.logger import get_logger
from models.database import db, Portfolio
from services.email_service import send_welcome_email, send_password_changed_email

logger = get_logger(__name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')
limiter = get_limiter()

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")
@require_valid_request
@validate_request_size(1)
@validate_json_input(UserRegistrationSchema)
@handle_exceptions(logger)
def register():
    """Register a new user"""
    data = request.validated_json
    
    logger.info(f"User registration attempt: {data.get('username')}")
    
    # Create user
    user = UserManager.create_user(
        username=data['username'],
        email=data['email'],
        password=data['password']
    )
    
    # Create tokens
    access_token, refresh_token = create_tokens(user)
    
    # Send welcome email (non-blocking)
    try:
        send_welcome_email(user.email, user.username)
    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")
        # Don't fail registration if email fails
    
    return jsonify({
        'success': True,
        'message': 'User registered successfully',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    }), 201

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
@require_valid_request
@validate_request_size(1)
@validate_json_input(UserLoginSchema)
@handle_exceptions(logger)
def login():
    """Authenticate user and return tokens"""
    data = request.validated_json
    
    logger.info(f"Login attempt: {data.get('username_or_email')}")
    
    # Authenticate user
    user = UserManager.authenticate_user(
        username_or_email=data['username_or_email'],
        password=data['password']
    )
    
    # Create tokens
    access_token, refresh_token = create_tokens(user)
    
    return jsonify({
        'success': True,
        'message': 'Login successful',
        'user': user.to_dict(),
        'access_token': access_token,
        'refresh_token': refresh_token
    })

@auth_bp.route('/refresh', methods=['POST'])
@limiter.limit("20 per minute")
@require_valid_request
@handle_exceptions(logger)
@jwt_required(refresh=True)
def refresh_token():
    """Refresh access token using refresh token"""
    user_id = get_jwt_identity()
    user = UserManager.get_user_by_id(user_id)
    
    # Create new access token
    access_token, _ = create_tokens(user)
    
    return jsonify({
        'success': True,
        'access_token': access_token
    })

@auth_bp.route('/logout', methods=['POST'])
@limiter.limit("20 per minute")
@require_valid_request
@auth_required()
@handle_exceptions(logger)
def logout():
    """Logout user and revoke token"""
    from flask import current_app
    
    # Get JWT claims
    claims = get_jwt()
    jti = claims['jti']
    
    # Revoke token (need to pass blacklisted_tokens from app context)
    blacklisted_tokens = current_app.config.get('blacklisted_tokens', set())
    revoke_token(jti, blacklisted_tokens)
    
    logger.info(f"User logged out: {request.current_user.username}")
    
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    })

@auth_bp.route('/profile', methods=['GET'])
@limiter.limit("30 per minute")
@require_valid_request
@auth_required()
@handle_exceptions(logger)
def get_profile():
    """Get current user profile"""
    user = request.current_user
    
    # Get user's portfolios
    portfolios = Portfolio.query.filter_by(user_id=user.id, is_active=True).all()
    
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'portfolios': [p.to_dict() for p in portfolios]
    })

@auth_bp.route('/change-password', methods=['POST'])
@limiter.limit("5 per minute")
@require_valid_request
@validate_request_size(1)
@validate_json_input(PasswordChangeSchema)
@auth_required()
@handle_exceptions(logger)
def change_password():
    """Change user password"""
    data = request.validated_json
    user = request.current_user
    
    # Verify current password
    if not PasswordManager.verify_password(data['current_password'], user.password_hash):
        logger.warning(f"Password change failed for user {user.username}: invalid current password")
        return jsonify({
            'success': False,
            'error': 'INVALID_PASSWORD',
            'message': 'Current password is incorrect'
        }), 400
    
    # Validate new password
    is_valid, message = PasswordManager.validate_password_strength(data['new_password'])
    if not is_valid:
        return jsonify({
            'success': False,
            'error': 'WEAK_PASSWORD',
            'message': message
        }), 400
    
    # Update password
    user.password_hash = PasswordManager.hash_password(data['new_password'])
    db.session.commit()
    
    logger.info(f"Password changed for user: {user.username}")
    
    # Send notification email (non-blocking)
    try:
        send_password_changed_email(user.email, user.username)
    except Exception as e:
        logger.error(f"Failed to send password change notification: {str(e)}")
        # Don't fail password change if email fails
    
    return jsonify({
        'success': True,
        'message': 'Password changed successfully'
    })