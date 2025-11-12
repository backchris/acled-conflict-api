"""Test auth utility helper functions"""
from app.auth_utils import hash_password, verify_password, validate_password, require_admin
import pytest


def test_hash_password():
    """Test hash_password creates a valid hash"""
    password = 'secure#password1'
    hashed = hash_password(password)
    
    # Hash should be a string and different from plaintext
    assert isinstance(hashed, str)
    assert hashed != password
    # Hash should start with pbkdf2_sha256 scheme identifier
    assert hashed.startswith('$pbkdf2-sha256$')


def test_verify_password_valid():
    """Test verify_password returns True for correct password"""
    password = 'secure#password1'
    hashed = hash_password(password)
    
    assert verify_password(password, hashed) is True


def test_verify_password_invalid():
    """Test verify_password returns False for incorrect password"""
    password = 'secure#password1'
    hashed = hash_password(password)
    wrong_password = 'wrong#password1'
    
    assert verify_password(wrong_password, hashed) is False


def test_validate_password_valid():
    """Test validate_password accepts valid password"""
    is_valid, message = validate_password('secure#password1')
    
    assert is_valid is True
    assert message == 'Password is valid.'


def test_validate_password_too_short():
    """Test validate_password rejects password shorter than 8 chars"""
    is_valid, message = validate_password('short#1')
    
    assert is_valid is False
    assert 'at least 8 characters' in message


def test_validate_password_missing_hashtag():
    """Test validate_password rejects password without hashtag"""
    is_valid, message = validate_password('securepassword1')
    
    assert is_valid is False
    assert 'hashtag' in message


def test_require_admin_decorator_exists():
    """Test require_admin decorator can be imported and used to wrap around functions"""
    # Create a simple test function
    @require_admin
    def test_function():
        return "success"
    
    # Decorator should preserve function name with @wraps
    assert test_function.__name__ == 'test_function'
