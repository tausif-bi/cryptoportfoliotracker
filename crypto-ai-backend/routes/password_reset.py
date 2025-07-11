from flask import Blueprint, request, jsonify, current_app
import random
import string
from datetime import datetime, timedelta, timezone
import traceback
from models.database import db, User
from services.email_service import send_reset_code, send_password_changed_email
from utils.logger import get_logger
import bcrypt
from sqlalchemy import or_

# Create blueprint
password_reset_bp = Blueprint('password_reset', __name__)
logger = get_logger(__name__)

# In-memory storage for reset codes (in production, use Redis or database)
reset_codes = {}

def generate_reset_code():
    """Generate a 6-digit reset code"""
    return ''.join(random.choices(string.digits, k=6))

@password_reset_bp.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    """Send password reset code to user's email"""
    try:
        data = request.get_json()
        email_or_username = data.get('email', '').strip().lower()
        
        if not email_or_username:
            return jsonify({
                'success': False,
                'message': 'Email or username is required'
            }), 400
        
        # Find user by email or username
        user = User.query.filter(
            or_(
                User.email == email_or_username,
                User.username == email_or_username
            )
        ).first()
        
        if not user:
            # Don't reveal if user exists or not for security
            logger.info(f"Password reset requested for non-existent user: {email_or_username}")
            return jsonify({
                'success': True,
                'message': 'If an account exists with this email/username, a reset code will be sent'
            }), 200
        
        # Generate reset code
        code = generate_reset_code()
        
        # Store code with expiration (15 minutes)
        reset_codes[user.email] = {
            'code': code,
            'expires': datetime.now() + timedelta(minutes=15),
            'user_id': str(user.id)
        }
        
        # Send email with reset code
        email_sent = send_reset_code(user.email, code)
        
        if email_sent:
            logger.info(f"Password reset code sent to {user.email}")
        else:
            logger.error(f"Failed to send password reset email to {user.email}")
        
        # Always return success for security (don't reveal if email failed)
        response = {
            'success': True,
            'message': 'If an account exists with this email/username, a reset code will be sent'
        }
        
        # Only include debug_code in development mode
        if current_app.config.get('DEBUG'):
            response['debug_code'] = code
            
        return jsonify(response), 200
        
    except Exception as e:
        print(f"Error in forgot_password: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'An error occurred'
        }), 500

@password_reset_bp.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """Reset user's password with valid reset code"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        reset_code = data.get('reset_code', '').strip()
        new_password = data.get('new_password', '')
        
        # Validate inputs
        if not all([email, reset_code, new_password]):
            return jsonify({
                'success': False,
                'message': 'Email, reset code, and new password are required'
            }), 400
        
        # Check if reset code exists and is valid
        if email not in reset_codes:
            return jsonify({
                'success': False,
                'message': 'Invalid or expired reset code'
            }), 400
        
        stored_data = reset_codes[email]
        
        # Check if code matches
        if stored_data['code'] != reset_code:
            return jsonify({
                'success': False,
                'message': 'Invalid reset code'
            }), 400
        
        # Check if code is expired
        if datetime.now() > stored_data['expires']:
            del reset_codes[email]  # Clean up expired code
            return jsonify({
                'success': False,
                'message': 'Reset code has expired'
            }), 400
        
        # Validate password strength
        if len(new_password) < 8:
            return jsonify({
                'success': False,
                'message': 'Password must be at least 8 characters long'
            }), 400
        
        # Find user by email
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        # Verify the stored user_id matches
        if str(user.id) != stored_data.get('user_id'):
            return jsonify({
                'success': False,
                'message': 'Invalid reset code'
            }), 400
        
        # Hash the new password
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        
        # Update user's password
        user.password_hash = password_hash.decode('utf-8')
        user.updated_at = datetime.now(timezone.utc)
        
        try:
            db.session.commit()
            
            # Remove used code
            del reset_codes[email]
            
            # Send confirmation email
            send_password_changed_email(user.email, user.username)
            
            logger.info(f"Password reset successful for user {user.username}")
            
            return jsonify({
                'success': True,
                'message': 'Password reset successfully'
            }), 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database error during password reset: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'Failed to update password'
            }), 500
        
    except Exception as e:
        print(f"Error in reset_password: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'An error occurred'
        }), 500

# Cleanup expired codes periodically
def cleanup_expired_codes():
    """Remove expired reset codes"""
    current_time = datetime.now()
    expired_emails = [
        email for email, data in reset_codes.items()
        if current_time > data['expires']
    ]
    for email in expired_emails:
        del reset_codes[email]