# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Radio Calico is a web-based radio streaming application that plays high-quality audio streams and allows users to rate tracks. The application consists of:
- Flask backend (Python) serving APIs and templates
- SQLite database for storing song ratings
- Single-page application with embedded JavaScript for the radio player
- HLS (HTTP Live Streaming) audio playback using hls.js

## Development Commands

### Running the application
```bash
# Activate virtual environment
source venv/bin/activate

# Run Flask development server
python app.py
```
The application runs on `http://localhost:5000` (or `http://0.0.0.0:5000`)

### Managing dependencies
```bash
# Install new package
venv/bin/pip install package-name

# Update requirements.txt after installing packages
venv/bin/pip freeze > requirements.txt
```

## Architecture

### Backend (Flask)
- **app.py**: Main Flask application containing all routes and database logic
- **Database**: SQLite (`ratings.db`) with a single `ratings` table
- **User identification**: Uses SHA-256 hash of IP + User-Agent as fingerprint (stored in `user_fingerprint` field)
- **No separate models.py or config.py**: All code is in app.py despite what README.md mentions

### API Endpoints
- `GET /`: Serves the main radio player (radio.html)
- `GET /api/metadata`: Proxies metadata from CloudFront (`https://d3d4yli4hf5bmh.cloudfront.net/metadatav2.json`)
- `GET /api/ratings/<song_id>`: Returns rating counts and user's rating for a song
- `POST /api/rate`: Submit/update/remove a rating (rating: 1 for thumbs up, -1 for thumbs down, 0 to remove)

### Frontend
- **templates/radio.html**: Clean HTML structure with semantic markup (91 lines)
- **static/style.css**: All CSS styles including responsive design (387 lines)
- **static/script.js**: All JavaScript code for player functionality and ratings (347 lines)
- **static/RadioCalicoLogoTM.png**: Logo image
- **HLS streaming**: Uses hls.js library loaded from CDN to handle the live stream
- **Metadata refresh**: Polls `/api/metadata` every 10 seconds to update now-playing information
- **Rating system**: Thumbs up/down buttons that submit ratings to the backend API

### Database Schema
```sql
CREATE TABLE ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id TEXT NOT NULL,              -- base64 encoded "artist::title"
    artist TEXT NOT NULL,
    title TEXT NOT NULL,
    user_fingerprint TEXT NOT NULL,     -- SHA-256 hash of IP + User-Agent
    rating INTEGER NOT NULL,            -- 1 (thumbs up) or -1 (thumbs down)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(song_id, user_fingerprint)   -- One rating per user per song
)
```

### Stream and Metadata Sources
- **Audio stream**: `https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8` (HLS format)
- **Album art**: `https://d3d4yli4hf5bmh.cloudfront.net/cover.jpg` (cache-busted on track change)
- **Metadata**: `https://d3d4yli4hf5bmh.cloudfront.net/metadatav2.json`
  - Contains current track info: artist, title, album, date, bit_depth, sample_rate
  - Contains previous 5 tracks as prev_artist_N and prev_title_N fields

## Key Implementation Details

### Song ID Generation
Song IDs are created client-side by base64 encoding the concatenation of artist and title: `btoa(artist + '::' + title)`

### Rating Logic
- Clicking an active rating button removes the rating (sends rating=0)
- Clicking an inactive rating button submits that rating
- The backend handles insert/update/delete based on existing ratings using SQLite UNIQUE constraint

### User Fingerprinting
The backend generates a fingerprint from `X-Forwarded-For` (or remote IP) and `User-Agent` headers. This allows anonymous rating without requiring user accounts.

### Style Guide
- The style guide in text form for the frontend is located at ./RadioCalico_Style_Guide.txt
- The logo for the frontend is located at ./RadioCalicoLogoTM.png
