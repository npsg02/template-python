"""Encryption utilities for securing API keys."""

import base64
import os
from typing import str as String

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..config import settings


class EncryptionManager:
    """Manages encryption and decryption of sensitive data."""
    
    def __init__(self, encryption_key: str = None):
        """Initialize encryption manager.
        
        Args:
            encryption_key: Base64 encoded key or passphrase
        """
        if encryption_key is None:
            encryption_key = settings.security.encryption_key
            
        # If the key looks like a Fernet key (44 chars, base64), use it directly
        if len(encryption_key) == 44 and self._is_base64(encryption_key):
            self._fernet = Fernet(encryption_key.encode())
        else:
            # Generate key from passphrase
            key = self._derive_key_from_passphrase(encryption_key.encode())
            self._fernet = Fernet(key)
    
    def _is_base64(self, s: str) -> bool:
        """Check if string is valid base64."""
        try:
            base64.b64decode(s)
            return True
        except Exception:
            return False
    
    def _derive_key_from_passphrase(self, passphrase: bytes, salt: bytes = None) -> bytes:
        """Derive encryption key from passphrase."""
        if salt is None:
            # Use a fixed salt for consistency (in production, use proper key management)
            salt = b"openai_proxy_salt_2024"
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(passphrase))
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64 encoded encrypted string
        """
        if not plaintext:
            return ""
        
        encrypted_bytes = self._fernet.encrypt(plaintext.encode())
        return base64.b64encode(encrypted_bytes).decode()
    
    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt encrypted string.
        
        Args:
            encrypted_text: Base64 encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        if not encrypted_text:
            return ""
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_text.encode())
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {e}")
    
    def mask_key(self, api_key: str, visible_chars: int = 4) -> str:
        """Mask API key for logging purposes.
        
        Args:
            api_key: API key to mask
            visible_chars: Number of characters to show at the end
            
        Returns:
            Masked API key string
        """
        if not api_key or len(api_key) <= visible_chars:
            return "***"
        
        return "*" * (len(api_key) - visible_chars) + api_key[-visible_chars:]


# Global encryption manager instance
encryption_manager = EncryptionManager()


def generate_fernet_key() -> str:
    """Generate a new Fernet key for encryption."""
    return Fernet.generate_key().decode()


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key."""
    return encryption_manager.encrypt(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key."""
    return encryption_manager.decrypt(encrypted_key)


def mask_api_key(api_key: str) -> str:
    """Mask an API key for logging."""
    return encryption_manager.mask_key(api_key)