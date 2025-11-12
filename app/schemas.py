from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List
"""
Use Pydantic model schemas to validate incoming request data and serialize outgoing responses
"""


# ---Auhthorization Schemas---
class RegisterRequest(BaseModel):
    """User registration request model"""
    username: str = Field(..., min_length=3, description="Username must be 3+ characters")
    password: str = Field(..., min_length=8, description="Password must be 8+ characters")
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError('Username must be alphanumeric')
        return v
    
    @field_validator('password')
    @classmethod
    def password_has_hash(cls, v):
        """Requirement - 'Password hashtag required'"""
        if '#' not in v:
            raise ValueError('Password must contain at least one special character (#)')
        return v
    
class LoginRequest(BaseModel):
    """User login request model"""
    username: str
    password: str

class UserResponse(BaseModel):
    """User response model - excludes password hash for security"""
    id: int
    username: str
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True  # Makes it compatible with SQLAlchemy


class TokenResponse(BaseModel):
    """JWT token response from login endpoint"""
    access_token: str
    token_type: str = "Bearer"

# ---Conflict Data Schemas---
class ConflictDataRow(BaseModel):
    """Single conflict data record (for list/response)."""
    id: int
    country: str
    admin1: str
    population: int | None
    events: int
    score: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True  # Convert ORM objects


class ConflictDataListResponse(BaseModel):
    """Paginated list of conflict data."""
    page: int
    per_page: int
    total: int
    data: List[ConflictDataRow]


class CountryDataResponse(BaseModel):
    """Conflict data grouped by country."""
    country: str
    admin1_entries: List[ConflictDataRow]


class RiskScoreResponse(BaseModel):
    """Average risk score for a country-admin1 combination using background job"""
    country: str
    admin1: str
    avg_score: float
    computed_at: datetime
    
    class Config:
        from_attributes = True

# ---Feedback Schemas---
class FeedbackCreateRequest(BaseModel):
    """User feedback submission (POST)"""
    text: str = Field(..., min_length=20, max_length=600, description="Feedback must be 20-600 characters")


class FeedbackResponse(BaseModel):
    """Feedback response (GET)"""
    id: int
    user_id: int
    country: str
    admin1: str
    text: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# ---Delete Schema---
class DeleteRequest(BaseModel):
    """Request to delete a conflict data record - by admins only"""
    country: str = Field(..., min_length=1)
    admin1: str = Field(..., min_length=1)


class DeleteResponse(BaseModel):
    """Response after deletion"""
    deleted: int = Field(..., description="Number of records deleted")