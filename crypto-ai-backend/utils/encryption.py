"""
Encryption utilities for sensitive data
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import current_app

class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""
    
    def __init__(self, app=None):
        self.cipher_suite = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize encryption with Flask app"""
        # Get encryption key from environment or generate one
        encryption_key = app.config.get('ENCRYPTION_KEY')
        
        if not encryption_key:
            # In production, this should come from environment variable
            # Generate a key from the JWT secret as fallback
            jwt_secret = app.config.get('JWT_SECRET_KEY', 'default-key')
            salt = b'crypto-portfolio-salt'  # In production, use random salt
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(jwt_secret.encode()))
            self.cipher_suite = Fernet(key)
        else:
            # Use provided encryption key
            self.cipher_suite = Fernet(encryption_key.encode())
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data"""
        if not data:
            return ""
        
        if not self.cipher_suite:
            # If encryption not initialized, return data as-is (development only)
            if current_app.config.get('ENV') == 'production':
                raise RuntimeError("Encryption not properly initialized")
            return data
        
        try:
            encrypted = self.cipher_suite.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            current_app.logger.error(f"Encryption error: {str(e)}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        if not encrypted_data:
            return ""
        
        if not self.cipher_suite:
            # If encryption not initialized, return data as-is (development only)
            if current_app.config.get('ENV') == 'production':
                raise RuntimeError("Encryption not properly initialized")
            return encrypted_data
        
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.cipher_suite.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            current_app.logger.error(f"Decryption error: {str(e)}")
            raise
    
    def encrypt_dict(self, data: dict) -> dict:
        """Encrypt sensitive fields in a dictionary"""
        encrypted_data = {}
        sensitive_fields = ['apiKey', 'apiSecret', 'password', 'api_key', 'api_secret']
        
        for key, value in data.items():
            if key in sensitive_fields and value:
                encrypted_data[key] = self.encrypt(str(value))
            else:
                encrypted_data[key] = value
        
        return encrypted_data
    
    def decrypt_dict(self, data: dict) -> dict:
        """Decrypt sensitive fields in a dictionary"""
        decrypted_data = {}
        sensitive_fields = ['apiKey', 'apiSecret', 'password', 'api_key', 'api_secret']
        
        for key, value in data.items():
            if key in sensitive_fields and value:
                decrypted_data[key] = self.decrypt(str(value))
            else:
                decrypted_data[key] = value
        
        return decrypted_data

# Global encryption service instance
encryption_service = EncryptionService()

def init_encryption(app):
    """Initialize encryption service with Flask app"""
    encryption_service.init_app(app)
    return encryption_service