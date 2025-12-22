#!/bin/sh
set -e

echo "Waiting for PostgreSQL to be ready..."
python -c "
import os
import time
import psycopg2
from urllib.parse import urlparse

max_retries = 30
retry_interval = 2

result = urlparse(os.environ.get('DATABASE_URL', ''))
config = {
    'host': result.hostname,
    'port': result.port or 5432,
    'database': result.path[1:],
    'user': result.username,
    'password': result.password
}

for i in range(max_retries):
    try:
        conn = psycopg2.connect(**config)
        conn.close()
        print('PostgreSQL is ready!')
        break
    except psycopg2.OperationalError as e:
        if i < max_retries - 1:
            print(f'PostgreSQL not ready yet, waiting... ({i+1}/{max_retries})')
            time.sleep(retry_interval)
        else:
            print('PostgreSQL did not become ready in time')
            raise
"

echo "Initializing database..."
python -c "from app import init_db; init_db()"

echo "Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 60 --access-logfile - --error-logfile - app:app
