"""Test Pydantic schema validation."""
from app.schemas import RegisterRequest, LoginRequest, TokenResponse, FeedbackCreateRequest
from pydantic import ValidationError
import pytest


def test_register_request_valid():
    """Test RegisterRequest accepts valid credentials"""
    req = RegisterRequest(username='alice', password='secure#password1')
    assert req.username == 'alice'
    assert req.password == 'secure#password1'


def test_register_request_invalid_username_not_alphanumeric():
    """Test RegisterRequest rejects non-alphanumeric username"""
    with pytest.raises(ValidationError):
        RegisterRequest(username='alice@123', password='secure#password1')


def test_register_request_password_missing_hash():
    """Test RegisterRequest rejects password without a hashtag (#)"""
    with pytest.raises(ValidationError):
        RegisterRequest(username='alice', password='securepassword1')


def test_register_request_password_too_short():
    """Test RegisterRequest rejects password shorter than 8 chars"""
    with pytest.raises(ValidationError):
        RegisterRequest(username='alice', password='sec#pwd')


def test_login_request_valid():
    """Test LoginRequest accepts valid credentials"""
    req = LoginRequest(username='alice', password='secure#password1')
    assert req.username == 'alice'
    assert req.password == 'secure#password1'


def test_token_response_valid():
    """Test TokenResponse creates valid token response"""
    token = TokenResponse(access_token='fake.jwt.token')
    assert token.access_token == 'fake.jwt.token'
    assert token.token_type == 'Bearer'


def test_feedback_create_request_valid():
    """Test FeedbackCreateRequest accepts valid feedback text"""
    req = FeedbackCreateRequest(text='This is valid feedback with more than 20 characters.')
    assert len(req.text) > 20


def test_feedback_create_request_text_too_short():
    """Test FeedbackCreateRequest rejects text shorter than 20 chars"""
    with pytest.raises(ValidationError):
        FeedbackCreateRequest(text='short')


def test_feedback_create_request_text_too_long():
    """Test FeedbackCreateRequest rejects text longer than 600 chars"""
    long_text = 'a' * 601
    with pytest.raises(ValidationError):
        FeedbackCreateRequest(text=long_text)
