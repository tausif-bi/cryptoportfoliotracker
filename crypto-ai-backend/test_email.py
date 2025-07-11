#!/usr/bin/env python
"""
Test email functionality
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up Flask app context
from app import app
from services.email_service import send_reset_code, send_welcome_email, send_password_changed_email

def test_email_config():
    """Test email configuration"""
    print("Email Configuration Test")
    print("=" * 50)
    
    with app.app_context():
        config = app.config
        
        print(f"MAIL_SERVER: {config.get('MAIL_SERVER')}")
        print(f"MAIL_PORT: {config.get('MAIL_PORT')}")
        print(f"MAIL_USE_TLS: {config.get('MAIL_USE_TLS')}")
        print(f"MAIL_USERNAME: {config.get('MAIL_USERNAME')}")
        print(f"MAIL_DEFAULT_SENDER: {config.get('MAIL_DEFAULT_SENDER')}")
        print(f"MAIL_PASSWORD: {'*' * len(config.get('MAIL_PASSWORD', '')) if config.get('MAIL_PASSWORD') else 'Not set'}")
        
        if not config.get('MAIL_USERNAME') or not config.get('MAIL_PASSWORD'):
            print("\n⚠️  Warning: Email credentials not configured!")
            print("Please set MAIL_USERNAME and MAIL_PASSWORD in your .env file")
            return False
        
        print("\n✅ Email configuration looks good!")
        return True

def test_send_emails():
    """Test sending different email types"""
    test_email = input("\nEnter test email address: ").strip()
    
    if not test_email:
        print("No email provided, skipping email tests")
        return
    
    with app.app_context():
        print("\nTesting email functionality...")
        print("=" * 50)
        
        # Test 1: Welcome email
        try:
            print("\n1. Testing welcome email...")
            result = send_welcome_email(test_email, "TestUser")
            if result:
                print("✅ Welcome email sent successfully!")
            else:
                print("❌ Failed to send welcome email")
        except Exception as e:
            print(f"❌ Error sending welcome email: {e}")
        
        # Test 2: Password reset email
        try:
            print("\n2. Testing password reset email...")
            result = send_reset_code(test_email, "123456")
            if result:
                print("✅ Password reset email sent successfully!")
            else:
                print("❌ Failed to send password reset email")
        except Exception as e:
            print(f"❌ Error sending password reset email: {e}")
        
        # Test 3: Password changed notification
        try:
            print("\n3. Testing password change notification...")
            result = send_password_changed_email(test_email, "TestUser")
            if result:
                print("✅ Password change notification sent successfully!")
            else:
                print("❌ Failed to send password change notification")
        except Exception as e:
            print(f"❌ Error sending password change notification: {e}")

def main():
    """Main test function"""
    print("Crypto Portfolio Tracker - Email Service Test")
    print("=" * 50)
    
    # Test configuration
    if not test_email_config():
        print("\nPlease configure email settings before testing.")
        print("\nExample .env configuration for Gmail:")
        print("MAIL_SERVER=smtp.gmail.com")
        print("MAIL_PORT=587")
        print("MAIL_USE_TLS=True")
        print("MAIL_USERNAME=your-email@gmail.com")
        print("MAIL_PASSWORD=your-app-specific-password")
        print("MAIL_DEFAULT_SENDER=your-email@gmail.com")
        return
    
    # Ask if user wants to send test emails
    response = input("\nDo you want to send test emails? (y/n): ").lower()
    if response == 'y':
        test_send_emails()
    else:
        print("Email configuration test completed. No emails sent.")

if __name__ == "__main__":
    main()