"""Tests for conflict data routes"""
import pytest
from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import ConflictData, User


@pytest.fixture
def app():
    """Create and configure a test app"""
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    with app.app_context():
        pass  # Ensure app context is active
    return app.test_client()


@pytest.fixture
def sample_conflict_data(app):
    """Create sample conflict data for testing."""
    conflicts = [
        ConflictData(
            country="Kenya",
            admin1="Nairobi",
            population=5000000,
            events=45,
            score=7
        ),
        ConflictData(
            country="Kenya",
            admin1="Mombasa",
            population=1200000,
            events=12,
            score=4
        ),
        ConflictData(
            country="Kenya",
            admin1="Kisumu",
            population=800000,
            events=8,
            score=3
        ),
        ConflictData(
            country="Uganda",
            admin1="Kampala",
            population=1500000,
            events=25,
            score=5
        ),
        ConflictData(
            country="Uganda",
            admin1="Jinja",
            population=450000,
            events=5,
            score=2
        ),
        ConflictData(
            country="Tanzania",
            admin1="Dar es Salaam",
            population=6000000,
            events=35,
            score=6
        ),
    ]
    db.session.add_all(conflicts)
    db.session.commit()
    return conflicts


class TestGetAllConflicts:
    """Tests for GET /conflictdata endpoint (paginated list)"""

    def test_get_all_conflicts_default_pagination(self, client, sample_conflict_data):
        """Test paginated list with default page and per_page"""
        response = client.get('/conflictdata')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['page'] == 1
        assert data['per_page'] == 20
        assert data['total'] == 6
        assert len(data['data']) == 6
        
        # Verify data is ordered by country and admin1 - alphabetically
        assert data['data'][0]['country'] == 'Kenya'
        assert data['data'][0]['admin1'] == 'Kisumu' 

    def test_get_all_conflicts_custom_pagination(self, client, sample_conflict_data):
        """Test paginated list with custom page and per_page"""
        response = client.get('/conflictdata?page=1&per_page=2')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['page'] == 1
        assert data['per_page'] == 2
        assert data['total'] == 6
        assert len(data['data']) == 2

    def test_get_all_conflicts_second_page(self, client, sample_conflict_data):
        """Test second page of paginated results"""
        response = client.get('/conflictdata?page=2&per_page=2')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['page'] == 2
        assert len(data['data']) == 2
        # Should get different entries from page 1
        assert data['data'][0]['admin1'] != 'Kisumu'

    def test_get_all_conflicts_invalid_page_zero(self, client, sample_conflict_data):
        """Test with invalid page number (zero)"""
        response = client.get('/conflictdata?page=0')
        assert response.status_code == 400
        assert 'Invalid pagination parameters' in response.get_json()['error']

    def test_get_all_conflicts_invalid_per_page_negative(self, client, sample_conflict_data):
        """Test with invalid per_page (negative)"""
        response = client.get('/conflictdata?per_page=-1')
        assert response.status_code == 400
        assert 'Invalid pagination parameters' in response.get_json()['error']

    def test_get_all_conflicts_per_page_exceeds_max(self, client, sample_conflict_data):
        """Test with per_page exceeding maximum (100)"""
        response = client.get('/conflictdata?per_page=101')
        assert response.status_code == 400
        assert 'Invalid pagination parameters' in response.get_json()['error']

    def test_get_all_conflicts_empty_database(self, client):
        """Test paginated list with no data"""
        response = client.get('/conflictdata')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['page'] == 1
        assert data['total'] == 0
        assert len(data['data']) == 0


class TestGetCountryConflicts:
    """Tests for GET /conflictdata/<countries> endpoint (single or multiple countries)."""

    def test_get_single_country(self, client, sample_conflict_data):
        """Test getting data for a single country"""
        response = client.get('/conflictdata/Kenya')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['country'] == 'Kenya'
        assert len(data['admin1_entries']) == 3
        
        # Verify all entries are from Kenya
        for entry in data['admin1_entries']:
            assert entry['country'] == 'Kenya'

    def test_get_multiple_countries(self, client, sample_conflict_data):
        """Test getting data for multiple countries"""
        response = client.get('/conflictdata/Kenya,Uganda')
        assert response.status_code == 200
        
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 2
        
        # Verify countries in response
        countries = {item['country'] for item in data}
        assert 'Kenya' in countries
        assert 'Uganda' in countries

    def test_get_multiple_countries_with_spaces(self, client, sample_conflict_data):
        """Test multiple countries with spaces around commas"""
        response = client.get('/conflictdata/Kenya, Uganda, Tanzania')
        assert response.status_code == 200
        
        data = response.get_json()
        assert len(data) == 3

    def test_get_country_not_found(self, client, sample_conflict_data):
        """Test requesting data for non-existent country"""
        response = client.get('/conflictdata/NonexistentCountry')
        assert response.status_code == 404
        assert 'No conflict data found' in response.get_json()['error']

    def test_get_mixed_existing_nonexisting_countries(self, client, sample_conflict_data):
        """Test with mix of existing and non-existent countries."""
        response = client.get('/conflictdata/Kenya,NonexistentCountry')
        assert response.status_code == 200
        
        data = response.get_json()
        # Should return only Kenya (existing country)
        assert len(data) == 2  
        
        kenya_data = next((item for item in data if item['country'] == 'Kenya'), None)
        assert kenya_data is not None
        assert len(kenya_data['admin1_entries']) == 3

    def test_country_data_structure(self, client, sample_conflict_data):
        """Test the structure of returned country data"""
        response = client.get('/conflictdata/Uganda')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'country' in data
        assert 'admin1_entries' in data
        
        # Verify admin1_entries structure
        entry = data['admin1_entries'][0]
        assert 'country' in entry
        assert 'admin1' in entry
        assert 'population' in entry
        assert 'events' in entry
        assert 'score' in entry

    def test_get_country_empty_string(self, client, sample_conflict_data):
        """Test with empty country string"""
        response = client.get('/conflictdata/')
        # This will match the /<countries> pattern with empty string
        assert response.status_code == 404
