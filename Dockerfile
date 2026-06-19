# Use Python 3.12 slim image
FROM python:3.12-slim

# Prevent python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies
# We need curl to download ttyd, nginx for reverse proxy, and gettext-base for envsubst
RUN apt-get update && \
    apt-get install -y curl nginx gettext-base && \
    curl -L https://github.com/tsl0922/ttyd/releases/download/1.7.3/ttyd.x86_64 -o /usr/local/bin/ttyd && \
    chmod +x /usr/local/bin/ttyd && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Make scripts executable
RUN chmod +x start.sh run_cli.sh

# Render dynamically sets PORT, so we expose a general one but trust Render's env var
EXPOSE 10000
EXPOSE 80

# Run the start script
CMD ["/app/start.sh"]
