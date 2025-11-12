"""Test that app factory creates all database tables."""
from app import create_app
from app.config import TestingConfig
from app.extensions import db


def test_app_creates_tables():
    """Test that create_app() calls db.create_all() and creates all tables."""
    app = create_app(TestingConfig)
    
    with app.app_context():
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        # Verify all 4 model tables exist
        assert 'users' in tables
        assert 'conflict_data' in tables
        assert 'feedback' in tables
        assert 'risk_cache' in tables


