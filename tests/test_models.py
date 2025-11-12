"""Test app factory and models"""
from app import create_app
from app.config import Config
from app.extensions import db
from app.models import User, ConflictData, Feedback
import pytest


@pytest.fixture
def app():
    """Create app with fresh test database."""
    app = create_app(Config)
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_app_creates_tables():
    """Test app creates all 4 tables."""
    app = create_app(Config)
    with app.app_context():
        tables = db.inspect(db.engine).get_table_names()
        assert 'users' in tables
        assert 'conflict_data' in tables
        assert 'feedback' in tables
        assert 'risk_cache' in tables


def test_user_creation(app):
    """Test User model creation."""
    with app.app_context():
        user = User(username='chris', password_hash='hash')
        db.session.add(user)
        db.session.commit()
        assert user.id is not None
        assert user.username == 'chris'


def test_conflict_data_creation(app):
    """Test ConflictData model creation."""
    with app.app_context():
        conflict = ConflictData(country='Nigeria', admin1='Lagos', events=10, score=5.0)
        db.session.add(conflict)
        db.session.commit()
        assert conflict.id is not None
        assert conflict.country == 'Nigeria'


def test_feedback_with_relationships(app):
    """Test Feedback creation with User and ConflictData relationships."""
    with app.app_context():
        user = User(username='daisy', password_hash='hash')
        conflict = ConflictData(country='Kenya', admin1='Nairobi', events=5, score=3.0)
        db.session.add_all([user, conflict])
        db.session.commit()
        
        feedback = Feedback(
            user_id=user.id,
            conflict_id=conflict.id,
            country='Kenya',
            admin1='Nairobi',
            text='Test feedback'
        )
        db.session.add(feedback)
        db.session.commit()
        
        # Verify relationships work
        assert feedback.user.username == 'daisy'
        assert feedback.conflict_data.country == 'Kenya'
        assert len(user.feedback) == 1
        assert len(conflict.feedback) == 1


def test_cascade_delete_user(app):
    """Test deleting User cascades to Feedback."""
    with app.app_context():
        user = User(username='charlie', password_hash='hash')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        
        feedback = Feedback(
            user_id=user_id,
            country='Uganda',
            admin1='Kampala',
            text='Feedback'
        )
        db.session.add(feedback)
        db.session.commit()
        
        db.session.delete(user)
        db.session.commit()
        
        assert User.query.get(user_id) is None
        assert Feedback.query.filter_by(user_id=user_id).first() is None


def test_cascade_delete_conflict(app):
    """Test deleting ConflictData cascades to Feedback."""
    with app.app_context():
        user = User(username='diana', password_hash='hash')
        conflict = ConflictData(country='Sudan', admin1='Khartoum', events=15, score=6.0)
        db.session.add_all([user, conflict])
        db.session.commit()
        conflict_id = conflict.id
        
        feedback = Feedback(
            user_id=user.id,
            conflict_id=conflict_id,
            country='Sudan',
            admin1='Khartoum',
            text='Feedback'
        )
        db.session.add(feedback)
        db.session.commit()
        
        db.session.delete(conflict)
        db.session.commit()
        
        assert ConflictData.query.get(conflict_id) is None
        assert Feedback.query.filter_by(conflict_id=conflict_id).first() is None
