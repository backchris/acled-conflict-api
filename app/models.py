from datetime import datetime, timezone
from sqlalchemy import Index, UniqueConstraint, ForeignKey
from .extensions import db

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # Relationship to Feedback
    feedback = db.relationship('Feedback', backref='user', lazy='select', cascade='all, delete-orphan')

class ConflictData(db.Model):
    __tablename__ = 'conflict_data'
    
    id = db.Column(db.Integer, primary_key=True)
    country = db.Column(db.String(100), nullable=False, index = True) # indexed for faster lookups by country
    admin1 = db.Column(db.String(100), nullable=False)
    population = db.Column(db.Integer, nullable=True)
    events = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationship to Feedback (one-to-many) via explicit FK on Feedback.conflict_id
    # use cascade so removing a conflict removes related feedback if desired
    feedback = db.relationship('Feedback', backref='conflict_data', lazy='select', cascade='all, delete-orphan')
    # Unique index on (country, admin1) for faster lookups, enforces uniqueness, enables safe csv imports
    __table_args__ = (db.UniqueConstraint('country', 'admin1', name='ux_country_admin1'),Index('idx_country', 'country'),) 

class Feedback(db.Model):
    __tablename__ = 'feedback'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False, index=True)
    # Optional explicit foreign key to ConflictData for robust linking
    conflict_id = db.Column(db.Integer, db.ForeignKey('conflict_data.id'), nullable=True, index=True)
    country = db.Column(db.String(100), nullable=False, index=True)
    admin1 = db.Column(db.String(100), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    # Unique index on (country, admin1)
    __table_args__ = (
        Index('idx_country_admin1', 'country', 'admin1'),
    )

class RiskCache(db.Model): #precomputed risk scores for fast retrieval
    __tablename__ = 'risk_cache'

    id = db.Column(db.Integer, primary_key=True)
    country = db.Column(db.String(100), nullable=False)
    admin1 = db.Column(db.String(100), nullable=False)
    avg_score = db.Column(db.Float, nullable=False)
    computed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # Unique index on (country, admin1)
    __table_args__ = (db.UniqueConstraint('country', 'admin1', name='ux_risk_country_admin1'),)
