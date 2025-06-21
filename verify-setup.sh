#!/bin/bash
# Open Karaoke Studio - Setup Verification Script
# This script verifies that the development environment is properly configured

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_WARNINGS=0

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    ((TESTS_WARNINGS++))
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
}

log_header() {
    echo -e "\n${BLUE}🔍 $1${NC}"
    echo "================================================"
}

# Test system dependencies
test_system_deps() {
    log_header "Testing System Dependencies"
    
    # Python
    if command -v python3 &> /dev/null; then
        local version=$(python3 --version 2>&1 | cut -d' ' -f2)
        local major=$(echo $version | cut -d'.' -f1)
        local minor=$(echo $version | cut -d'.' -f2)
        
        if [ "$major" -gt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -ge 8 ]); then
            log_success "Python $version (>= 3.8 required)"
        else
            log_error "Python $version (>= 3.8 required)"
        fi
    else
        log_error "Python 3 not found"
    fi
    
    # Node.js
    if command -v node &> /dev/null; then
        local version=$(node --version | sed 's/v//')
        local major=$(echo $version | cut -d'.' -f1)
        
        if [ "$major" -ge 16 ]; then
            log_success "Node.js v$version (>= 16 required)"
        else
            log_error "Node.js v$version (>= 16 required)"
        fi
    else
        log_error "Node.js not found"
    fi
    
    # pnpm
    if command -v pnpm &> /dev/null; then
        local version=$(pnpm --version)
        log_success "pnpm $version"
    else
        log_error "pnpm not found"
    fi
    
    # Redis
    if command -v redis-server &> /dev/null; then
        log_success "Redis server installed"
    else
        log_error "Redis server not found"
    fi
    
    # Git
    if command -v git &> /dev/null; then
        log_success "Git installed"
    else
        log_error "Git not found"
    fi
    
    # FFmpeg (optional)
    if command -v ffmpeg &> /dev/null; then
        log_success "FFmpeg installed"
    else
        log_warning "FFmpeg not found (optional, but recommended)"
    fi
}

# Test Redis connection
test_redis() {
    log_header "Testing Redis Connection"
    
    if redis-cli ping &> /dev/null; then
        log_success "Redis server is running and responding"
        
        # Test basic operations
        if redis-cli set test_key "test_value" &> /dev/null && 
           [ "$(redis-cli get test_key)" = "test_value" ] &&
           redis-cli del test_key &> /dev/null; then
            log_success "Redis read/write operations working"
        else
            log_error "Redis read/write operations failed"
        fi
    else
        log_error "Redis server not responding"
        log_info "Try starting Redis:"
        echo "  Ubuntu: sudo systemctl start redis-server"
        echo "  macOS:  brew services start redis"
        echo "  Manual: redis-server"
    fi
}

# Test backend setup
test_backend() {
    log_header "Testing Backend Setup"
    
    if [ ! -d "backend" ]; then
        log_error "Backend directory not found"
        return
    fi
    
    cd backend
    
    # Check virtual environment
    if [ -d "venv" ]; then
        log_success "Python virtual environment exists"
        
        # Activate and test
        source venv/bin/activate
        
        # Check Python version in venv
        local python_version=$(python --version 2>&1 | cut -d' ' -f2)
        log_success "Virtual environment Python: $python_version"
        
        # Test key imports
        if python -c "import flask" &> /dev/null; then
            log_success "Flask import successful"
        else
            log_error "Flask import failed"
        fi
        
        if python -c "import celery" &> /dev/null; then
            log_success "Celery import successful"
        else
            log_error "Celery import failed"
        fi
        
        if python -c "import sqlalchemy" &> /dev/null; then
            log_success "SQLAlchemy import successful"
        else
            log_error "SQLAlchemy import failed"
        fi
        
        if python -c "import torch" &> /dev/null; then
            log_success "PyTorch import successful"
        else
            log_error "PyTorch import failed (required for AI processing)"
        fi
        
        # Test database
        if [ -f "karaoke.db" ]; then
            log_success "Database file exists"
            
            # Test database schema
            if python -c "
from app.db.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()
required_tables = ['songs', 'users', 'jobs', 'karaoke_queue']
missing = [t for t in required_tables if t not in tables]
if missing:
    raise Exception(f'Missing tables: {missing}')
print('All required tables exist')
            " &> /dev/null; then
                log_success "Database schema is valid"
            else
                log_error "Database schema is invalid or incomplete"
            fi
        else
            log_error "Database file not found"
        fi
        
        # Test configuration
        if [ -f ".env" ]; then
            log_success "Environment configuration exists"
        else
            log_warning "Environment configuration (.env) not found"
        fi
        
        # Check scripts
        if [ -x "run_api.sh" ]; then
            log_success "API script is executable"
        else
            log_error "API script not found or not executable"
        fi
        
        if [ -x "run_celery.sh" ]; then
            log_success "Celery script is executable"
        else
            log_error "Celery script not found or not executable"
        fi
        
        deactivate
    else
        log_error "Python virtual environment not found"
    fi
    
    # Check directories
    if [ -d "logs" ]; then
        log_success "Logs directory exists"
    else
        log_warning "Logs directory not found"
    fi
    
    cd ..
}

# Test frontend setup
test_frontend() {
    log_header "Testing Frontend Setup"
    
    if [ ! -d "frontend" ]; then
        log_error "Frontend directory not found"
        return
    fi
    
    cd frontend
    
    # Check package.json
    if [ -f "package.json" ]; then
        log_success "package.json exists"
    else
        log_error "package.json not found"
    fi
    
    # Check node_modules
    if [ -d "node_modules" ]; then
        log_success "Node modules installed"
        
        # Test pnpm list
        if pnpm list &> /dev/null; then
            log_success "All dependencies properly installed"
        else
            log_error "Dependency issues detected"
        fi
    else
        log_error "Node modules not found - run 'pnpm install'"
    fi
    
    # Check lock file
    if [ -f "pnpm-lock.yaml" ]; then
        log_success "pnpm lock file exists"
    else
        log_warning "pnpm lock file not found"
    fi
    
    # Check environment config
    if [ -f ".env.local" ]; then
        log_success "Frontend environment configuration exists"
    else
        log_warning "Frontend environment configuration (.env.local) not found"
    fi
    
    # Test TypeScript compilation
    if pnpm run type-check &> /dev/null; then
        log_success "TypeScript compilation successful"
    else
        log_error "TypeScript compilation failed"
    fi
    
    cd ..
}

# Test project structure
test_project_structure() {
    log_header "Testing Project Structure"
    
    # Required directories
    local required_dirs=("backend" "frontend" "scripts" "docs")
    for dir in "${required_dirs[@]}"; do
        if [ -d "$dir" ]; then
            log_success "Directory '$dir' exists"
        else
            log_error "Directory '$dir' missing"
        fi
    done
    
    # Optional directories
    if [ -d "karaoke_library" ]; then
        log_success "Karaoke library directory exists"
    else
        log_warning "Karaoke library directory not found (will be created)"
    fi
    
    if [ -d "temp_downloads" ]; then
        log_success "Temp downloads directory exists"
    else
        log_warning "Temp downloads directory not found (will be created)"
    fi
    
    # Check development scripts
    local scripts=("dev.sh" "dev-localhost.sh")
    for script in "${scripts[@]}"; do
        if [ -f "scripts/$script" ]; then
            if [ -x "scripts/$script" ]; then
                log_success "Script '$script' exists and is executable"
            else
                log_warning "Script '$script' exists but is not executable"
            fi
        else
            log_error "Script '$script' not found"
        fi
    done
}

# Test API endpoints (if server is running)
test_api_endpoints() {
    log_header "Testing API Endpoints (if server is running)"
    
    local backend_url="http://localhost:5123"
    
    # Check if server is running
    if curl -s "$backend_url/health" &> /dev/null; then
        log_success "Backend server is running"
        
        # Test health endpoint
        if curl -s "$backend_url/health" | grep -q "ok"; then
            log_success "Health endpoint responding"
        else
            log_warning "Health endpoint not responding correctly"
        fi
        
        # Test songs endpoint
        if curl -s "$backend_url/api/songs" &> /dev/null; then
            log_success "Songs API endpoint accessible"
        else
            log_error "Songs API endpoint not accessible"
        fi
    else
        log_info "Backend server not running (this is OK if not started yet)"
        log_info "To start: cd backend && ./run_api.sh"
    fi
}

# Test Celery worker
test_celery() {
    log_header "Testing Celery Configuration"
    
    cd backend
    source venv/bin/activate
    
    # Test Celery app import
    if python -c "from app.jobs.celery_app import celery; print('Celery app imported successfully')" &> /dev/null; then
        log_success "Celery app configuration is valid"
    else
        log_error "Celery app configuration is invalid"
    fi
    
    # Test broker connection (without starting worker)
    if python -c "
from app.jobs.celery_app import celery
try:
    inspect = celery.control.inspect()
    # This will fail if broker is not accessible
    inspect.active()
    print('Broker connection successful')
except Exception as e:
    print(f'Broker connection failed: {e}')
    exit(1)
    " &> /dev/null; then
        log_success "Celery broker connection working"
    else
        log_warning "Celery broker connection failed (Redis may not be running)"
    fi
    
    deactivate
    cd ..
}

# Display summary
show_summary() {
    log_header "Verification Summary"
    
    echo -e "${BLUE}Test Results:${NC}"
    echo -e "${GREEN}✅ Passed: $TESTS_PASSED${NC}"
    if [ $TESTS_WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠️  Warnings: $TESTS_WARNINGS${NC}"
    fi
    if [ $TESTS_FAILED -gt 0 ]; then
        echo -e "${RED}❌ Failed: $TESTS_FAILED${NC}"
    fi
    
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}🎉 Your Open Karaoke Studio setup is ready!${NC}"
        echo ""
        echo "Start the development environment with:"
        echo "  ./scripts/dev.sh"
        echo ""
        echo "Or start services individually:"
        echo "  Backend:  cd backend && ./run_api.sh"
        echo "  Worker:   cd backend && ./run_celery.sh"
        echo "  Frontend: cd frontend && pnpm dev"
    else
        echo -e "${RED}❌ Setup has issues that need to be resolved.${NC}"
        echo ""
        echo "Common fixes:"
        echo "  - Run the setup script: ./setup.sh"
        echo "  - Install missing dependencies manually"
        echo "  - Check the installation guide: docs/getting-started/installation.md"
        echo ""
        echo "For Redis issues:"
        echo "  Ubuntu: sudo systemctl start redis-server"
        echo "  macOS:  brew services start redis"
        echo "  Manual: redis-server"
    fi
}

# Main execution
main() {
    log_header "Open Karaoke Studio Setup Verification"
    echo "This script will verify your development environment setup."
    echo ""
    
    test_system_deps
    test_redis
    test_backend
    test_frontend
    test_project_structure
    test_api_endpoints
    test_celery
    show_summary
}

# Run main function
main "$@"
