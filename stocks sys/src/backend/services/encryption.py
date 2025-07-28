"""
Encryption service for secure storage of API keys and sensitive data
Uses AES-256 encryption with Fernet (symmetric encryption)
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)

class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""
    
    def __init__(self, password: Optional[str] = None):
        """
        Initialize encryption service
        
        Args:
            password: Master password for encryption. If None, uses environment variable.
        """
        self.password = password or os.getenv("ENCRYPTION_PASSWORD", "default-password-change-in-production")
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize Fernet encryption with derived key"""
        try:
            # Generate a salt (in production, this should be stored securely)
            salt = os.getenv("ENCRYPTION_SALT", "default-salt-change-in-production").encode()
            
            # Derive key from password
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.password.encode()))
            
            # Initialize Fernet
            self._fernet = Fernet(key)
            logger.info("Encryption service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize encryption service: {str(e)}")
            raise
    
    def encrypt(self, data: Union[str, bytes]) -> str:
        """
        Encrypt data and return base64 encoded string
        
        Args:
            data: Data to encrypt (string or bytes)
            
        Returns:
            Base64 encoded encrypted data
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            encrypted_data = self._fernet.encrypt(data)
            return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt base64 encoded encrypted data
        
        Args:
            encrypted_data: Base64 encoded encrypted data
            
        Returns:
            Decrypted data as string
        """
        try:
            # Decode from base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
            
            # Decrypt
            decrypted_data = self._fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise
    
    def encrypt_api_key(self, api_key: str, service_name: str) -> str:
        """
        Encrypt API key with additional service context
        
        Args:
            api_key: The API key to encrypt
            service_name: Name of the service (for logging)
            
        Returns:
            Encrypted API key
        """
        try:
            encrypted_key = self.encrypt(api_key)
            logger.info(f"API key encrypted for service: {service_name}")
            return encrypted_key
            
        except Exception as e:
            logger.error(f"Failed to encrypt API key for {service_name}: {str(e)}")
            raise
    
    def decrypt_api_key(self, encrypted_key: str, service_name: str) -> str:
        """
        Decrypt API key with additional service context
        
        Args:
            encrypted_key: The encrypted API key
            service_name: Name of the service (for logging)
            
        Returns:
            Decrypted API key
        """
        try:
            decrypted_key = self.decrypt(encrypted_key)
            logger.info(f"API key decrypted for service: {service_name}")
            return decrypted_key
            
        except Exception as e:
            logger.error(f"Failed to decrypt API key for {service_name}: {str(e)}")
            raise
    
    def generate_key(self) -> str:
        """
        Generate a new Fernet key for encryption
        
        Returns:
            Base64 encoded Fernet key
        """
        key = Fernet.generate_key()
        return base64.urlsafe_b64encode(key).decode('utf-8')
    
    def verify_encryption(self) -> bool:
        """
        Verify that encryption/decryption is working correctly
        
        Returns:
            True if encryption is working, False otherwise
        """
        try:
            test_data = "test_encryption_verification"
            encrypted = self.encrypt(test_data)
            decrypted = self.decrypt(encrypted)
            
            return test_data == decrypted
            
        except Exception as e:
            logger.error(f"Encryption verification failed: {str(e)}")
            return False

# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None

def get_encryption_service() -> EncryptionService:
    """Get global encryption service instance"""
    global _encryption_service
    
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    
    return _encryption_service

def encrypt_sensitive_data(data: str, context: str = "general") -> str:
    """
    Convenience function to encrypt sensitive data
    
    Args:
        data: Data to encrypt
        context: Context for logging
        
    Returns:
        Encrypted data
    """
    service = get_encryption_service()
    return service.encrypt(data)

def decrypt_sensitive_data(encrypted_data: str, context: str = "general") -> str:
    """
    Convenience function to decrypt sensitive data
    
    Args:
        encrypted_data: Encrypted data
        context: Context for logging
        
    Returns:
        Decrypted data
    """
    service = get_encryption_service()
    return service.decrypt(encrypted_data)

# Database integration functions
def store_encrypted_api_key(db, service_name: str, api_key: str, provider: str = None):
    """
    Store encrypted API key in database
    
    Args:
        db: Database session
        service_name: Name of the service
        api_key: API key to encrypt and store
        provider: API provider name
    """
    from database.models import APIKey
    
    try:
        encryption_service = get_encryption_service()
        encrypted_key = encryption_service.encrypt_api_key(api_key, service_name)
        
        # Check if key already exists
        existing_key = db.query(APIKey).filter(APIKey.service_name == service_name).first()
        
        if existing_key:
            # Update existing key
            existing_key.encrypted_key = encrypted_key
            existing_key.provider = provider
            existing_key.updated_at = datetime.utcnow()
        else:
            # Create new key
            api_key_record = APIKey(
                service_name=service_name,
                encrypted_key=encrypted_key,
                provider=provider
            )
            db.add(api_key_record)
        
        db.commit()
        logger.info(f"API key stored successfully for service: {service_name}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store API key for {service_name}: {str(e)}")
        raise

def retrieve_decrypted_api_key(db, service_name: str) -> Optional[str]:
    """
    Retrieve and decrypt API key from database
    
    Args:
        db: Database session
        service_name: Name of the service
        
    Returns:
        Decrypted API key or None if not found
    """
    from database.models import APIKey
    
    try:
        api_key_record = db.query(APIKey).filter(
            APIKey.service_name == service_name,
            APIKey.is_active == True
        ).first()
        
        if not api_key_record:
            logger.warning(f"No API key found for service: {service_name}")
            return None
        
        encryption_service = get_encryption_service()
        decrypted_key = encryption_service.decrypt_api_key(
            api_key_record.encrypted_key, 
            service_name
        )
        
        return decrypted_key
        
    except Exception as e:
        logger.error(f"Failed to retrieve API key for {service_name}: {str(e)}")
        return None

def delete_api_key(db, service_name: str) -> bool:
    """
    Delete API key from database
    
    Args:
        db: Database session
        service_name: Name of the service
        
    Returns:
        True if deleted successfully, False otherwise
    """
    from database.models import APIKey
    
    try:
        api_key_record = db.query(APIKey).filter(APIKey.service_name == service_name).first()
        
        if api_key_record:
            db.delete(api_key_record)
            db.commit()
            logger.info(f"API key deleted for service: {service_name}")
            return True
        else:
            logger.warning(f"No API key found to delete for service: {service_name}")
            return False
            
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete API key for {service_name}: {str(e)}")
        return False

# Environment setup helper
def setup_encryption_environment():
    """
    Setup encryption environment variables if they don't exist
    This should be called during application initialization
    """
    if not os.getenv("ENCRYPTION_PASSWORD"):
        logger.warning("ENCRYPTION_PASSWORD not set, using default (not secure for production)")
    
    if not os.getenv("ENCRYPTION_SALT"):
        logger.warning("ENCRYPTION_SALT not set, using default (not secure for production)")
    
    # Verify encryption is working
    service = get_encryption_service()
    if not service.verify_encryption():
        raise RuntimeError("Encryption service verification failed")
    
    logger.info("Encryption environment setup completed")