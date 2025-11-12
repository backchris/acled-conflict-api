"""Test authentication HTTP routes - register and login endpoints."""
import pytest
from app import create_app
from app.config import TestingConfig
from app.extensions import db


@pytest.fixture
def app():
    """Create app with testing config."""
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_register_success(client):
    """Test successful user registration returns 201."""
    response = client.post('/auth/register',
        json={'username': 'alice', 'password': 'secure#password1'})
    
    assert response.status_code == 201
    data = response.get_json()
    assert data['username'] == 'alice'
    assert data['message'] == 'User successfully registered'


def test_register_duplicate_username(client):
    """Test duplicate username returns 409."""
    client.post('/auth/register',
        json={'username': 'alice', 'password': 'secure#password1'})
    
    response = client.post('/auth/register',
        json={'username': 'alice', 'password': 'another#pass2'})
    
    assert response.status_code == 409


def test_register_invalid_password(client):
    """Test invalid password returns 400."""
    response = client.post('/auth/register',
        json={'username': 'bob', 'password': 'short#1'})
    
    assert response.status_code == 400


def test_login_success(client):
    """Test successful login returns JWT token."""
    client.post('/auth/register',
        json={'username': 'alice', 'password': 'secure#password1'})
    
    response = client.post('/auth/login',
        json={'username': 'alice', 'password': 'secure#password1'})
    
    assert response.status_code == 200
    data = response.get_json()
    assert 'access_token' in data
    assert data['token_type'] == 'Bearer'


def test_login_wrong_password(client):
    """Test wrong password returns 401."""
    client.post('/auth/register',
        json={'username': 'alice', 'password': 'secure#password1'})
    
    response = client.post('/auth/login',
        json={'username': 'alice', 'password': 'wrong#password1'})
    
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    """Test non-existent user returns 401."""
    response = client.post('/auth/login',
        json={'username': 'bob', 'password': 'secure#password1'})
    
    assert response.status_code == 401

