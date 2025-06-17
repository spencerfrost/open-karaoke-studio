#!/bin/bash
# Network connectivity test for Open Karaoke Studio

echo "🌐 Open Karaoke Studio - Network Test"
echo "======================================="

# Get host IP
HOST_IP=$(hostname -I | awk '{print $1}')
echo "📡 Host IP Address: $HOST_IP"

# Test if ports are available
echo ""
echo "🔍 Checking port availability..."

# Check if port 5123 is in use
if lsof -i :5123 >/dev/null 2>&1; then
  echo "✅ Port 5123 (Backend): In use (server running)"
else
  echo "❌ Port 5123 (Backend): Available (server not running)"
fi

# Check if port 5173 is in use
if lsof -i :5173 >/dev/null 2>&1; then
  echo "✅ Port 5173 (Frontend): In use (server running)"
else
  echo "❌ Port 5173 (Frontend): Available (server not running)"
fi

echo ""
echo "📱 Device Connection URLs:"
echo "   Frontend: http://$HOST_IP:5173"
echo "   Backend:  http://$HOST_IP:5123"
echo ""
echo "🔧 Quick Tests:"
echo "   Test backend:  curl http://$HOST_IP:5123/api/health"
echo "   Test frontend: curl http://$HOST_IP:5173"
echo ""
echo "💡 Tip: Share the frontend URL with other devices on your network!"
