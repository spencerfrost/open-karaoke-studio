#!/bin/bash
# Open Karaoke Studio - Complete Setup Script
# This script sets up the entire development environment from scratch

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_header() {
    echo -e "\n${BLUE}🎤 $1${NC}"
    echo "================================================"
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            OS="ubuntu"
        elif command -v yum &> /dev/null; then
            OS="centos"
        else
            OS="linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS="windows"
    else
        OS="unknown"
    fi
    
    log_info "Detected operating system: $OS"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root. Please run as a regular user."
        exit 1
    fi
}

# Install system dependencies
install_system_deps() {
    log_header "Installing System Dependencies"
    
    case $OS in
        "ubuntu")
            log_info "Updating package list..."
            sudo apt update
            
            log_info "Installing Python dependencies..."
            sudo apt install -y python3 python3-pip python3-venv python3-dev
            
            log_info "Installing Node.js..."
            # Check if Node.js is already installed and recent enough
            if command -v node &> /dev/null; then
                local node_version=$(node --version | sed 's/v//')
                local major=$(echo $node_version | cut -d'.' -f1)
                if [ "$major" -ge 16 ]; then
                    log_success "Node.js $node_version already installed"
                else
                    log_info "Upgrading Node.js..."
                    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
                    sudo apt install -y nodejs
                fi
            else
                # Install Node.js 20 LTS
                curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
                sudo apt install -y nodejs
            fi
            
            log_info "Installing Redis server..."
            sudo apt install -y redis-server
            
            log_info "Installing audio processing dependencies..."
            sudo apt install -y ffmpeg libsndfile1 portaudio19-dev
            
            log_info "Installing git and curl..."
            sudo apt install -y git curl
            
            # Start and enable Redis
            sudo systemctl start redis-server
            sudo systemctl enable redis-server
            ;;
            
        "macos")
            # Check if Homebrew is installed
            if ! command -v brew &> /dev/null; then
                log_info "Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            fi
            
            log_info "Installing Python..."
            brew install python@3.11
            
            log_info "Installing Node.js..."
            brew install node@20
            
            log_info "Installing Redis..."
            brew install redis
            brew services start redis
            
            log_info "Installing audio dependencies..."
            brew install ffmpeg portaudio
            ;;
            
        "centos")
            log_info "Installing EPEL repository..."
            sudo yum install -y epel-release
            
            log_info "Installing Python..."
            sudo yum install -y python3 python3-pip python3-devel
            
            log_info "Installing Node.js..."
            curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
            sudo yum install -y nodejs
            
            log_info "Installing Redis..."
            sudo yum install -y redis
            sudo systemctl start redis
            sudo systemctl enable redis
            
            log_info "Installing audio dependencies..."
            sudo yum install -y ffmpeg-devel portaudio-devel
            ;;
            
        *)
            log_warning "Unsupported OS. Please install dependencies manually:"
            echo "  - Python 3.10+"
            echo "  - Node.js 16+"
            echo "  - Redis server"
            echo "  - FFmpeg"
            echo "  - Git"
            ;;
    esac
    
    log_success "System dependencies installed"
}

# Install pnpm
install_pnpm() {
    log_header "Installing pnpm"
    
    if command -v pnpm &> /dev/null; then
        log_info "pnpm already installed: $(pnpm --version)"
    else
        log_info "Installing pnpm..."
        npm install -g pnpm
        log_success "pnpm installed: $(pnpm --version)"
    fi
}

# Verify system dependencies
verify_system_deps() {
    log_header "Verifying System Dependencies"
    
    local errors=0
    
    # Check Python
    if command -v python3 &> /dev/null; then
        local python_version=$(python3 --version | cut -d' ' -f2)
        log_success "Python $python_version found"
    else
        log_error "Python 3 not found"
        ((errors++))
    fi
    
    # Check Node.js
    if command -v node &> /dev/null; then
        local node_version=$(node --version)
        log_success "Node.js $node_version found"
    else
        log_error "Node.js not found"
        ((errors++))
    fi
    
    # Check pnpm
    if command -v pnpm &> /dev/null; then
        local pnpm_version=$(pnpm --version)
        log_success "pnpm $pnpm_version found"
    else
        log_error "pnpm not found"
        ((errors++))
    fi
    
    # Check Redis
    if command -v redis-server &> /dev/null; then
        log_success "Redis server found"
        if redis-cli ping &> /dev/null; then
            log_success "Redis server is running"
        else
            log_warning "Redis server found but not running"
        fi
    else
        log_error "Redis server not found"
        ((errors++))
    fi
    
    # Check Git
    if command -v git &> /dev/null; then
        log_success "Git found"
    else
        log_error "Git not found"
        ((errors++))
    fi
    
    if [ $errors -gt 0 ]; then
        log_error "$errors system dependencies missing. Please install them first."
        exit 1
    fi
    
    log_success "All system dependencies verified"
}

# Setup backend
setup_backend() {
    log_header "Setting up Backend"
    
    cd backend
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        log_info "Creating Python virtual environment..."
        python3 -m venv venv
        log_success "Virtual environment created"
    else
        log_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    log_info "Activating virtual environment..."
    source venv/bin/activate
    
    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip
    
    # Install Python dependencies
    log_info "Installing Python dependencies..."
    pip install -r requirements.txt
    
    # Initialize database
    log_info "Initializing database..."
    if [ ! -f "karaoke.db" ]; then
        python -c "
from app.db.database import ensure_db_schema
ensure_db_schema()
print('Database initialized successfully')
        "
        log_success "Database initialized"
    else
        log_info "Database already exists, verifying schema..."
        python -c "
from app.db.database import ensure_db_schema
ensure_db_schema()
print('Database schema verified')
        "
        log_success "Database schema verified"
    fi
    
    # Create necessary directories
    log_info "Creating necessary directories..."
    mkdir -p logs
    mkdir -p ../karaoke_library
    mkdir -p ../temp_downloads
    
    # Make scripts executable
    chmod +x run_api.sh run_celery.sh
    
    cd ..
    log_success "Backend setup complete"
}

# Setup frontend
setup_frontend() {
    log_header "Setting up Frontend"
    
    cd frontend
    
    # Install dependencies
    log_info "Installing frontend dependencies..."
    pnpm install
    
    # Verify installation
    log_info "Verifying frontend setup..."
    if pnpm list &> /dev/null; then
        log_success "Frontend dependencies installed successfully"
    else
        log_error "Frontend dependency installation failed"
        exit 1
    fi
    
    cd ..
    log_success "Frontend setup complete"
}

# Create environment configuration
setup_environment() {
    log_header "Setting up Environment Configuration"
    
    # Backend environment
    if [ ! -f "backend/.env" ]; then
        log_info "Creating backend .env file..."
        cat > backend/.env << EOF
# Open Karaoke Studio Backend Configuration
FLASK_ENV=development
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///karaoke.db
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
REDIS_URL=redis://localhost:6379/0
HOST=0.0.0.0
PORT=5123
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
EOF
        log_success "Backend .env file created"
    else
        log_info "Backend .env file already exists"
    fi
    
    # Frontend environment for development
    if [ ! -f "frontend/.env.local" ]; then
        log_info "Creating frontend .env.local file..."
        cat > frontend/.env.local << EOF
# Open Karaoke Studio Frontend Configuration
VITE_BACKEND_URL=http://localhost:5123
EOF
        log_success "Frontend .env.local file created"
    else
        log_info "Frontend .env.local file already exists"
    fi
}

# Run health checks
run_health_checks() {
    log_header "Running Health Checks"
    
    # Test Redis connection
    if redis-cli ping > /dev/null 2>&1; then
        log_success "Redis connection: OK"
    else
        log_error "Redis connection: FAILED"
        log_info "Starting Redis server..."
        case $OS in
            "ubuntu")
                sudo systemctl start redis-server
                ;;
            "macos")
                brew services start redis
                ;;
            "centos")
                sudo systemctl start redis
                ;;
        esac
        
        if redis-cli ping > /dev/null 2>&1; then
            log_success "Redis started successfully"
        else
            log_error "Failed to start Redis"
        fi
    fi
    
    # Test Python environment
    cd backend
    source venv/bin/activate
    if python -c "import flask, celery, sqlalchemy; print('All imports successful')" > /dev/null 2>&1; then
        log_success "Python environment: OK"
    else
        log_error "Python environment: FAILED"
    fi
    cd ..
    
    # Test Node.js environment
    cd frontend
    if node --version > /dev/null 2>&1 && pnpm --version > /dev/null 2>&1; then
        log_success "Node.js environment: OK"
    else
        log_error "Node.js environment: FAILED"
    fi
    cd ..
}

# Make scripts executable
make_scripts_executable() {
    log_header "Making Scripts Executable"
    
    chmod +x scripts/*.sh
    chmod +x backend/run_*.sh
    
    log_success "Scripts made executable"
}

# Display next steps
show_next_steps() {
    log_header "Setup Complete! 🎉"
    
    echo -e "${GREEN}"
    echo "Open Karaoke Studio is now ready to use!"
    echo ""
    echo "Next steps:"
    echo "1. Start the development environment:"
    echo "   ./scripts/dev.sh"
    echo ""
    echo "2. Or start services individually:"
    echo "   Backend:  cd backend && ./run_api.sh"
    echo "   Worker:   cd backend && ./run_celery.sh" 
    echo "   Frontend: cd frontend && pnpm dev"
    echo ""
    echo "3. Access the application:"
    echo "   Frontend: http://localhost:5173"
    echo "   Backend:  http://localhost:5123"
    echo ""
    echo "4. Run verification:"
    echo "   ./verify-setup.sh"
    echo ""
    echo "Troubleshooting:"
    echo "- Check logs in backend/logs/ if issues occur"
    echo "- Ensure Redis is running: redis-cli ping"
    echo "- Review docs/getting-started/installation.md"
    echo -e "${NC}"
}

# Main execution
main() {
    log_header "Open Karaoke Studio Setup"
    echo "This script will set up your complete development environment."
    echo ""
    
    check_root
    detect_os
    
    # Ask for confirmation
    read -p "Continue with setup? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Setup cancelled by user"
        exit 0
    fi
    
    install_system_deps
    install_pnpm
    verify_system_deps
    setup_backend
    setup_frontend
    setup_environment
    make_scripts_executable
    run_health_checks
    show_next_steps
    
    log_success "Setup completed successfully!"
}

# Run main function
main "$@"
