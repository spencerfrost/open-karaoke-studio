# Deployment Guide

This guide covers deploying Open Karaoke Studio in production environments, from single-machine installations to scalable cloud deployments.

## 🚀 Deployment Options

### Development (Current Setup)
- **Local development** with separate frontend/backend servers
- **SQLite database** for simple data storage
- **File-based job queue** for background processing

### Production Ready
- **[Docker Deployment](docker.md)** - *Coming Soon* - Container-based deployment
- **[Configuration Management](configuration.md)** - *Coming Soon* - Environment variables and settings
- **[Monitoring & Logging](monitoring.md)** - *Coming Soon* - Observability setup

### Enterprise Scale
- **[Scaling Guide](scaling.md)** - *Coming Soon* - Performance optimization and scaling

## 📋 Quick Production Setup

### Prerequisites
- **Docker** and **Docker Compose** (recommended)
- **Linux server** with 4GB+ RAM
- **Domain name** (optional, for external access)
- **SSL certificates** (optional, for HTTPS)

### Docker Deployment (Recommended)
```bash
# Clone repository
git clone https://github.com/yourusername/open-karaoke-studio.git
cd open-karaoke-studio

# Configure environment
cp .env.example .env
nano .env  # Edit configuration

# Deploy with Docker
docker-compose up -d

# Access application
# Frontend: http://your-server:3000
# Backend: http://your-server:5000
```

## ⚙️ Configuration

### Environment Variables
Key settings for production deployment:

```bash
# Database
DATABASE_URL=sqlite:///karaoke.db  # or PostgreSQL URL

# Redis (for background jobs)
REDIS_URL=redis://localhost:6379

# Storage
LIBRARY_DIR=/data/karaoke_library

# Security
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# Performance
DEMUCS_DEVICE=cuda  # or cpu
MAX_WORKERS=4
```

### Volume Mounts
Important directories to persist:
- **`/data/karaoke_library`** - Processed song files
- **`/data/database`** - SQLite database files
- **`/data/logs`** - Application logs

## 🔧 Production Considerations

### Performance Optimization
- **GPU Support** - Configure CUDA for faster processing
- **Storage** - Use SSD for better I/O performance
- **Memory** - Allocate sufficient RAM for concurrent processing
- **CPU** - Multi-core systems improve background job throughput

### Security
- **Network Access** - Configure firewall rules appropriately
- **Authentication** - Enable user authentication for multi-user setups
- **HTTPS** - Use SSL/TLS for external access
- **Backup** - Regular database and library backups

### Monitoring
- **Health Checks** - Monitor service availability
- **Resource Usage** - Track CPU, memory, and storage
- **Job Queue** - Monitor background processing status
- **Error Logging** - Centralized log aggregation

## 📊 Deployment Architecture

### Single Machine
```
┌─────────────────────────────────────┐
│              Server                 │
│  ┌─────────────┐ ┌─────────────┐   │
│  │  Frontend   │ │   Backend   │   │
│  │   (React)   │ │  (Flask)    │   │
│  └─────────────┘ └─────────────┘   │
│  ┌─────────────┐ ┌─────────────┐   │
│  │   Redis     │ │   SQLite    │   │
│  │  (Queue)    │ │ (Database)  │   │
│  └─────────────┘ └─────────────┘   │
└─────────────────────────────────────┘
```

### Scalable Architecture
```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Frontend  │    │   Backend   │    │   Workers   │
│  (React)    │───▶│   (Flask)   │───▶│  (Celery)   │
│   Nginx     │    │     API     │    │ Processing  │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       │            ┌─────────────┐    ┌─────────────┐
       │            │  Database   │    │    Redis    │
       └───────────▶│ PostgreSQL  │    │   Queue     │
                    └─────────────┘    └─────────────┘
```

## 🐳 Docker Configuration

### Current Docker Setup
Open Karaoke Studio includes Docker configurations:

```yaml
# docker-compose.yml structure
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    
  backend:
    build: ./backend  
    ports: ["5000:5000"]
    volumes: ["./karaoke_library:/data/library"]
    
  redis:
    image: redis:alpine
    
  worker:
    build: ./backend
    command: celery worker
```

### Production Enhancements
- **Reverse proxy** (Nginx) for SSL termination
- **Volume persistence** for data and configurations
- **Health checks** for container monitoring
- **Resource limits** for container isolation

## 📋 Maintenance

### Regular Tasks
- **Database backups** - Automated backup scheduling
- **Log rotation** - Prevent disk space issues
- **Security updates** - Keep dependencies current
- **Performance monitoring** - Track system health

### Scaling Operations
- **Horizontal scaling** - Add worker nodes for processing
- **Vertical scaling** - Increase resources for single-machine setups
- **Storage scaling** - Expand library storage as needed
- **Database optimization** - Index tuning and query optimization

## 🔍 Monitoring & Troubleshooting

### Health Checks
```bash
# Check API health
curl http://localhost:5000/api/songs

# Check job queue status  
curl http://localhost:5000/api/jobs/status

# Monitor container health (Docker)
docker-compose ps
```

### Log Locations
- **Application logs**: `/data/logs/app.log`
- **Error logs**: `/data/logs/error.log`
- **Celery logs**: `/data/logs/celery.log`
- **Nginx logs**: `/var/log/nginx/` (if using proxy)

### Common Issues
- **Out of disk space** - Monitor library growth
- **High memory usage** - Adjust worker concurrency
- **Slow processing** - Check GPU configuration
- **Network timeouts** - Configure appropriate timeouts

## 📚 Related Documentation

### Current Documentation
- **[Backend Configuration](../architecture/backend/deployment/configuration.md)** - Detailed config options
- **[Monitoring Setup](../architecture/backend/deployment/monitoring.md)** - Logging and observability

### Additional Resources
- **[Development Setup](../development/setup/README.md)** - Local development environment
- **[Troubleshooting](../getting-started/troubleshooting.md)** - Common issues and solutions
- **[Architecture Overview](../architecture/README.md)** - System design understanding

---

**Production Deployment**: For immediate production needs, refer to the existing Docker configurations and backend deployment documentation.

**Questions?** Check the [troubleshooting guide](../getting-started/troubleshooting.md) or open an issue for deployment-specific questions.
