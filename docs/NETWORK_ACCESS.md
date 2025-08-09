# Open Karaoke Studio - Network Access Quick Reference

## 🌐 Access URLs

### Local Machine
- **Application**: http://localhost:5192
- **API**: http://localhost:5192/api
- **Health Check**: http://localhost:5192/api/health

### Local Network (Other Devices)
- **Application**: http://192.168.50.112:5192
- **API**: http://192.168.50.112:5192/api
- **Health Check**: http://192.168.50.112:5192/api/health

## 🚀 Quick Commands

```bash
# Deploy the application
./deploy.sh

# Check health locally
./health-check.sh

# Check health from network IP
./health-check.sh 192.168.50.112

# Test network connectivity
curl http://192.168.50.112:5192/api/health
```

## 🔥 Firewall Setup

### Ubuntu/Debian
```bash
sudo ufw allow 5192
sudo ufw status
```

### CentOS/RHEL
```bash
sudo firewall-cmd --permanent --add-port=5192/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```

### macOS
```bash
# Usually no configuration needed for local network access
# If using pfctl, add rule to allow incoming connections on port 5192
```

## 📱 Mobile/Tablet Access

Once deployed and firewall configured, you can access the karaoke studio from:
- **Smartphones**: Open browser → http://192.168.50.112:5192
- **Tablets**: Open browser → http://192.168.50.112:5192
- **Other Laptops**: Open browser → http://192.168.50.112:5192

## 🔧 Troubleshooting Network Access

1. **Can't access from other devices?**
   ```bash
   # Check if service is running
   docker-compose ps
   
   # Check firewall
   sudo ufw status  # Ubuntu/Debian
   sudo firewall-cmd --list-ports  # CentOS/RHEL
   ```

2. **Connection refused errors?**
   ```bash
   # Verify Docker is binding to all interfaces
   docker-compose logs frontend
   
   # Test local access first
   curl http://localhost:5192
   ```

3. **Wrong IP address?**
   ```bash
   # Find your actual local network IP
   ip addr show | grep "inet 192.168"
   # or
   ifconfig | grep "inet 192.168"
   
   # Update .env file with correct IP
   echo "LOCAL_NETWORK_IP=YOUR_ACTUAL_IP" >> .env
   ```

## 📡 Network Information

- **Container Port Binding**: `0.0.0.0:5192:80`
- **Nginx Server Names**: `localhost 192.168.50.112 _`
- **Network Mode**: Bridge (allows external access)
- **Protocol**: HTTP (upgrade to HTTPS for production)
