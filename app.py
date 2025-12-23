from flask import Flask, render_template, jsonify, request
import requests
import sqlite3
import hashlib
from datetime import datetime
import os

app = Flask(__name__)

# Build version for cache busting
BUILD_VERSION = os.environ.get('BUILD_VERSION', datetime.now().strftime('%Y%m%d%H%M%S'))

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///ratings.db')
USE_POSTGRES = DATABASE_URL.startswith('postgresql://') or DATABASE_URL.startswith('postgres://')

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from urllib.parse import urlparse

    # Parse database URL
    result = urlparse(DATABASE_URL)
    DB_CONFIG = {
        'host': result.hostname,
        'port': result.port or 5432,
        'database': result.path[1:],
        'user': result.username,
        'password': result.password
    }

# Database connection helper
def get_db_connection():
    """Get database connection based on configuration"""
    if USE_POSTGRES:
        return psycopg2.connect(**DB_CONFIG)
    else:
        return sqlite3.connect('ratings.db')

# Database initialization
def init_db():
    """Initialize database with ratings table"""
    if USE_POSTGRES:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id SERIAL PRIMARY KEY,
                song_id TEXT NOT NULL,
                artist TEXT NOT NULL,
                title TEXT NOT NULL,
                user_fingerprint TEXT NOT NULL,
                rating INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(song_id, user_fingerprint)
            )
        ''')
        conn.commit()
        conn.close()
    else:
        conn = sqlite3.connect('ratings.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                song_id TEXT NOT NULL,
                artist TEXT NOT NULL,
                title TEXT NOT NULL,
                user_fingerprint TEXT NOT NULL,
                rating INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(song_id, user_fingerprint)
            )
        ''')
        conn.commit()
        conn.close()

def get_user_fingerprint():
    """Generate a unique fingerprint for the user based on IP and User-Agent"""
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    fingerprint = hashlib.sha256(f"{ip}:{user_agent}".encode()).hexdigest()
    return fingerprint

@app.context_processor
def inject_build_version():
    """Inject build version into templates for cache busting"""
    return {'build_version': BUILD_VERSION}

@app.after_request
def add_cache_headers(response):
    """Add appropriate Cache-Control headers for performance optimization"""
    path = request.path

    # Static assets - long cache (1 year)
    if path.startswith('/static/'):
        if path.endswith(('.css', '.js', '.png', '.jpg', '.jpeg', '.webp', '.svg', '.woff', '.woff2', '.ttf', '.map')):
            response.cache_control.max_age = 31536000  # 1 year
            response.cache_control.public = True

    # API endpoints - no cache
    elif path.startswith('/api/'):
        response.cache_control.no_cache = True
        response.cache_control.no_store = True
        response.cache_control.must_revalidate = True

    # HTML pages - short cache
    elif path == '/' or path.endswith('.html'):
        response.cache_control.max_age = 300  # 5 minutes
        response.cache_control.public = True

    return response

@app.route('/')
def index():
    return render_template('radio.html')

@app.route('/api/metadata')
def get_metadata():
    try:
        response = requests.get('https://d3d4yli4hf5bmh.cloudfront.net/metadatav2.json', timeout=10)
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.Timeout as e:
        app.logger.error(f"Metadata request timeout: {str(e)}")
        return jsonify({'error': 'Metadata service timeout'}), 504
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Metadata request error: {str(e)}")
        return jsonify({'error': 'Unable to fetch metadata'}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error in metadata endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ratings/<song_id>', methods=['GET'])
def get_ratings(song_id):
    """Get rating counts for a song"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        placeholder = '%s' if USE_POSTGRES else '?'

        # Get thumbs up count
        c.execute(f'SELECT COUNT(*) FROM ratings WHERE song_id = {placeholder} AND rating = 1', (song_id,))
        thumbs_up = c.fetchone()[0]

        # Get thumbs down count
        c.execute(f'SELECT COUNT(*) FROM ratings WHERE song_id = {placeholder} AND rating = -1', (song_id,))
        thumbs_down = c.fetchone()[0]

        # Check if current user has rated this song
        user_fp = get_user_fingerprint()
        c.execute(f'SELECT rating FROM ratings WHERE song_id = {placeholder} AND user_fingerprint = {placeholder}', (song_id, user_fp))
        user_rating_row = c.fetchone()
        user_rating = user_rating_row[0] if user_rating_row else None

        conn.close()

        return jsonify({
            'thumbs_up': thumbs_up,
            'thumbs_down': thumbs_down,
            'user_rating': user_rating
        })
    except Exception as e:
        app.logger.error(f"Error getting ratings for {song_id}: {str(e)}")
        if conn:
            conn.close()
        return jsonify({'error': str(e)}), 500

@app.route('/api/rate', methods=['POST'])
def rate_song():
    """Submit, update, or remove a rating for a song"""
    conn = None
    try:
        data = request.json
        song_id = data.get('song_id')
        artist = data.get('artist')
        title = data.get('title')
        rating = data.get('rating')  # 1 for thumbs up, -1 for thumbs down, 0 to remove

        if not song_id or not artist or not title or rating not in [1, -1, 0]:
            return jsonify({'error': 'Invalid data'}), 400

        user_fp = get_user_fingerprint()
        placeholder = '%s' if USE_POSTGRES else '?'

        conn = get_db_connection()
        c = conn.cursor()

        # Check if user has already rated this song
        c.execute(f'SELECT rating FROM ratings WHERE song_id = {placeholder} AND user_fingerprint = {placeholder}', (song_id, user_fp))
        existing_rating = c.fetchone()

        if rating == 0:
            # Remove rating
            if existing_rating:
                c.execute(f'DELETE FROM ratings WHERE song_id = {placeholder} AND user_fingerprint = {placeholder}', (song_id, user_fp))
                message = 'Rating removed successfully'
            else:
                message = 'No rating to remove'
        elif existing_rating:
            # Update existing rating
            c.execute(f'''
                UPDATE ratings
                SET rating = {placeholder}, created_at = CURRENT_TIMESTAMP
                WHERE song_id = {placeholder} AND user_fingerprint = {placeholder}
            ''', (rating, song_id, user_fp))
            message = 'Rating updated successfully'
        else:
            # Insert new rating
            c.execute(f'''
                INSERT INTO ratings (song_id, artist, title, user_fingerprint, rating)
                VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
            ''', (song_id, artist, title, user_fp, rating))
            message = 'Rating submitted successfully'

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': message
        })
    except Exception as e:
        app.logger.error(f"Error rating song {song_id if 'song_id' in locals() else 'unknown'}: {str(e)}")
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500

# Initialize database on module load
init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
