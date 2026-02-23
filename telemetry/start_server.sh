
#!/bin/bash
# ilia Telemetry Server Startup Script

# Configuration
PORT=3001
HOST="127.0.0.1"
LOG_DIR="./telemetry_logs"
WORKERS=4

echo "🔧 Starting ilia Telemetry Server..."

# Create log directory
mkdir -p "$LOG_DIR"
mkdir -p ./logs

# Check if port is available
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port $PORT is already in use"
    echo "   Trying to find existing process..."
    existing_pid=$(lsof -ti:$PORT)
    if [ ! -z "$existing_pid" ]; then
        echo "   Found process: $existing_pid"
        read -p "   Kill existing process? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill $existing_pid
            sleep 2
        else
            echo "❌ Cannot start server. Port $PORT is in use."
            exit 1
        fi
    fi
fi

# Start Gunicorn (production)
echo "🚀 Starting Gunicorn server on $HOST:$PORT..."
echo "   Workers: $WORKERS"
echo "   Logs: $LOG_DIR"

gunicorn \
    --bind "$HOST:$PORT" \
    --workers $WORKERS \
    --access-logfile ./logs/access.log \
    --error-logfile ./logs/error.log \
    --log-level info \
    telemetry_server:app &

# Save PID
SERVER_PID=$!
echo $SERVER_PID > ./logs/server.pid

echo "✅ Server started with PID: $SERVER_PID"
echo "📊 View logs: tail -f ./logs/error.log"
echo "🌐 Server URL: http://$HOST:$PORT"
echo "📝 API Endpoint: http://$HOST:$PORT/ilia-cli/tm/submit"

# Wait for server to start
sleep 3

# Check if server is running
if curl -s http://$HOST:$PORT/health > /dev/null; then
    echo "🎉 Server is healthy and ready!"
else
    echo "⚠️  Server may have failed to start. Check logs."
fi