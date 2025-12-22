from flask import Flask, render_template, jsonify, request
import requests
import sqlite3
import hashlib
import os
from datetime import datetime

app = Flask(__name__)

# Database path configuration
DB_PATH = os.path.join('instance', 'ratings.db')

# Ensure instance directory exists
os.makedirs('instance', exist_ok=True)

# Database initialization
def init_db():
    conn = sqlite3.connect(DB_PATH)
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

@app.route('/')
def index():
    return render_template('radio.html')

@app.route('/api/metadata')
def get_metadata():
    try:
        response = requests.get('https://d3d4yli4hf5bmh.cloudfront.net/metadatav2.json', timeout=5)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ratings/<song_id>', methods=['GET'])
def get_ratings(song_id):
    """Get rating counts for a song"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Get thumbs up count
        c.execute('SELECT COUNT(*) FROM ratings WHERE song_id = ? AND rating = 1', (song_id,))
        thumbs_up = c.fetchone()[0]

        # Get thumbs down count
        c.execute('SELECT COUNT(*) FROM ratings WHERE song_id = ? AND rating = -1', (song_id,))
        thumbs_down = c.fetchone()[0]

        # Check if current user has rated this song
        user_fp = get_user_fingerprint()
        c.execute('SELECT rating FROM ratings WHERE song_id = ? AND user_fingerprint = ?', (song_id, user_fp))
        user_rating_row = c.fetchone()
        user_rating = user_rating_row[0] if user_rating_row else None

        conn.close()

        return jsonify({
            'thumbs_up': thumbs_up,
            'thumbs_down': thumbs_down,
            'user_rating': user_rating
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rate', methods=['POST'])
def rate_song():
    """Submit, update, or remove a rating for a song"""
    try:
        data = request.json
        song_id = data.get('song_id')
        artist = data.get('artist')
        title = data.get('title')
        rating = data.get('rating')  # 1 for thumbs up, -1 for thumbs down, 0 to remove

        if not song_id or not artist or not title or rating not in [1, -1, 0]:
            return jsonify({'error': 'Invalid data'}), 400

        user_fp = get_user_fingerprint()

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Check if user has already rated this song
        c.execute('SELECT rating FROM ratings WHERE song_id = ? AND user_fingerprint = ?', (song_id, user_fp))
        existing_rating = c.fetchone()

        if rating == 0:
            # Remove rating
            if existing_rating:
                c.execute('DELETE FROM ratings WHERE song_id = ? AND user_fingerprint = ?', (song_id, user_fp))
                message = 'Rating removed successfully'
            else:
                message = 'No rating to remove'
        elif existing_rating:
            # Update existing rating
            c.execute('''
                UPDATE ratings
                SET rating = ?, created_at = CURRENT_TIMESTAMP
                WHERE song_id = ? AND user_fingerprint = ?
            ''', (rating, song_id, user_fp))
            message = 'Rating updated successfully'
        else:
            # Insert new rating
            c.execute('''
                INSERT INTO ratings (song_id, artist, title, user_fingerprint, rating)
                VALUES (?, ?, ?, ?, ?)
            ''', (song_id, artist, title, user_fp, rating))
            message = 'Rating submitted successfully'

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': message
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Initialize database when app starts (works with both Flask dev server and Gunicorn)
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
