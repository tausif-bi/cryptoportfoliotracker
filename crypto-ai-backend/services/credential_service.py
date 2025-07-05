"""
Service for managing encrypted exchange credentials
"""
from models.database import db, ExchangeCredential
from utils.encryption import encryption_service
from utils.logger import get_logger
from datetime import datetime

logger = get_logger(__name__)

class CredentialService:
    """Service for managing encrypted exchange credentials"""
    
    @staticmethod
    def store_credentials(user_id: int, exchange_name: str, api_key: str, 
                         api_secret: str, password: str = None) -> ExchangeCredential:
        """Store encrypted exchange credentials"""
        try:
            # Check if credentials already exist for this exchange
            existing = ExchangeCredential.query.filter_by(
                user_id=user_id,
                exchange_name=exchange_name
            ).first()
            
            # Encrypt credentials
            encrypted_key = encryption_service.encrypt(api_key)
            encrypted_secret = encryption_service.encrypt(api_secret)
            encrypted_password = encryption_service.encrypt(password) if password else None
            
            if existing:
                # Update existing credentials
                existing.api_key_encrypted = encrypted_key
                existing.api_secret_encrypted = encrypted_secret
                existing.password_encrypted = encrypted_password
                existing.updated_at = datetime.utcnow()
                credential = existing
            else:
                # Create new credentials
                credential = ExchangeCredential(
                    user_id=user_id,
                    exchange_name=exchange_name,
                    api_key_encrypted=encrypted_key,
                    api_secret_encrypted=encrypted_secret,
                    password_encrypted=encrypted_password
                )
                db.session.add(credential)
            
            db.session.commit()
            logger.info(f"Stored encrypted credentials for user {user_id} on {exchange_name}")
            return credential
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to store credentials: {str(e)}")
            raise
    
    @staticmethod
    def get_credentials(user_id: int, exchange_name: str) -> dict:
        """Retrieve and decrypt exchange credentials"""
        try:
            credential = ExchangeCredential.query.filter_by(
                user_id=user_id,
                exchange_name=exchange_name,
                is_active=True
            ).first()
            
            if not credential:
                return None
            
            # Decrypt credentials
            return {
                'exchangeName': credential.exchange_name,
                'apiKey': encryption_service.decrypt(credential.api_key_encrypted),
                'apiSecret': encryption_service.decrypt(credential.api_secret_encrypted),
                'password': encryption_service.decrypt(credential.password_encrypted) if credential.password_encrypted else None
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve credentials: {str(e)}")
            raise
    
    @staticmethod
    def delete_credentials(user_id: int, exchange_name: str) -> bool:
        """Delete exchange credentials"""
        try:
            credential = ExchangeCredential.query.filter_by(
                user_id=user_id,
                exchange_name=exchange_name
            ).first()
            
            if credential:
                # Soft delete - just mark as inactive
                credential.is_active = False
                credential.updated_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"Deleted credentials for user {user_id} on {exchange_name}")
                return True
            
            return False
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete credentials: {str(e)}")
            raise
    
    @staticmethod
    def list_exchanges(user_id: int) -> list:
        """List all exchanges with stored credentials for a user"""
        try:
            credentials = ExchangeCredential.query.filter_by(
                user_id=user_id,
                is_active=True
            ).all()
            
            return [
                {
                    'exchange_name': cred.exchange_name,
                    'created_at': cred.created_at.isoformat(),
                    'updated_at': cred.updated_at.isoformat()
                }
                for cred in credentials
            ]
            
        except Exception as e:
            logger.error(f"Failed to list exchanges: {str(e)}")
            raise

# Global instance
credential_service = CredentialService()