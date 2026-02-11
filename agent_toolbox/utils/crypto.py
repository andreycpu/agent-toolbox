"""Cryptographic utilities for basic encryption, hashing, and tokens."""

import hashlib
import hmac
import secrets
import base64
from typing import Union, Optional


def generate_random_string(length: int = 32, url_safe: bool = True) -> str:
    """Generate cryptographically secure random string."""
    if url_safe:
        return secrets.token_urlsafe(length)[:length]
    else:
        return secrets.token_hex(length//2)


def generate_api_key(length: int = 32) -> str:
    """Generate API key with standard format."""
    return "atb_" + generate_random_string(length - 4, url_safe=True)


def hash_string(text: str, algorithm: str = "sha256") -> str:
    """Hash string using specified algorithm."""
    if algorithm not in hashlib.algorithms_available:
        raise ValueError(f"Algorithm {algorithm} not available")
        
    hasher = hashlib.new(algorithm)
    hasher.update(text.encode('utf-8'))
    return hasher.hexdigest()


def hash_file(file_path: str, algorithm: str = "sha256", chunk_size: int = 8192) -> str:
    """Hash file contents using specified algorithm."""
    if algorithm not in hashlib.algorithms_available:
        raise ValueError(f"Algorithm {algorithm} not available")
        
    hasher = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
            
    return hasher.hexdigest()


def generate_hmac(message: str, key: str, algorithm: str = "sha256") -> str:
    """Generate HMAC for message using key."""
    return hmac.new(
        key.encode('utf-8'),
        message.encode('utf-8'),
        getattr(hashlib, algorithm)
    ).hexdigest()


def verify_hmac(message: str, key: str, signature: str, algorithm: str = "sha256") -> bool:
    """Verify HMAC signature."""
    expected = generate_hmac(message, key, algorithm)
    return hmac.compare_digest(expected, signature)


def encode_base64(data: Union[str, bytes]) -> str:
    """Encode data as base64 string."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.b64encode(data).decode('ascii')


def decode_base64(encoded: str) -> bytes:
    """Decode base64 string to bytes."""
    return base64.b64decode(encoded)


def encode_base64_url(data: Union[str, bytes]) -> str:
    """Encode data as URL-safe base64 string."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return base64.urlsafe_b64encode(data).decode('ascii').rstrip('=')


def decode_base64_url(encoded: str) -> bytes:
    """Decode URL-safe base64 string to bytes."""
    # Add padding if needed
    padding = 4 - (len(encoded) % 4)
    if padding != 4:
        encoded += '=' * padding
    return base64.urlsafe_b64decode(encoded)