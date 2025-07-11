# Open Karaoke Studio - Essential Commands

## Frontend Commands
```bash
cd frontend/

# Development
pnpm dev                    # Local development
pnpm run host              # Network accessible (0.0.0.0)

# Code Quality
pnpm run check             # Run all checks
pnpm run format:check      # Check formatting
pnpm run lint:check        # Check linting  
pnpm run type-check        # Check TypeScript

# Fixes
pnpm run fix               # Fix formatting + linting
pnpm run format            # Auto-format code
pnpm run lint:fix          # Auto-fix linting issues

# Build
pnpm build                 # Production build
pnpm preview               # Preview production build
```

## Backend Commands
```bash
cd backend/

# Development (ALWAYS activate venv first)
source venv/bin/activate   # REQUIRED: Activate virtual environment
./run_api.sh               # Start Flask API server
./run_celery.sh            # Start Celery worker

# Testing (ALWAYS activate venv first)
source venv/bin/activate   # REQUIRED: Activate virtual environment
pytest                     # Run all tests
pytest tests/unit/         # Unit tests only
pytest tests/integration/  # Integration tests only
pytest --cov              # With coverage report

# Code Quality (with venv activated)
source venv/bin/activate   # REQUIRED: Activate virtual environment
isort app/                 # Sort imports
black app/                 # Format Python code
pylint app/                # Lint Python code

# Database (with venv activated)
source venv/bin/activate   # REQUIRED: Activate virtual environment
alembic upgrade head       # Run migrations
alembic revision --autogenerate -m "description"  # Create migration

# Python Module Testing (with venv activated)
source venv/bin/activate   # REQUIRED: Activate virtual environment
python -c "import app.services.youtube_service; print('Import successful')"
python -m py_compile app/services/youtube_service.py
```

## System Utilities (Linux/WSL)
```bash
# Common commands for project maintenance
git status                 # Check git status
git log --oneline -10      # Recent commits
find . -name "*.py" | head # Find Python files
grep -r "search_term" .    # Search in files
ps aux | grep celery       # Check Celery processes
```

## Verification Commands
```bash
# Health checks
./verify-setup.sh          # Complete system verification
./verify-setup-simple.sh   # Basic verification
curl http://localhost:5123/api/health  # Backend health check
```

## IMPORTANT: Virtual Environment Usage
**ALWAYS activate the virtual environment before running Python commands in the backend:**

```bash
cd backend
source venv/bin/activate
# Now run your Python commands
```

This is especially critical for:
- Running tests with pytest
- Using Python linting tools
- Running database migrations
- Importing/testing Python modules
- Any Python-related development tasks