# Suggested Commands (Windows)

## Development Commands

### Start Development Environment
```bash
# Start all services (frontend, backend, celery)
./scripts/dev.sh

# Start individual services
pnpm run dev:frontend  # Frontend only
pnpm run dev:backend   # Backend only
```

### Backend Development
```bash
cd backend
# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run backend API
python -m app.main
# OR
./run_api.sh

# Run Celery worker
./run_celery.sh
```

### Frontend Development
```bash
cd frontend
# Install dependencies
pnpm install

# Start dev server
pnpm dev

# Build for production
pnpm build
```

## Testing Commands
```bash
# Backend tests
cd backend
pytest
pytest --cov=app --cov-report=html

# Frontend tests
cd frontend
pnpm test
```

## Code Quality Commands
```bash
# Backend linting/formatting
cd backend
pylint app
black app
isort app

# Frontend linting/formatting
cd frontend
pnpm lint:check
pnpm lint:fix
pnpm format
pnpm format:check
pnpm type-check
```

## Docker Commands
```bash
# Start with Docker Compose
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f
```

## Windows-Specific Commands
- Use `dir` instead of `ls`
- Use `type` instead of `cat`
- Use `findstr` instead of `grep`
- Use `PowerShell` or `Command Prompt`
- Virtual environment: `venv\Scripts\activate`