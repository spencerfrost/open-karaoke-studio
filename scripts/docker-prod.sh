#!/bin/bash
# Open Karaoke Studio - Docker Compose helper
# Builds, starts and looks after the Docker stack in docker-compose.yml.
# Settings come from .env at the project root, which Compose reads itself.

set -e

# Run from the project root, wherever the script is called from
cd "$(dirname "$0")/.."

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Refuse to start without the secrets production needs, rather than letting
# the API container fail its health check with the reason buried in its logs.
check_env() {
    if [ ! -f ".env" ]; then
        echo -e "${RED}❌ .env not found${NC}"
        echo ""
        echo "Create it from the example and fill in the secrets:"
        echo "  cp .env.example .env"
        exit 1
    fi

    local missing=()
    for var in JWT_SECRET_KEY SECRET_KEY; do
        local value
        value=$(grep -E "^${var}=" .env | tail -n 1 | cut -d= -f2-)
        if [ -z "$value" ] || [[ "$value" == change-me* ]]; then
            missing+=("$var")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        echo -e "${RED}❌ Set these in .env first: ${missing[*]}${NC}"
        echo ""
        echo "Generate a value with:  openssl rand -hex 32"
        exit 1
    fi

    if ! grep -qE '^ADMIN_USERNAME=.+' .env || ! grep -qE '^ADMIN_PASSWORD=.+' .env; then
        echo -e "${YELLOW}⚠️  ADMIN_USERNAME / ADMIN_PASSWORD aren't set in .env.${NC}"
        echo "   Fine if an admin already exists; on a fresh install nobody can sign in."
        echo ""
    fi
}

COMMAND=${1:-up}

case $COMMAND in
    up)
        check_env
        echo -e "${BLUE}🚀 Building and starting...${NC}"

        # Docker would create a missing bind-mount folder owned by root
        mkdir -p karaoke_library secrets

        docker compose up -d --build

        echo ""
        echo -e "${GREEN}✅ Started${NC}"
        echo ""
        echo "   App:       http://localhost:5192"
        echo "   API:       http://localhost:15123"
        echo ""
        echo "   Logs:      $0 logs -f"
        echo "   Status:    docker compose ps"
        ;;

    down)
        echo -e "${BLUE}🛑 Stopping...${NC}"
        docker compose down
        echo -e "${GREEN}✅ Stopped${NC}"
        ;;

    logs)
        shift
        docker compose logs "$@"
        ;;

    restart)
        echo -e "${BLUE}🔄 Restarting...${NC}"
        docker compose restart
        echo -e "${GREEN}✅ Restarted${NC}"
        ;;

    update)
        check_env
        echo -e "${BLUE}🔄 Rebuilding...${NC}"
        # Build while the old containers keep serving, then swap them in
        docker compose build
        docker compose up -d
        echo -e "${GREEN}✅ Updated${NC}"
        ;;

    backup)
        # The database holds every song's metadata, lyrics and sessions. Song
        # audio lives in karaoke_library/ and is too large to copy here; back
        # that folder up separately if you need to.
        BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        echo -e "${BLUE}💾 Dumping the database...${NC}"
        docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > "$BACKUP_DIR/database.sql"
        echo -e "${GREEN}✅ $BACKUP_DIR/database.sql${NC}"
        ;;

    shell-api)
        docker compose exec api /bin/bash
        ;;

    shell-celery)
        docker compose exec celery /bin/bash
        ;;

    *)
        echo "Usage: $0 {up|down|logs|restart|update|backup|shell-api|shell-celery}"
        echo ""
        echo "  up             Build and start everything"
        echo "  down           Stop everything"
        echo "  logs           Show logs (add -f to follow, or a service name)"
        echo "  restart        Restart the containers without rebuilding"
        echo "  update         Rebuild, then swap in the new containers"
        echo "  backup         Dump the database to backups/"
        echo "  shell-api      Open a shell in the API container"
        echo "  shell-celery   Open a shell in the Celery container"
        exit 1
        ;;
esac
