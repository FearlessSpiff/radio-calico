const audio = document.getElementById('audio');
const playButton = document.getElementById('playButton');
const volumeSlider = document.getElementById('volumeSlider');
const volumeValue = document.getElementById('volumeValue');
const status = document.getElementById('status');
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const streamUrl = 'https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8';
const metadataUrl = '/api/metadata';

let isPlaying = false;
let hls = null;
let currentTrackId = null;
let metadataRefreshInterval = null;
let currentSongId = null;
let currentArtist = null;
let currentTitle = null;

// Set initial volume
audio.volume = 0.7;

// Metadata fetching and display
async function fetchMetadata() {
    try {
        const response = await fetch(metadataUrl, {
            cache: 'no-store',
            headers: {
                'Cache-Control': 'no-cache'
            }
        });

        if (!response.ok) {
            throw new Error('Failed to fetch metadata');
        }

        const data = await response.json();
        updateNowPlaying(data);
        updatePlaylistHistory(data);

        document.getElementById('metadataStatus').textContent =
            'Metadata: Updated ' + new Date().toLocaleTimeString();

    } catch (err) {
        console.error('Error fetching metadata:', err);
        document.getElementById('metadataStatus').textContent =
            'Metadata: Error - Retrying...';
    }
}

function updateNowPlaying(data) {
    const artistName = document.getElementById('artistName');
    const songTitle = document.getElementById('songTitle');
    const albumInfo = document.getElementById('albumInfo');
    const yearInfo = document.getElementById('yearInfo');
    const audioQuality = document.getElementById('audioQuality');
    const albumArt = document.getElementById('albumArt');

    // Check if track has changed
    const newTrackId = data.title + data.artist;
    if (currentTrackId !== newTrackId && currentTrackId !== null) {
        // Update album art with cache busting
        albumArt.src = 'https://d3d4yli4hf5bmh.cloudfront.net/cover.jpg?t=' + new Date().getTime();
    }
    currentTrackId = newTrackId;

    // Store current song info for ratings
    currentArtist = data.artist || 'Unknown Artist';
    currentTitle = data.title || 'Unknown Title';
    currentSongId = btoa(currentArtist + '::' + currentTitle);

    // Update display
    artistName.textContent = currentArtist;
    songTitle.textContent = currentTitle;

    if (data.album) {
        albumInfo.textContent = data.album;
    } else {
        albumInfo.textContent = '';
    }

    if (data.date) {
        yearInfo.textContent = data.date;
    } else {
        yearInfo.textContent = '';
    }

    // Display audio specs
    const bitDepth = data.bit_depth || 'N/A';
    const sampleRate = data.sample_rate ?
        (data.sample_rate / 1000).toFixed(1) + ' kHz' : 'N/A';
    audioQuality.textContent = `Lossless quality: ${bitDepth}-bit / ${sampleRate}`;

    // Fetch ratings for the new track
    fetchRatings();
}

function updatePlaylistHistory(data) {
    const trackList = document.getElementById('trackList');
    trackList.innerHTML = '';

    // Build history from prev_artist_N and prev_title_N fields
    for (let i = 1; i <= 5; i++) {
        const artistKey = `prev_artist_${i}`;
        const titleKey = `prev_title_${i}`;

        if (data[artistKey] && data[titleKey]) {
            const li = document.createElement('li');
            li.className = 'track-item';

            const nameDiv = document.createElement('div');
            nameDiv.className = 'track-name';
            nameDiv.textContent = data[titleKey];

            const artistDiv = document.createElement('div');
            artistDiv.className = 'track-artist';
            artistDiv.textContent = data[artistKey];

            li.appendChild(nameDiv);
            li.appendChild(artistDiv);
            trackList.appendChild(li);
        }
    }

    if (trackList.children.length === 0) {
        const li = document.createElement('li');
        li.className = 'track-item';
        li.innerHTML = '<div class="track-name">No history available</div>';
        trackList.appendChild(li);
    }
}

// Initialize HLS
function initPlayer() {
    if (Hls.isSupported()) {
        hls = new Hls({
            enableWorker: true,
            lowLatencyMode: true,
            backBufferLength: 90
        });

        hls.loadSource(streamUrl);
        hls.attachMedia(audio);

        hls.on(Hls.Events.MANIFEST_PARSED, function() {
            console.log('HLS manifest loaded, ready to play');
            status.textContent = 'Ready to Play';
            playButton.disabled = false;
        });

        hls.on(Hls.Events.ERROR, function(event, data) {
            if (data.fatal) {
                switch(data.type) {
                    case Hls.ErrorTypes.NETWORK_ERROR:
                        console.error('Network error, trying to recover...');
                        error.textContent = 'Network error occurred. Trying to reconnect...';
                        error.style.display = 'block';
                        hls.startLoad();
                        break;
                    case Hls.ErrorTypes.MEDIA_ERROR:
                        console.error('Media error, trying to recover...');
                        hls.recoverMediaError();
                        break;
                    default:
                        console.error('Fatal error, cannot recover');
                        error.textContent = 'Cannot play stream. Please refresh the page.';
                        error.style.display = 'block';
                        hls.destroy();
                        break;
                }
            }
        });

        hls.on(Hls.Events.FRAG_LOADING, function() {
            loading.textContent = 'Loading...';
            loading.classList.add('active');
        });

        hls.on(Hls.Events.FRAG_LOADED, function() {
            loading.textContent = '';
            loading.classList.remove('active');
            error.style.display = 'none';
        });

    } else if (audio.canPlayType('application/vnd.apple.mpegurl')) {
        audio.src = streamUrl;
        playButton.disabled = false;
    } else {
        error.textContent = 'Your browser does not support HLS streaming.';
        error.style.display = 'block';
        playButton.disabled = true;
    }
}

// Play/Pause functionality
playButton.addEventListener('click', function() {
    if (!isPlaying) {
        audio.play().then(() => {
            isPlaying = true;
            playButton.textContent = '⏸';
            status.textContent = 'Now Playing';
        }).catch(err => {
            console.error('Error playing audio:', err);
            error.textContent = 'Error playing stream. Please try again.';
            error.style.display = 'block';
        });
    } else {
        audio.pause();
        isPlaying = false;
        playButton.textContent = '▶';
        status.textContent = 'Paused';
    }
});

// Volume control
volumeSlider.addEventListener('input', function() {
    const volume = this.value / 100;
    audio.volume = volume;
    volumeValue.textContent = this.value + '%';
});

// Audio event listeners
audio.addEventListener('playing', function() {
    status.textContent = 'Now Playing';
    isPlaying = true;
    playButton.textContent = '⏸';
});

audio.addEventListener('pause', function() {
    status.textContent = 'Paused';
    isPlaying = false;
    playButton.textContent = '▶';
});

audio.addEventListener('waiting', function() {
    loading.textContent = 'Buffering...';
    loading.classList.add('active');
});

audio.addEventListener('canplay', function() {
    loading.textContent = '';
    loading.classList.remove('active');
});

// Rating functions
async function fetchRatings() {
    if (!currentSongId) return;

    try {
        const response = await fetch(`/api/ratings/${currentSongId}`);
        const data = await response.json();

        document.getElementById('thumbsUpCount').textContent = data.thumbs_up;
        document.getElementById('thumbsDownCount').textContent = data.thumbs_down;

        const thumbsUpBtn = document.getElementById('thumbsUpBtn');
        const thumbsDownBtn = document.getElementById('thumbsDownBtn');

        thumbsUpBtn.classList.remove('active');
        thumbsDownBtn.classList.remove('active');

        if (data.user_rating === 1) {
            thumbsUpBtn.classList.add('active');
        } else if (data.user_rating === -1) {
            thumbsDownBtn.classList.add('active');
        }
    } catch (err) {
        console.error('Error fetching ratings:', err);
    }
}

async function submitRating(rating) {
    if (!currentSongId || !currentArtist || !currentTitle) return;

    try {
        const response = await fetch('/api/rate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                song_id: currentSongId,
                artist: currentArtist,
                title: currentTitle,
                rating: rating
            })
        });

        const data = await response.json();
        const messageEl = document.getElementById('ratingMessage');

        if (data.success) {
            if (data.message.includes('removed')) {
                messageEl.textContent = 'Rating removed!';
            } else if (data.message.includes('updated')) {
                messageEl.textContent = 'Rating changed!';
            } else {
                messageEl.textContent = 'Thank you for your rating!';
            }
            messageEl.style.color = '#38A29D';
            fetchRatings();
        } else {
            messageEl.textContent = data.message;
            messageEl.style.color = '#C62828';
        }

        setTimeout(() => {
            messageEl.textContent = '';
        }, 3000);
    } catch (err) {
        console.error('Error submitting rating:', err);
        document.getElementById('ratingMessage').textContent = 'Error submitting rating';
    }
}

// Rating button event listeners
document.getElementById('thumbsUpBtn').addEventListener('click', function() {
    if (this.classList.contains('active')) {
        submitRating(0);
    } else {
        submitRating(1);
    }
});

document.getElementById('thumbsDownBtn').addEventListener('click', function() {
    if (this.classList.contains('active')) {
        submitRating(0);
    } else {
        submitRating(-1);
    }
});

// Initialize metadata refresh
function startMetadataRefresh() {
    fetchMetadata();
    metadataRefreshInterval = setInterval(fetchMetadata, 10000);
}

window.addEventListener('beforeunload', function() {
    if (metadataRefreshInterval) {
        clearInterval(metadataRefreshInterval);
    }
});

// Initialize
initPlayer();
startMetadataRefresh();