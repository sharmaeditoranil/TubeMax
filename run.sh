#!/bin/bash
# Move to script directory
cd "$(dirname "$0")"

echo "=================================================="
echo "  🎬 YouTube Video Downloader (Full HD 1080p + MP3)"
echo "=================================================="
echo "Starting local web server..."

# Check virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Flask server
python3 app.py
