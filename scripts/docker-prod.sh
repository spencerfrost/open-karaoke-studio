#!/bin/bash
# Production Environment - Docker Compose
# Starts all services with production configuration

set -e

echo "🎤 Open Karaoke Studio - Docker Production Environment"
echo "======================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check for .env.docker file
if [ ! -f ".env.docker" ]; then
    echo -e "${RED}❌ Error: .env.docker file not found${NC}"
    echo ""
    echo "Please create .env.docker from .env.docker.example:"
    echo "  cp .env.docker.example .env.docker"
    echo ""
    echo "Then update the values in .env.docker with your production settings."
    exit 1
fi

# Load environment variables
export $(cat .env.docker | grep -v '^#' | xargs)

# Parse command line arguments
COMMAND=${1:-up}

case $COMMAND in
    up)
        echo -e "${BLUE}🚀 Starting production environment...${NC}"
        echo ""
        
        # Check if karaoke_library exists, create if not
        if [ ! -d "karaoke_library" ]; then
            echo -e "${YELLOW}📁 Creating karaoke_library directory...${NC}"
            mkdir -p karaoke_library
        fi
        
        # Pull latest images if needed
        echo -e "${BLUE}📥 Pulling latest images...${NC}"
        docker-compose -f docker-compose.prod.yml pull
        
        # Build containers
        echo -e "${BLUE}🔨 Building containers...${NC}"
        docker-compose -f docker-compose.prod.yml build
        
        # Start services
        echo -e "${BLUE}🚀 Starting services...${NC}"
        docker-compose -f docker-compose.prod.yml up -d
        
        echo ""
        echo -e "${GREEN}✅ Production services started!${NC}"
        echo ""
        echo "🌐 URLs:"
        echo "   Frontend:           http://localhost:80"
        echo "   Flask API:          http://localhost:5123"
        echo "   FastAPI Sessions:   http://localhost:5124"
        echo ""
        echo "📋 Useful commands:"
        echo "   View logs:          ./scripts/docker-prod.sh logs"
        echo "   View logs (follow): ./scripts/docker-prod.sh logs -f"
        echo "   Stop services:      ./scripts/docker-prod.sh down"
        echo "   Restart services:   ./scripts/docker-prod.sh restart"
        echo ""
        echo "🔍 Check status:      docker-compose -f docker-compose.prod.yml ps"
        ;;
    
    down)
        echo -e "${BLUE}🛑 Stopping production environment...${NC}"
        docker-compose -f docker-compose.prod.yml down
        echo -e "${GREEN}✅ Services stopped${NC}"
        ;;
    
    logs)
        shift
        docker-compose -f docker-compose.prod.yml logs "$@"
        ;;
    
    restart)
        echo -e "${BLUE}🔄 Restarting production environment...${NC}"
        docker-compose -f docker-compose.prod.yml restart
        echo -e "${GREEN}✅ Services restarted${NC}"
        ;;
    
    update)
        echo -e "${BLUE}🔄 Updating production environment...${NC}"
        docker-compose -f docker-compose.prod.yml down
        docker-compose -f docker-compose.prod.yml pull
        docker-compose -f docker-compose.prod.yml build
        docker-compose -f docker-compose.prod.yml up -d
        echo -e "${GREEN}✅ Update complete${NC}"
        ;;
    
    backup)
        echo -e "${BLUE}💾 Creating backup...${NC}"
        BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        
        # Backup database
        docker exec karaoke-postgres-prod pg_dump -U karaoke_user karaoke > "$BACKUP_DIR/database.sql"
        
        # Backup karaoke library (excluding audio files if too large)
        tar -czf "$BACKUP_DIR/library_metadata.tar.gz" karaoke_library/*.json 2>/dev/null || true
        
        echo -e "${GREEN}✅ Backup created in $BACKUP_DIR${NC}"
        ;;
    
    shell-backend)
        echo -e "${BLUE}🐚 Opening shell in backend container...${NC}"
        docker exec -it karaoke-flask-prod /bin/bash
        ;;
    
    shell-celery)
        echo -e "${BLUE}🐚 Opening shell in celery container...${NC}"
        docker exec -it karaoke-celery-prod /bin/bash
        ;;
    
    *)
        echo "Usage: $0 {up|down|logs|restart|update|backup|shell-backend|shell-celery}"
        echo ""
        echo "Commands:"
        echo "  up             - Start all services"
        echo "  down           - Stop all services"
        echo "  logs           - View logs (add -f to follow)"
        echo "  restart        - Restart all services"
        echo "  update         - Pull, rebuild, and restart services"
        echo "  backup         - Create backup of database and metadata"
        echo "  shell-backend  - Open shell in backend container"
        echo "  shell-celery   - Open shell in celery container"
        exit 1
        ;;
esac
