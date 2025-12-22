# Radio Calico

A web-based live radio streaming application featuring high-quality audio playback and community-driven song ratings.

## Features

- **Live HLS Audio Streaming**: High-quality lossless audio streaming with automatic quality display (bit depth and sample rate)
- **Real-time Metadata**: Current track information updates every 10 seconds, including artist, title, album, and release date
- **Album Artwork**: Dynamic album art that updates with each track change
- **Community Ratings**: Thumbs up/down rating system for tracks with aggregate vote counts
- **Playlist History**: View the last 5 tracks that played on the stream
- **Responsive Design**: Works seamlessly across desktop and mobile devices

## Running the Application

1. Activate the virtual environment:
```bash
source venv/bin/activate
```

2. Run the Flask application:
```bash
python app.py
```

3. Open your browser and navigate to:
```
http://localhost:5000
```

## Project Structure

```
.
├── app.py              # Main Flask application (routes, database, API)
├── ratings.db          # SQLite database for song ratings
├── .env               # Environment variables
├── requirements.txt   # Python dependencies
├── templates/         # HTML templates
│   └── radio.html     # Main radio player interface (HTML only)
├── static/           # Static assets
│   ├── style.css      # All CSS styles
│   ├── script.js      # All JavaScript code
│   └── RadioCalicoLogoTM.png
└── venv/            # Virtual environment
```

## Technical Details

### Backend
- **Framework**: Flask
- **Database**: SQLite with raw SQL (no ORM)
- **User Identification**: Anonymous fingerprinting based on IP + User-Agent hash

### Frontend
- **Player**: HLS.js for adaptive streaming
- **Metadata Polling**: Updates every 10 seconds from CloudFront
- **Styling**: Separated CSS file (style.css) with Montserrat and Open Sans fonts
- **JavaScript**: Modular code in script.js for player controls, metadata, and ratings

### API Endpoints
- `GET /` - Serves the radio player interface
- `GET /api/metadata` - Retrieves current track and playlist history
- `GET /api/ratings/<song_id>` - Gets rating counts for a specific track
- `POST /api/rate` - Submits or updates a track rating

### Database
The `ratings` table stores user ratings with these fields:
- `song_id` - Base64 encoded identifier (artist + title)
- `artist`, `title` - Track information
- `user_fingerprint` - SHA-256 hash for anonymous user tracking
- `rating` - Vote value (1 for thumbs up, -1 for thumbs down)
- `created_at` - Timestamp

## Development

To install additional packages:
```bash
venv/bin/pip install package-name
venv/bin/pip freeze > requirements.txt
```

To deactivate the virtual environment:
```bash
deactivate
```

## Stream Information

The application streams from a CloudFront CDN:
- **Audio Stream**: HLS format (.m3u8)
- **Metadata**: JSON format with current and previous track information
- **Album Art**: JPEG images updated per track