#!/bin/bash

# HVLC_DB Server Startup Script
# This script starts both the API server and frontend development server

echo "🚀 Starting HVLC_DB Development Environment..."

# Kill any existing processes
echo "🧹 Cleaning up existing processes..."
pkill -f "python.*run_api_server" 2>/dev/null
pkill -f "npm run dev" 2>/dev/null
sleep 2

# Start API Server in background
echo "🔧 Starting API Server on port 5001..."
python run_api_server.py --port 5001 &
API_PID=$!
sleep 3

# Start Frontend in background
echo "🎨 Starting Frontend on port 5173..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait a moment for servers to start
sleep 3

# Test if servers are running
echo "🧪 Testing server connections..."
if curl -s http://localhost:5001/api/health > /dev/null; then
    echo "✅ API Server: Running on http://localhost:5001"
else
    echo "❌ API Server: Failed to start"
fi

if curl -s http://localhost:5173 > /dev/null; then
    echo "✅ Frontend: Running on http://localhost:5173"
else
    echo "❌ Frontend: Failed to start"
fi

echo ""
echo "🎯 Your application is ready at: http://localhost:5173"
echo ""
echo "To stop servers:"
echo "  kill $API_PID $FRONTEND_PID"
echo "  or run: pkill -f 'python.*run_api_server'; pkill -f 'npm run dev'"
echo ""
echo "Press Ctrl+C to stop this script (servers will continue running)"

# Keep script alive
wait 