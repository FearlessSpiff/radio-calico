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

### Option 1: Docker (Recommended)

#### Development Mode
```bash
# Build and run the development container
docker compose up -d

# View logs
docker compose logs -f

# Stop the container
docker compose down
```

#### Production Mode
```bash
# Build and run the production containers
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Stop the containers
docker compose -f docker-compose.prod.yml down
```

The application will be available at `http://localhost:5001` (port 5001 via nginx)

**Development features**:
- Hot reload on code changes
- Flask debug mode enabled
- Source code mounted as volumes

**Production features**:
- PostgreSQL database for scalability and reliability
- Nginx reverse proxy with caching and security headers
- Gunicorn WSGI server with 4 workers
- Health checks for all services
- Resource limits (512MB memory, 1 CPU)
- Non-root user for security
- No source code mounting
- Automatic database initialization

### Option 2: Local Python Environment

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
├── app.py                    # Main Flask application (routes, database, API)
├── ratings.db                # SQLite database (development only)
├── .env                      # Environment variables
├── requirements.txt          # Python dependencies
├── package.json              # npm dependencies (frontend)
├── Makefile                  # Build and security scanning targets
├── Dockerfile                # Multi-stage Docker build (dev & prod)
├── docker-compose.yml        # Docker Compose for development
├── docker-compose.prod.yml   # Docker Compose for production (PostgreSQL + nginx)
├── nginx.conf                # Nginx reverse proxy configuration
├── entrypoint-prod.sh        # Production entrypoint script (DB init)
├── .dockerignore             # Docker build exclusions
├── templates/                # HTML templates
│   └── radio.html            # Main radio player interface (HTML only)
├── static/                   # Static assets
│   ├── js/                   # JavaScript libraries
│   │   └── hls.min.js        # HLS.js player library
│   ├── style.css             # All CSS styles
│   ├── script.js             # All JavaScript code
│   └── RadioCalicoLogoTM.png # Logo
├── node_modules/             # npm dependencies (gitignored)
└── venv/                     # Virtual environment (local dev only)
```

## Technical Details

### Backend
- **Framework**: Flask
- **Database**:
  - Development: SQLite with raw SQL
  - Production: PostgreSQL 16 with raw SQL
- **User Identification**: Anonymous fingerprinting based on IP + User-Agent hash
- **Deployment**: Docker containers with multi-stage builds

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

### Using Docker

To rebuild after changing dependencies:
```bash
# Development
docker compose build

# Production
docker compose -f docker-compose.prod.yml build
```

To access the container shell:
```bash
docker exec -it radiocalico-dev /bin/bash
```

### Using Local Python Environment

To install additional packages:
```bash
venv/bin/pip install package-name
venv/bin/pip freeze > requirements.txt
```

To deactivate the virtual environment:
```bash
deactivate
```

## Security Scanning

The project includes comprehensive security scanning for both Python and JavaScript dependencies.

### Running Security Scans

Using Make (recommended):
```bash
# Run all security scans (Python + npm)
make security

# Run only Python security scans
make security-python

# Run only npm security scan
make security-npm

# Run individual scanners
make pip-audit    # Scan Python dependencies
make safety       # Scan Python dependencies (alternative)
make bandit       # Scan Python code for security issues
make npm-audit    # Scan npm dependencies
```

Using tools directly:
```bash
# Python dependency scanning
pip-audit --desc
safety check

# Python code scanning
bandit -r . --exclude ./venv,./node_modules

# npm dependency scanning
npm audit --audit-level=moderate
```

### Security Tools

**Python:**
- **pip-audit**: Scans Python dependencies for known vulnerabilities using the PyPA Advisory Database
- **safety**: Checks Python dependencies against the Safety DB database
- **bandit**: Analyzes Python code for common security issues

**JavaScript:**
- **npm audit**: Scans npm dependencies for known security vulnerabilities

### Installing Dependencies with Security Tools

```bash
# Install all dependencies (Python + npm)
make install

# Install only Python dependencies
make install-python

# Install only npm dependencies
make install-npm
```

### Docker Configuration

The application uses a multi-stage Dockerfile with two build targets:
- **development**: Flask dev server with hot reload and debug mode, SQLite database
- **production**: Gunicorn + PostgreSQL + nginx with health checks and security hardening

**Production architecture** (3-tier setup):
- **nginx**: Reverse proxy on port 5001 (host) → port 80 (container) with gzip compression and security headers
- **radiocalico**: Flask application with Gunicorn (4 workers, 2 threads) on port 5000
- **postgres**: PostgreSQL 16 Alpine database with persistent storage

**Key production features**:
- Nginx proxies all requests (including static files) to Gunicorn
- PostgreSQL database replaces SQLite for better scalability
- Automatic database initialization on container startup
- Health checks for all three services
- Resource limits on application container

Database persistence is handled through Docker volumes:
- `radiocalico-dev-data`: Development SQLite database
- `radiocalico-postgres-data`: Production PostgreSQL data

**Environment variables for production**:
- `DATABASE_URL`: PostgreSQL connection string (auto-configured in docker-compose.prod.yml)
- `POSTGRES_PASSWORD`: **IMPORTANT**: Change the default password in docker-compose.prod.yml before deploying to production

**Firewall/Network Requirements**:
- If using nftables, ensure Docker bridge interfaces (`br-*`) are allowed in the forward chain
- Containers need outbound internet access to fetch metadata from CloudFront

## Stream Information

The application streams from a CloudFront CDN:
- **Audio Stream**: HLS format (.m3u8)
- **Metadata**: JSON format with current and previous track information
- **Album Art**: JPEG images updated per track

## Troubleshooting

### Metadata not loading or ratings not working (Production)

If metadata fails to load or song ratings don't work in production, Docker containers likely can't access the internet.

**Symptoms**:
- Metadata shows "Error - Retrying..."
- Rating buttons don't respond
- Logs show "Network is unreachable" errors

**Solution for nftables**:

Edit `/etc/nftables.conf` and ensure the forward chain allows Docker bridge interfaces:

```nft
chain forward {
  type filter hook forward priority filter; policy drop;
  iifname "docker0" accept comment "allow docker0 outbound"
  oifname "docker0" ct state related,established accept comment "allow docker0 inbound"
  iifname "br-*" accept comment "allow docker bridge outbound"
  oifname "br-*" ct state related,established accept comment "allow docker bridge inbound"
}
```

Then reload nftables and restart containers:
```bash
sudo systemctl reload nftables
docker compose -f docker-compose.prod.yml restart
```

**Solution for iptables/firewalld**: Ensure Docker's MASQUERADE rules are present and firewall allows Docker traffic.