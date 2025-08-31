# Open Karaoke Studio - Project Overview for Gemini

This document provides a comprehensive overview of the Open Karaoke Studio project, detailing its purpose, technical stack, architecture, and key operational procedures for development and testing.

## Project Overview

Open Karaoke Studio is an open-source, AI-powered web application designed to facilitate the creation of karaoke tracks by performing vocal separation on audio files. It aims to provide a user-friendly platform for managing a song library, processing audio, and enabling multi-device karaoke sessions.

**Key Features:**
*   AI-powered vocal extraction for instrumental track generation.
*   User-friendly song library management.
*   Modern, fast, and multi-device compatible web interface.
*   Asynchronous audio processing.
*   Adjustable vocal guide for singing along.
*   Self-hosting capabilities.

**Architecture:**
The application follows a client-server architecture:
*   **Backend:** A Python-based API (originally Flask, migrating to FastAPI as per `docs/issues/FLASK_TO_FASTAPI_MIGRATION.md`) responsible for:
    *   Receiving audio file uploads.
    *   Orchestrating AI-powered audio separation using Demucs (PyTorch).
    *   Managing the song library and processed audio files.
    *   Providing RESTful API endpoints.
    *   Utilizes Celery for asynchronous task processing.
*   **Frontend:** A modern web application built with React and TypeScript, providing the user interface for interacting with the backend.

**Main Technologies:**
*   **Backend:** Python (Flask/FastAPI, Demucs, PyTorch, Celery, SQLAlchemy), Redis.
*   **Frontend:** React 19 (TypeScript), Vite, Tailwind CSS, Shadcn/UI, TanStack Query, pnpm.

## Building and Running

### Initial Setup

To set up the complete development environment, run the main setup script:

```bash
./setup.sh
```

This script handles:
*   Installation of system dependencies (Python, Node.js, Redis, FFmpeg, Git).
*   Installation of `pnpm`.
*   Creation and activation of Python virtual environments for the backend.
*   Installation of Python and Node.js dependencies.
*   Database initialization.
*   Creation of necessary directories (`logs`, `karaoke_library`).
*   Configuration of environment variables for both backend and frontend.

### Running the Application

The project can be run in a local network mode, starting all services:

```bash
./scripts/dev.sh
```

This script automatically detects the host IP, configures the frontend to connect to the backend, and starts the following services in the background:

*   **Backend API:** `http://<HOST_IP>:5123`
*   **Celery Worker**
*   **Frontend Development Server:** `http://localhost:5173` (accessible from the host machine) and `http://<HOST_IP>:5173` (accessible from other devices on the local network).

### Running Individual Services

For more granular control, you can start each service independently:

*   **Backend API:**
    ```bash
    cd backend
    ./run_api.sh
    ```
*   **Celery Worker:**
    ```bash
    cd backend
    ./run_celery.sh
    ```
*   **Frontend Development Server:**
    ```bash
    cd frontend
    pnpm dev
    ```
    (Use `pnpm run host` for local network access: `cd frontend && pnpm run host`)

### Building for Production

To build the frontend for production:

```bash
cd frontend
pnpm run build
```
The built assets will be located in the `frontend/dist/` directory.

## Development Conventions

### Backend (Python)

*   **Command Execution:** When executing any command in the backend, you must wrap it as follows: `cd /mnt/ssd-data/spencer/code/open-karaoke-studio/backend && source venv/bin/activate && {COMMAND}`. This ensures the command runs in the correct directory with the virtual environment activated.
*   **Code Formatting:** Uses `black` and `isort`.
    *   Apply formatting: `cd backend && isort . && black .`
*   **Linting:** Uses `flake8` and `pylint`.
    *   Run linting: `cd backend && flake8 .`
*   **Type Checking:** Uses `pyright`.
*   **Logging:** Strict logging standards are enforced (refer to `docs/development/coding-standards.md` for details). Every Python module should have `logger = logging.getLogger(__name__)` and use `logger.info`, `logger.warning`, `logger.error` (with `exc_info=True` for exceptions). Direct `logging` module usage, `print()` statements in production code, and `current_app.logger` are forbidden.
*   **Error Handling:** Standardized error handling with specific exception types, consistent JSON error responses, and the `@handle_api_error` decorator for API endpoints.
*   **Docstrings:** Functions should have comprehensive docstrings following a specified format (refer to `docs/development/coding-standards.md`).
*   **Type Hints:** All function parameters and return values should be type-hinted.
*   **Import Order:** Follows a specific order: Standard library, third-party, local application, then logger setup.

### Frontend (TypeScript/React)

*   **Code Formatting:** Uses `prettier`.
    *   Apply formatting: `cd frontend && pnpm run format`
    *   Check formatting: `cd frontend && pnpm run format:check`
*   **Linting:** Uses `eslint`.
    *   Check linting: `cd frontend && pnpm run lint:check`
    *   Fix linting: `cd frontend && pnpm run lint:fix`
*   **Type Checking:** Uses `tsc`.
    *   Run type check: `cd frontend && pnpm run type-check`
*   **Combined Checks/Fixes:**
    *   Check all: `cd frontend && pnpm run check`
    *   Fix all: `cd frontend && pnpm run fix`

## Testing

### Verification Script

A dedicated script is available to verify the development environment setup:

```bash
./verify-setup.sh
```

This script checks:
*   System dependencies (Python, Node.js, pnpm, Redis, Git, FFmpeg).
*   Redis connection and basic operations.
*   Backend setup (virtual environment, key Python imports, database existence and schema, environment configuration, script executability).
*   Frontend setup (`package.json`, `node_modules`, lock file, environment configuration, TypeScript compilation).
*   Project directory structure.
*   Attempts to test API endpoints if the backend server is running.
*   Celery configuration and broker connection.

### Running Tests

The project uses `pytest` for backend testing. Frontend testing details are not explicitly defined in the provided `package.json` but typically involve frameworks like Jest or Vitest.

To run backend tests:

```bash
cd backend
pytest
```

A general `test` script is defined in the root `package.json`:

```bash
./scripts/test.sh
```
(The content of `scripts/test.sh` would define how tests are executed for both frontend and backend.)
