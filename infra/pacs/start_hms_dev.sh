#!/bin/bash
# HMS Development Environment Startup Script

set -e

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║  🏥 HMS Development Environment Startup   ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Kill any running processes on ports
echo "🔌 Cleaning up ports 4200, 8000, 8080..."
lsof -ti:4200,8000,8080 | xargs kill -9 2>/dev/null || true
sleep 1

# Start PACS
echo ""
echo "📡 Starting PACS Services..."
docker compose -f docker-compose.pacs.yml down --remove-orphans 2>/dev/null || true
docker compose -f docker-compose.pacs.yml up -d

# Wait for Orthanc
echo "⏳ Waiting for Orthanc to be ready..."
for i in {1..10}; do
  if curl -s http://localhost:8042/studies > /dev/null 2>&1; then
    echo "✓ Orthanc is ready"
    break
  fi
  echo "  Attempt $i/10..."
  sleep 1
done

# Start Viewer
echo ""
echo "🖥️  Starting DICOM Viewer..."
cd /Users/sahidulislam/ATM/HMS
python3 infra/pacs/viewer_server.py > /tmp/viewer.log 2>&1 &
VIEWER_PID=$!
echo "   Viewer PID: $VIEWER_PID"

# Verify Viewer
sleep 2
if curl -s http://localhost:8080/ > /dev/null 2>&1; then
    echo "✓ DICOM Viewer is ready on http://localhost:8080"
else
    echo "✗ Viewer failed to start"
    kill $VIEWER_PID 2>/dev/null || true
    exit 1
fi

# Start Backend
echo ""
echo "⚙️  Starting Backend API..."
cd /Users/sahidulislam/ATM/HMS/backend
PYTHONPATH=. ./.venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

# Wait for backend
sleep 2
if curl -s http://localhost:8000/ > /dev/null 2>&1; then
    echo "✓ Backend API is ready on http://localhost:8000"
else
    echo "⚠️  Backend still starting..."
fi

# Start Frontend
echo ""
echo "📱 Starting Frontend..."
cd /Users/sahidulislam/ATM/HMS/frontend
npm start > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║  ✅ HMS Development Environment Ready     ║"
echo "╚════════════════════════════════════════════╝"
echo ""
echo "📍 Services:"
echo "   🏥 DICOM Viewer:  http://localhost:8080"
echo "   ⚙️  Backend API:    http://localhost:8000"
echo "   📱 Frontend:       http://localhost:4200 (starting...)"
echo ""
echo "📊 Orthanc Studies:"
STUDY_COUNT=$(curl -s http://localhost:8042/studies | jq 'length')
echo "   Available: $STUDY_COUNT studies"
echo ""
echo "📋 View logs:"
echo "   tail -f /tmp/viewer.log"
echo "   tail -f /tmp/backend.log"
echo "   tail -f /tmp/frontend.log"
echo ""
echo "🛑 To stop services:"
echo "   kill $VIEWER_PID $BACKEND_PID $FRONTEND_PID"
echo "   docker compose -f docker-compose.pacs.yml down"
echo ""

# Keep script running
wait
