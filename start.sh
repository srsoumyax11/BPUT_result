#!/bin/bash

# Ensure exports directory exists
mkdir -p /app/exports

# Default port to 10000 if Render doesn't provide one
export PORT=${PORT:-10000}

# Generate the nginx.conf by replacing ${PORT} in the template
envsubst '${PORT}' < /app/nginx.conf.template > /etc/nginx/nginx.conf

# Start ttyd in the background on internal port 9999
# -W enables writing (input)
# -p 9999 sets the port
echo "Starting ttyd on port 9999..."
ttyd -W -p 9999 /app/run_cli.sh &

# Start NGINX in the foreground
echo "Starting NGINX reverse proxy on port ${PORT}..."
nginx -c /etc/nginx/nginx.conf
