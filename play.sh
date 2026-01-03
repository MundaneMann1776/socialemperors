#!/bin/bash

# Social Empires Launcher for macOS
# This script starts the game server and opens the game in your browser

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🏰 Social Empires Launcher"
echo "=========================="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 First-time setup: Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    echo ""
else
    source .venv/bin/activate
fi

echo "🚀 Starting Social Empires server..."
echo "   The game will open in your browser shortly."
echo "   Press Ctrl+C to stop the server when done playing."
echo ""

# Open browser after a short delay (in background)
(sleep 3 && open "http://127.0.0.1:5050/") &

# Start the server
python server.py
