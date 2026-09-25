#!/usr/bin/env bash
# Universal Dynamic Dev Server & Launcher for ai-chat Dashboard & Interactive Agent

PORT=8770
# Find unused port
while lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; do
    PORT=$((PORT+1))
done

echo "⚡ Starting AI-CHAT Visual Dashboard on port $PORT..."
python3 -m http.server $PORT --directory . &
SERVER_PID=$!

trap "kill $SERVER_PID 2>/dev/null" EXIT

sleep 0.5
open "http://localhost:$PORT/dashboard.html" 2>/dev/null || xdg-open "http://localhost:$PORT/dashboard.html" 2>/dev/null || true

echo "Dashboard running at http://localhost:$PORT/dashboard.html"
echo "To run interactive terminal agent: ./cli/main.py"
echo "Press Ctrl+C to stop dashboard server."
wait $SERVER_PID
