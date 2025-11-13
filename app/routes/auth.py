"""Authentication HTTP routes - register and login"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token
from flasgger import swag_from
import os
from app.models import User
from app.extensions import db
from app.auth_utils import validate_password, hash_password, verify_password
from app.schemas import RegisterRequest, UserResponse, LoginRequest, TokenResponse

# Get absolute path to specs directory
_specs_dir = os.path.join(os.path.dirname(__file__), '..', 'specs')

# Create Blueprint for auth routes - keeps related routes together
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
@swag_from(os.path.join(_specs_dir, 'auth_register.yaml'))
def register():
    """Register a new user with username and password"""
    try:
        # 1. Validate request with Pydantic schema (schemas.py)
        data = request.get_json()
        req = RegisterRequest(**data)

        # 2. Check if username exists in DB
        existing_user = User.query.filter_by(username=req.username).first()
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 409

        # 3. Validate password requirements using validate_password from auth_utils.py
        is_valid, error_msg = validate_password(req.password)
        if not is_valid:
            raise ValueError(error_msg)
        
        # 4. Hash password and create new user with hashed password (irreversible)
        hashed_password = hash_password(req.password)
        new_user = User(username=req.username, password_hash=hashed_password)

        # 5. Save new user to DB
        db.session.add(new_user)
        db.session.commit()

        # 6. Return user response using Pydantic schema (schemas.py) to serialize response
        user_response = UserResponse.model_validate(new_user)
        response_data = user_response.model_dump()
        response_data['message'] = 'User successfully registered'
        return jsonify(response_data), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500
    
@auth_bp.route('/login', methods=['POST'])
@swag_from(os.path.join(_specs_dir, 'auth_login.yaml'))
def login():
    """Login with credentials to receive JWT token"""
    try:
        # 1. Validate login request with Pydantic schema (schemas.py)
        data = request.get_json()
        req = LoginRequest(**data)

        # 2. Query user by username
        user = User.query.filter_by(username=req.username).first()

        # 3. Check if user exists and verify password
        if not user or not verify_password(req.password, user.password_hash):
            return jsonify({'error': 'Invalid username or password'}), 401

        # 4. Generate JWT token
        token = create_access_token(
            identity=str(user.id),
            additional_claims={'is_admin': user.is_admin})
    
        # 5. Return token, verified with TokenResponse Pydantic schema
        token_response = TokenResponse(access_token=token)
        return jsonify(token_response.model_dump()), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500