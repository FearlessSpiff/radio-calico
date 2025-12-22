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

#### Docker (Recommended)
```bash
# Development mode (hot reload, debug enabled)
docker compose up -d
docker compose logs -f

# Production mode (Gunicorn, health checks)
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f

# Stop containers
docker compose down
```

#### Local Python Environment
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

# If using Docker, rebuild after dependency changes
docker compose build
```

### Docker commands
```bash
# Rebuild containers
docker compose build
docker compose -f docker-compose.prod.yml build

# Access container shell
docker exec -it radiocalico-dev /bin/bash

# View container logs
docker compose logs -f radiocalico-dev
```

## Architecture

### Deployment
The application supports two deployment modes:

#### Docker (Multi-stage Build)
- **Dockerfile**: Contains two build targets (`development` and `production`)
- **docker-compose.yml**: Development configuration with SQLite, volume mounts for hot reload
- **docker-compose.prod.yml**: Production with PostgreSQL, nginx, and Gunicorn
- **nginx.conf**: Nginx reverse proxy configuration (proxies all requests to Gunicorn)
- **entrypoint-prod.sh**: Production startup script (waits for PostgreSQL, initializes DB, starts Gunicorn)
- **Database volumes**: Separate volumes for dev (`radiocalico-dev-data`) and prod (`radiocalico-postgres-data`)

**Development container features**:
- Flask development server
- Hot reload on code changes
- Debug mode enabled
- Source code mounted as volumes

**Production container features**:
- Three-tier architecture: nginx → Gunicorn → PostgreSQL
- **nginx**: Reverse proxy on port 80 with gzip compression and security headers
  - Proxies all requests (including static files) to Gunicorn
  - Health check endpoint at `/health`
- **radiocalico (app)**: Gunicorn WSGI server (4 workers, 2 threads) on port 5000
  - Non-root user (`appuser`) for security
  - Resource limits (512MB memory, 1 CPU)
  - Automatic database initialization via entrypoint script
  - Health checks via HTTP request to port 5000
- **postgres**: PostgreSQL 16 Alpine database
  - Persistent volume for data storage
  - Health checks via `pg_isready`
- No source code mounting (production uses baked-in code)

**Important production notes**:
- Change default PostgreSQL password in `docker-compose.prod.yml`
- Ensure Docker bridge interfaces (`br-*`) are allowed in firewall (nftables/iptables)
- Containers require outbound internet access for metadata API

### Backend (Flask)
- **app.py**: Main Flask application containing all routes and database logic
- **Database**:
  - Development: SQLite (`ratings.db`) with a single `ratings` table
  - Production: PostgreSQL with a single `ratings` table
  - Automatic detection via `DATABASE_URL` environment variable
  - Uses raw SQL (no ORM) with parameterized queries
- **User identification**: Uses SHA-256 hash of IP + User-Agent as fingerprint (stored in `user_fingerprint` field)
- **No separate models.py or config.py**: All code is in app.py

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

**Development (SQLite)**:
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

**Production (PostgreSQL)**:
```sql
CREATE TABLE ratings (
    id SERIAL PRIMARY KEY,              -- PostgreSQL auto-increment
    song_id TEXT NOT NULL,
    artist TEXT NOT NULL,
    title TEXT NOT NULL,
    user_fingerprint TEXT NOT NULL,
    rating INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(song_id, user_fingerprint)
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
