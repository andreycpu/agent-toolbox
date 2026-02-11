"""Tests for crypto utilities module."""

import pytest
import hashlib
import hmac
import base64
from agent_toolbox.utils.crypto import (
    generate_random_string, generate_api_key, hash_string, hash_file,
    generate_hmac, verify_hmac, encode_base64, decode_base64,
    encode_base64_url, decode_base64_url
)
import tempfile
from pathlib import Path


class TestCryptoUtils:
    """Test cases for crypto utilities."""
    
    def test_generate_random_string(self):
        """Test random string generation."""
        # Test default length
        string1 = generate_random_string()
        assert len(string1) == 32
        assert isinstance(string1, str)
        
        # Test custom length
        string2 = generate_random_string(16)
        assert len(string2) == 16
        
        # Test different strings are generated
        string3 = generate_random_string()
        assert string1 != string3
        
        # Test zero length
        string4 = generate_random_string(0)
        assert len(string4) == 0
    
    def test_generate_api_key(self):
        """Test API key generation."""
        key1 = generate_api_key()
        assert len(key1) == 64  # Default length
        assert isinstance(key1, str)
        
        # Test custom length
        key2 = generate_api_key(32)
        assert len(key2) == 32
        
        # Test different keys are generated
        key3 = generate_api_key()
        assert key1 != key3
        
        # Test prefix
        key4 = generate_api_key(prefix="test_")
        assert key4.startswith("test_")
        assert len(key4) == 69  # 5 (prefix) + 64 (default key)
    
    def test_hash_string(self):
        """Test string hashing."""
        test_string = "Hello, World!"
        
        # Test default algorithm (sha256)
        hash1 = hash_string(test_string)
        expected_sha256 = hashlib.sha256(test_string.encode('utf-8')).hexdigest()
        assert hash1 == expected_sha256
        
        # Test different algorithms
        hash_md5 = hash_string(test_string, algorithm='md5')
        expected_md5 = hashlib.md5(test_string.encode('utf-8')).hexdigest()
        assert hash_md5 == expected_md5
        
        hash_sha1 = hash_string(test_string, algorithm='sha1')
        expected_sha1 = hashlib.sha1(test_string.encode('utf-8')).hexdigest()
        assert hash_sha1 == expected_sha1
        
        # Test consistency
        hash2 = hash_string(test_string)
        assert hash1 == hash2
        
        # Test different strings produce different hashes
        hash3 = hash_string("Different string")
        assert hash1 != hash3
    
    def test_hash_file(self):
        """Test file hashing."""
        test_content = "This is test file content for hashing."
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(test_content)
            temp_file = f.name
        
        try:
            # Test file hashing
            file_hash = hash_file(temp_file)
            expected_hash = hashlib.sha256(test_content.encode('utf-8')).hexdigest()
            assert file_hash == expected_hash
            
            # Test different algorithms
            md5_hash = hash_file(temp_file, algorithm='md5')
            expected_md5 = hashlib.md5(test_content.encode('utf-8')).hexdigest()
            assert md5_hash == expected_md5
            
            # Test with Path object
            path_hash = hash_file(Path(temp_file))
            assert path_hash == file_hash
            
        finally:
            Path(temp_file).unlink()
    
    def test_hash_file_not_found(self):
        """Test hashing non-existent file."""
        with pytest.raises(FileNotFoundError):
            hash_file("/path/that/does/not/exist.txt")
    
    def test_hmac_operations(self):
        """Test HMAC generation and verification."""
        key = "secret_key"
        message = "This is a test message"
        
        # Test HMAC generation
        signature = generate_hmac(key, message)
        assert isinstance(signature, str)
        assert len(signature) > 0
        
        # Test HMAC verification
        assert verify_hmac(key, message, signature) is True
        
        # Test wrong key
        assert verify_hmac("wrong_key", message, signature) is False
        
        # Test wrong message
        assert verify_hmac(key, "wrong_message", signature) is False
        
        # Test wrong signature
        assert verify_hmac(key, message, "wrong_signature") is False
        
        # Test different algorithms
        signature_sha1 = generate_hmac(key, message, algorithm='sha1')
        assert verify_hmac(key, message, signature_sha1, algorithm='sha1') is True
        assert signature != signature_sha1  # Different algorithms produce different signatures
    
    def test_base64_operations(self):
        """Test Base64 encoding and decoding."""
        test_data = "Hello, Base64 encoding!"
        
        # Test standard Base64
        encoded = encode_base64(test_data)
        assert isinstance(encoded, str)
        decoded = decode_base64(encoded)
        assert decoded == test_data
        
        # Test with bytes input
        test_bytes = test_data.encode('utf-8')
        encoded_bytes = encode_base64(test_bytes)
        decoded_bytes = decode_base64(encoded_bytes)
        assert decoded_bytes == test_data
        
        # Test URL-safe Base64
        url_encoded = encode_base64_url(test_data)
        url_decoded = decode_base64_url(url_encoded)
        assert url_decoded == test_data
        
        # URL-safe should be different from standard for certain characters
        test_special = "Test with + and / characters for URL safety"
        standard_encoded = encode_base64(test_special)
        url_safe_encoded = encode_base64_url(test_special)
        
        # Both should decode to the same content
        assert decode_base64(standard_encoded) == test_special
        assert decode_base64_url(url_safe_encoded) == test_special
    
    def test_base64_invalid_input(self):
        """Test Base64 decoding with invalid input."""
        with pytest.raises(Exception):  # Should raise decoding error
            decode_base64("Invalid Base64!")
        
        with pytest.raises(Exception):  # Should raise decoding error
            decode_base64_url("Invalid Base64 URL!")
    
    def test_hash_empty_string(self):
        """Test hashing empty string."""
        empty_hash = hash_string("")
        expected = hashlib.sha256(b'').hexdigest()
        assert empty_hash == expected
    
    def test_hmac_empty_message(self):
        """Test HMAC with empty message."""
        key = "test_key"
        signature = generate_hmac(key, "")
        assert verify_hmac(key, "", signature) is True
    
    def test_base64_empty_string(self):
        """Test Base64 with empty string."""
        encoded = encode_base64("")
        decoded = decode_base64(encoded)
        assert decoded == ""
        
        url_encoded = encode_base64_url("")
        url_decoded = decode_base64_url(url_encoded)
        assert url_decoded == ""