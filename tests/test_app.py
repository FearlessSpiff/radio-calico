import pytest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, init_db, get_user_fingerprint


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    # Use a temporary database for testing
    db_fd, db_path = tempfile.mkstemp()
    app.config['TESTING'] = True

    # Override database URL to use SQLite for tests
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'

    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

    os.close(db_fd)
    os.unlink(db_path)


class TestRoutes:
    """Test Flask route endpoints"""

    def test_index_route(self, client):
        """Test that index route returns 200 and HTML"""
        response = client.get('/')
        assert response.status_code == 200
        assert b'<!DOCTYPE html>' in response.data
        assert b'Radio Calico' in response.data

    def test_index_contains_minified_assets(self, client):
        """Test that index loads minified CSS and JS"""
        response = client.get('/')
        assert b'style.min.css' in response.data
        assert b'script.min.js' in response.data

    @patch('app.requests.get')
    def test_metadata_endpoint_success(self, mock_get, client):
        """Test successful metadata fetch"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'artist': 'Test Artist',
            'title': 'Test Song',
            'album': 'Test Album'
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        response = client.get('/api/metadata')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['artist'] == 'Test Artist'
        assert data['title'] == 'Test Song'

    @patch('app.requests.get')
    def test_metadata_endpoint_timeout(self, mock_get, client):
        """Test metadata endpoint handles timeouts"""
        mock_get.side_effect = Exception('Timeout')

        response = client.get('/api/metadata')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data


class TestRatings:
    """Test rating functionality"""

    def test_get_ratings_new_song(self, client):
        """Test getting ratings for a new song"""
        response = client.get('/api/ratings/test_song_id')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['thumbs_up'] == 0
        assert data['thumbs_down'] == 0
        assert data['user_rating'] is None

    def test_submit_thumbs_up(self, client):
        """Test submitting a thumbs up rating"""
        rating_data = {
            'song_id': 'test_song_123',
            'artist': 'Test Artist',
            'title': 'Test Song',
            'rating': 1
        }
        response = client.post('/api/rate',
                               data=json.dumps(rating_data),
                               content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        # Verify the rating was saved
        response = client.get('/api/ratings/test_song_123')
        data = json.loads(response.data)
        assert data['thumbs_up'] == 1
        assert data['user_rating'] == 1

    def test_submit_thumbs_down(self, client):
        """Test submitting a thumbs down rating"""
        rating_data = {
            'song_id': 'test_song_456',
            'artist': 'Test Artist',
            'title': 'Test Song',
            'rating': -1
        }
        response = client.post('/api/rate',
                               data=json.dumps(rating_data),
                               content_type='application/json')
        assert response.status_code == 200

        # Verify the rating was saved
        response = client.get('/api/ratings/test_song_456')
        data = json.loads(response.data)
        assert data['thumbs_down'] == 1
        assert data['user_rating'] == -1

    def test_update_rating(self, client):
        """Test updating an existing rating"""
        song_id = 'test_song_update'

        # Submit initial rating
        rating_data = {
            'song_id': song_id,
            'artist': 'Test Artist',
            'title': 'Test Song',
            'rating': 1
        }
        client.post('/api/rate',
                   data=json.dumps(rating_data),
                   content_type='application/json')

        # Update to thumbs down
        rating_data['rating'] = -1
        response = client.post('/api/rate',
                               data=json.dumps(rating_data),
                               content_type='application/json')
        assert response.status_code == 200

        # Verify the rating was updated
        response = client.get(f'/api/ratings/{song_id}')
        data = json.loads(response.data)
        assert data['thumbs_up'] == 0
        assert data['thumbs_down'] == 1
        assert data['user_rating'] == -1

    def test_remove_rating(self, client):
        """Test removing a rating"""
        song_id = 'test_song_remove'

        # Submit initial rating
        rating_data = {
            'song_id': song_id,
            'artist': 'Test Artist',
            'title': 'Test Song',
            'rating': 1
        }
        client.post('/api/rate',
                   data=json.dumps(rating_data),
                   content_type='application/json')

        # Remove rating
        rating_data['rating'] = 0
        response = client.post('/api/rate',
                               data=json.dumps(rating_data),
                               content_type='application/json')
        assert response.status_code == 200

        # Verify the rating was removed
        response = client.get(f'/api/ratings/{song_id}')
        data = json.loads(response.data)
        assert data['thumbs_up'] == 0
        assert data['thumbs_down'] == 0
        assert data['user_rating'] is None

    def test_invalid_rating_value(self, client):
        """Test submitting invalid rating value"""
        rating_data = {
            'song_id': 'test_invalid',
            'artist': 'Test Artist',
            'title': 'Test Song',
            'rating': 5  # Invalid
        }
        response = client.post('/api/rate',
                               data=json.dumps(rating_data),
                               content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_missing_required_fields(self, client):
        """Test submitting rating with missing fields"""
        rating_data = {
            'song_id': 'test_missing',
            'rating': 1
            # Missing artist and title
        }
        response = client.post('/api/rate',
                               data=json.dumps(rating_data),
                               content_type='application/json')
        assert response.status_code == 400


class TestCacheHeaders:
    """Test Cache-Control headers"""

    def test_api_no_cache_headers(self, client):
        """Test that API endpoints have no-cache headers"""
        response = client.get('/api/ratings/test')
        assert 'Cache-Control' in response.headers
        assert 'no-cache' in response.headers.get('Cache-Control', '')
        assert 'no-store' in response.headers.get('Cache-Control', '')

    def test_html_short_cache(self, client):
        """Test that HTML pages have short cache"""
        response = client.get('/')
        assert 'Cache-Control' in response.headers
        cache_control = response.headers.get('Cache-Control', '')
        assert 'max-age=300' in cache_control or 'public' in cache_control


class TestUserFingerprinting:
    """Test user fingerprinting functionality"""

    def test_user_fingerprint_generation(self, client):
        """Test that user fingerprint is generated correctly"""
        with app.test_request_context(
            '/',
            environ_base={'REMOTE_ADDR': '127.0.0.1'},
            headers={'User-Agent': 'TestBrowser/1.0'}
        ):
            fingerprint = get_user_fingerprint()
            assert isinstance(fingerprint, str)
            assert len(fingerprint) == 64  # SHA-256 hash length

    def test_different_ips_different_fingerprints(self, client):
        """Test that different IPs produce different fingerprints"""
        with app.test_request_context(
            '/',
            environ_base={'REMOTE_ADDR': '127.0.0.1'},
            headers={'User-Agent': 'TestBrowser/1.0'}
        ):
            fingerprint1 = get_user_fingerprint()

        with app.test_request_context(
            '/',
            environ_base={'REMOTE_ADDR': '192.168.1.1'},
            headers={'User-Agent': 'TestBrowser/1.0'}
        ):
            fingerprint2 = get_user_fingerprint()

        assert fingerprint1 != fingerprint2

    def test_x_forwarded_for_header(self, client):
        """Test that X-Forwarded-For header is used for fingerprinting"""
        with app.test_request_context(
            '/',
            environ_base={'REMOTE_ADDR': '127.0.0.1'},
            headers={
                'User-Agent': 'TestBrowser/1.0',
                'X-Forwarded-For': '203.0.113.1'
            }
        ):
            fingerprint = get_user_fingerprint()
            assert isinstance(fingerprint, str)


class TestDatabase:
    """Test database operations"""

    def test_database_initialization(self, client):
        """Test that database initializes correctly"""
        # Database should be initialized by fixture
        # Try to insert and retrieve a rating
        rating_data = {
            'song_id': 'db_test',
            'artist': 'DB Test Artist',
            'title': 'DB Test Song',
            'rating': 1
        }
        response = client.post('/api/rate',
                               data=json.dumps(rating_data),
                               content_type='application/json')
        assert response.status_code == 200

        # Verify we can retrieve it
        response = client.get('/api/ratings/db_test')
        assert response.status_code == 200

    def test_unique_constraint(self, client):
        """Test that one user can only rate a song once"""
        song_id = 'unique_test'
        rating_data = {
            'song_id': song_id,
            'artist': 'Test Artist',
            'title': 'Test Song',
            'rating': 1
        }

        # First rating should succeed
        response = client.post('/api/rate',
                               data=json.dumps(rating_data),
                               content_type='application/json')
        assert response.status_code == 200

        # Second rating should update, not create duplicate
        rating_data['rating'] = -1
        response = client.post('/api/rate',
                               data=json.dumps(rating_data),
                               content_type='application/json')
        assert response.status_code == 200

        # Verify only one rating exists
        response = client.get(f'/api/ratings/{song_id}')
        data = json.loads(response.data)
        assert data['thumbs_down'] == 1
        assert data['thumbs_up'] == 0


class TestErrorHandling:
    """Test error handling"""

    def test_invalid_song_id(self, client):
        """Test handling of invalid song ID"""
        response = client.get('/api/ratings/')
        # Should return 404 for missing song_id
        assert response.status_code == 404

    def test_malformed_json(self, client):
        """Test handling of malformed JSON in POST request"""
        response = client.post('/api/rate',
                               data='invalid json',
                               content_type='application/json')
        # Should handle gracefully
        assert response.status_code in [400, 500]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
