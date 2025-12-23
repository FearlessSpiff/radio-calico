# Base stage with common dependencies
FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy package.json and install npm dependencies
COPY package.json package-lock.json* ./
RUN npm install --production

# Create static/js directory and copy hls.js
RUN mkdir -p static/js && \
    cp node_modules/hls.js/dist/hls.min.js static/js/ && \
    cp node_modules/hls.js/dist/hls.min.js.map static/js/ 2>/dev/null || true

# Copy application code
COPY app.py .
COPY templates/ templates/
COPY static/ static/

# Create directory for database
RUN mkdir -p /app/instance

# Development stage
FROM base as development

# Install development tools
RUN pip install --no-cache-dir flask-debugtoolbar

# Set Flask environment for development
ENV FLASK_APP=app.py
ENV FLASK_ENV=development
ENV FLASK_DEBUG=1

# Expose port
EXPOSE 5000

# Use Flask development server with host binding
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]

# Production stage
FROM base as production

# Install production WSGI server
RUN pip install --no-cache-dir gunicorn

# Copy entrypoint script
COPY entrypoint-prod.sh /entrypoint-prod.sh
RUN chmod 755 /entrypoint-prod.sh

# Set Flask environment for production
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app && \
    chown appuser:appuser /entrypoint-prod.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Use entrypoint script to initialize database and start Gunicorn
CMD ["/entrypoint-prod.sh"]
