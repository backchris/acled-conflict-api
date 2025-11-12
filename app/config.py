import os
from datetime import timedelta

class Config:
    DEBUG = True
    TESTING = False
    # Use PostgreSQL via DATABASE_URL if provided, otherwise SQLite for local dev
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///acled_dev.db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)