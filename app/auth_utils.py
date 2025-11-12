from functools import wraps
from flask import jsonify
from passlib.context import CryptContext
from flask_jwt_extended import verify_jwt_in_request, get_jwt

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash plaintext password using passlib's pbkdf2_sha256 algorithm"""
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """Verify plaintext password against stored hashed version"""
    return pwd_context.verify(plain, hashed)

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password has at least 8 characters and contains hashtag (#)"""
    if len(password) < 8:
        return (False, "Password must be at least 8 characters long.")
    if '#' not in password:
        return (False, "Password must contain at least one hashtag (#).")
    return (True, "Password is valid.")

def require_admin(fn):
    """require_admin decorator to validate admin-only routes"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        
        if not claims.get('is_admin'):
            return jsonify({'error': 'Admin access required'}), 403
        
        return fn(*args, **kwargs)
    
    return wrapper



