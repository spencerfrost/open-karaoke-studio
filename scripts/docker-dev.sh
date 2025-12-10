#!/bin/bash
# Development Environment - Docker Compose
# Starts all services with hot-reload and volume mounts for live code changes

set -e

echo "🎤 Open Karaoke Studio - Docker Development Environment"
echo "========================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse command line arguments
COMMAND=${1:-up}

case $COMMAND in
    up)
        echo -e "${BLUE}🚀 Starting development environment...${NC}"
        echo ""
        
        # Check if karaoke_library exists, create if not
        if [ ! -d "karaoke_library" ]; then
            echo -e "${YELLOW}📁 Creating karaoke_library directory...${NC}"
            mkdir -p karaoke_library
        fi
        
        # Start services
        docker-compose -f docker-compose.dev.yml up -d
        
        echo ""
        echo -e "${GREEN}✅ Services started!${NC}"
        echo ""
        echo "🌐 URLs:"
        echo "   Frontend:           http://localhost:5192"
        echo "   Flask API:          http://localhost:5123"
        echo "   FastAPI Sessions:   http://localhost:5124"
        echo "   Session Test:       http://localhost:5124/session-test"
        echo "   API Docs:           http://localhost:5124/docs"
        echo ""
        echo "📋 Useful commands:"
        echo "   View logs:          ./scripts/docker-dev.sh logs"
        echo "   View logs (follow): ./scripts/docker-dev.sh logs -f"
        echo "   Stop services:      ./scripts/docker-dev.sh down"
        echo "   Restart services:   ./scripts/docker-dev.sh restart"
        echo "   Rebuild containers: ./scripts/docker-dev.sh build"
        echo ""
        echo "🔍 Check status:      docker-compose -f docker-compose.dev.yml ps"
        ;;
    
    down)
        echo -e "${BLUE}🛑 Stopping development environment...${NC}"
        docker-compose -f docker-compose.dev.yml down
        echo -e "${GREEN}✅ Services stopped${NC}"
        ;;
    
    logs)
        shift
        docker-compose -f docker-compose.dev.yml logs "$@"
        ;;
    
    restart)
        echo -e "${BLUE}🔄 Restarting development environment...${NC}"
        docker-compose -f docker-compose.dev.yml restart
        echo -e "${GREEN}✅ Services restarted${NC}"
        ;;
    
    build)
        echo -e "${BLUE}🔨 Rebuilding containers...${NC}"
        docker-compose -f docker-compose.dev.yml build
        echo -e "${GREEN}✅ Build complete${NC}"
        ;;
    
    rebuild)
        echo -e "${BLUE}🔨 Rebuilding and restarting...${NC}"
        docker-compose -f docker-compose.dev.yml down
        docker-compose -f docker-compose.dev.yml build
        docker-compose -f docker-compose.dev.yml up -d
        echo -e "${GREEN}✅ Rebuild and restart complete${NC}"
        ;;
    
    shell-backend)
        echo -e "${BLUE}🐚 Opening shell in backend container...${NC}"
        docker exec -it karaoke-flask-dev /bin/bash
        ;;
    
    shell-frontend)
        echo -e "${BLUE}🐚 Opening shell in frontend container...${NC}"
        docker exec -it karaoke-frontend-dev /bin/sh
        ;;
    
    shell-celery)
        echo -e "${BLUE}🐚 Opening shell in celery container...${NC}"
        docker exec -it karaoke-celery-dev /bin/bash
        ;;
    
    clean)
        echo -e "${YELLOW}🧹 Cleaning up containers, volumes, and images...${NC}"
        read -p "Are you sure? This will remove all containers, volumes, and images (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose -f docker-compose.dev.yml down -v
            docker system prune -f
            echo -e "${GREEN}✅ Cleanup complete${NC}"
        else
            echo "Cleanup cancelled"
        fi
        ;;
    
    *)
        echo "Usage: $0 {up|down|logs|restart|build|rebuild|shell-backend|shell-frontend|shell-celery|clean}"
        echo ""
        echo "Commands:"
        echo "  up              - Start all services"
        echo "  down            - Stop all services"
        echo "  logs            - View logs (add -f to follow)"
        echo "  restart         - Restart all services"
        echo "  build           - Rebuild containers"
        echo "  rebuild         - Rebuild and restart all services"
        echo "  shell-backend   - Open shell in backend container"
        echo "  shell-frontend  - Open shell in frontend container"
        echo "  shell-celery    - Open shell in celery container"
        echo "  clean           - Remove all containers, volumes, and images"
        exit 1
        ;;
esac
