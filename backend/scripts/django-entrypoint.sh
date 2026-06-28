#!/bin/bash

echo "Waiting for the database to be ready..."
python <<EOF
import time
import psycopg2
from psycopg2 import OperationalError

db_ready = False
while not db_ready:
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="$POSTGRES_USER",
            password="$POSTGRES_PASSWORD",
            host="$DB_HOST",
            port=int("$DB_PORT")
        )
        conn.close()
        db_ready = True
        print("Database is ready!")
    except OperationalError:
        print("Database is not ready. Retrying...")
        time.sleep(2)
EOF

echo "Database is ready!"


if [ $# -eq 0 ]; then
    echo "No arguments provided, skipping command execution."
    echo "Running Migration"
    python manage.py migrate

    echo "Populating Groups (roles)..."
    python manage.py loaddata fixtures/roles.json
    
    echo "Assigning permissions to groups..."
    python manage.py loaddata fixtures/group_permissions.json

    echo "Creating Admin User.."
    python manage.py populate_geo_data

    echo "Creating Superuser..."
    python manage.py createsuperuser --noinput 

    echo "Collecting static files..."
    python manage.py collectstatic --noinput

    # nginx is commented out — ALB now handles reverse proxying on port 8080.
    # Gunicorn binds directly on 0.0.0.0:8080 so the ALB can reach it.
    echo "Starting nginx..."
    nginx -g "daemon off;" &

    if [ "$DEBUG_PYTHON" = "True" ]; then
        echo "Starting Django with debugpy..."
        python -m debugpy --listen 0.0.0.0:5678 manage.py runserver 0.0.0.0:8000 --nothreading --noreload
    else
        echo "Starting Gunicorn..."
        gunicorn core.wsgi --log-file - -b 0.0.0.0:8000 --reload --workers 4 --timeout 120 --max-requests 1000 --max-requests-jitter 50
    fi
else
    echo "Executing command: $@"
    exec "$@"
fi
