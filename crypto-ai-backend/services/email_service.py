"""
Email service for sending transactional emails
"""
from flask_mail import Mail, Message
from flask import current_app
from threading import Thread
import logging

mail = Mail()
logger = logging.getLogger(__name__)

def init_mail(app):
    """Initialize Flask-Mail with the Flask app"""
    mail.init_app(app)
    return mail

def send_async_email(app, msg):
    """Send email asynchronously"""
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")

def send_email(subject, recipients, body, html_body=None, sender=None, async_send=True):
    """
    Send email to recipients
    
    Args:
        subject: Email subject
        recipients: List of recipient email addresses
        body: Plain text body
        html_body: HTML body (optional)
        sender: Sender email (optional, uses default if not provided)
        async_send: Send email asynchronously (default: True)
    """
    try:
        msg = Message(
            subject=subject,
            recipients=recipients if isinstance(recipients, list) else [recipients],
            body=body,
            html=html_body,
            sender=sender or current_app.config.get('MAIL_DEFAULT_SENDER')
        )
        
        if async_send:
            Thread(
                target=send_async_email,
                args=(current_app._get_current_object(), msg)
            ).start()
        else:
            mail.send(msg)
            
        logger.info(f"Email sent successfully to {recipients}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def send_reset_code(email, code):
    """
    Send password reset code to user
    
    Args:
        email: User's email address
        code: Password reset code
    """
    subject = "Password Reset Code - Crypto Portfolio Tracker"
    
    body = f"""Hello,

You requested a password reset for your Crypto Portfolio Tracker account.

Your password reset code is: {code}

This code will expire in 15 minutes. If you didn't request this reset, please ignore this email.

Best regards,
Crypto Portfolio Tracker Team
"""

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: #0B0E11;
            color: #fff;
            padding: 20px;
            text-align: center;
        }}
        .content {{
            padding: 20px;
            background-color: #f4f4f4;
        }}
        .code-box {{
            background-color: #fff;
            border: 2px solid #4CAF50;
            padding: 15px;
            margin: 20px 0;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
            letter-spacing: 2px;
            color: #4CAF50;
        }}
        .footer {{
            margin-top: 20px;
            text-align: center;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Hello,</p>
            <p>You requested a password reset for your Crypto Portfolio Tracker account.</p>
            
            <p>Your password reset code is:</p>
            <div class="code-box">{code}</div>
            
            <p><strong>This code will expire in 15 minutes.</strong></p>
            
            <p>If you didn't request this reset, please ignore this email and your password will remain unchanged.</p>
            
            <p>Best regards,<br>
            Crypto Portfolio Tracker Team</p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
        </div>
    </div>
</body>
</html>
"""
    
    return send_email(
        subject=subject,
        recipients=email,
        body=body,
        html_body=html_body
    )

def send_welcome_email(email, username):
    """
    Send welcome email to new user
    
    Args:
        email: User's email address
        username: User's username
    """
    subject = "Welcome to Crypto Portfolio Tracker!"
    
    body = f"""Hello {username},

Welcome to Crypto Portfolio Tracker! We're excited to have you on board.

With Crypto Portfolio Tracker, you can:
- Track your cryptocurrency portfolio across multiple exchanges
- Get AI-powered trading insights and signals
- Analyze your trading performance with advanced strategies
- Monitor real-time price movements

To get started:
1. Connect your exchange accounts
2. View your consolidated portfolio
3. Explore AI trading strategies
4. Set up price alerts

If you have any questions, feel free to reach out to our support team.

Best regards,
Crypto Portfolio Tracker Team
"""

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .content {{
            padding: 30px;
            background-color: #f8f9fa;
            border-radius: 0 0 10px 10px;
        }}
        .feature-list {{
            background-color: #fff;
            border-radius: 5px;
            padding: 20px;
            margin: 20px 0;
        }}
        .feature-list ul {{
            list-style-type: none;
            padding: 0;
        }}
        .feature-list li {{
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}
        .feature-list li:last-child {{
            border-bottom: none;
        }}
        .feature-list li:before {{
            content: "✓ ";
            color: #4CAF50;
            font-weight: bold;
            margin-right: 10px;
        }}
        .cta-button {{
            display: inline-block;
            background-color: #4CAF50;
            color: white;
            padding: 12px 30px;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 20px;
        }}
        .footer {{
            margin-top: 30px;
            text-align: center;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to Crypto Portfolio Tracker!</h1>
            <p>Your journey to smarter crypto trading starts here</p>
        </div>
        <div class="content">
            <p>Hello <strong>{username}</strong>,</p>
            <p>Welcome to Crypto Portfolio Tracker! We're excited to have you on board.</p>
            
            <div class="feature-list">
                <h3>With Crypto Portfolio Tracker, you can:</h3>
                <ul>
                    <li>Track your cryptocurrency portfolio across multiple exchanges</li>
                    <li>Get AI-powered trading insights and signals</li>
                    <li>Analyze your trading performance with advanced strategies</li>
                    <li>Monitor real-time price movements</li>
                    <li>Calculate P&L with FIFO matching</li>
                    <li>Access technical indicators and charts</li>
                </ul>
            </div>
            
            <h3>Getting Started:</h3>
            <ol>
                <li>Connect your exchange accounts securely</li>
                <li>View your consolidated portfolio dashboard</li>
                <li>Explore AI trading strategies</li>
                <li>Set up price alerts and notifications</li>
            </ol>
            
            <p>If you have any questions, our support team is here to help!</p>
            
            <p>Best regards,<br>
            <strong>Crypto Portfolio Tracker Team</strong></p>
        </div>
        <div class="footer">
            <p>This is an automated message. Please do not reply to this email.</p>
            <p>&copy; 2024 Crypto Portfolio Tracker. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
    
    return send_email(
        subject=subject,
        recipients=email,
        body=body,
        html_body=html_body
    )

def send_password_changed_email(email, username):
    """
    Send notification email when password is changed
    
    Args:
        email: User's email address
        username: User's username
    """
    subject = "Password Changed - Crypto Portfolio Tracker"
    
    body = f"""Hello {username},

Your password has been successfully changed.

If you made this change, no further action is required.

If you didn't make this change, please contact our support team immediately and secure your account.

Best regards,
Crypto Portfolio Tracker Team
"""
    
    return send_email(
        subject=subject,
        recipients=email,
        body=body
    )