#!/usr/bin/env python3
"""
Generate secure keys for production configuration
"""
import secrets
import base64
from cryptography.fernet import Fernet

def generate_secret_key(length=32):
    """Generate a secure random string"""
    return secrets.token_urlsafe(length)

def generate_encryption_key():
    """Generate a Fernet encryption key"""
    return Fernet.generate_key().decode()

def main():
    print("=== Secure Key Generator for Crypto Portfolio Tracker ===\n")
    
    print("Add these to your .env.production file:\n")
    
    # Generate Flask secret key
    secret_key = generate_secret_key(32)
    print(f"SECRET_KEY={secret_key}")
    
    # Generate JWT secret key
    jwt_secret = generate_secret_key(32)
    print(f"JWT_SECRET_KEY={jwt_secret}")
    
    # Generate encryption key
    encryption_key = generate_encryption_key()
    print(f"ENCRYPTION_KEY={encryption_key}")
    
    print("\n=== IMPORTANT SECURITY NOTES ===")
    print("1. Never commit these keys to version control")
    print("2. Store them securely (use environment variables or secrets management)")
    print("3. Use different keys for each environment (dev, staging, prod)")
    print("4. Rotate keys periodically")
    print("5. Keep backup of encryption key - losing it means losing encrypted data")

if __name__ == "__main__":
    main()