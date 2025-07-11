# Open Karaoke Studio: Post-Migration Issues & Next Steps

## Overview

After the major migration and refactor, several areas require attention to restore full functionality and stability. This document outlines the main issues and priorities for the next phase of development.

---

## 1. Test Failures & Coverage

- **31 test failures** across unit, integration, and API tests.
- **Coverage at 43%** (target: 80%).
- Common issues:
  - Model keyword argument errors (e.g., `duration` in `DbSong`).
  - Service constructor/argument mismatches (e.g., `JobsService`).
  - Mocking errors in audio/image/itunes services.
  - API endpoints returning empty or unexpected data.

## 2. Database Model & Migration Issues

- `DbSong` and other models may not match expected schemas (missing/extra fields).
- Alembic migrations may need review for new/removed columns and types.
- Ensure all models are compatible with PostgreSQL (see `postgres_migration.md`).

## 3. Service Layer Refactor

- Some services (Jobs, Audio, Itunes, File) have interface or implementation mismatches.
- Review constructor signatures and dependency injection patterns.
- Update tests to match new service interfaces.

## 4. Mocking & Test Data

- Many test failures are due to incomplete or incorrect mocks.
- Update mocks to return realistic data and support new method signatures.
- Ensure test fixtures match the new data models.

## 5. API & Integration Endpoints

- Several endpoints return empty or invalid responses.
- Review API logic for data retrieval and serialization.
- Add integration tests for critical endpoints (songs, metadata, jobs).

## 6. Documentation & Developer Experience

- Update setup, migration, and contribution docs for new stack.
- Add troubleshooting for common migration issues.
- Document new/changed environment variables and config options.

---

## Immediate Priorities

1. Fix model and service constructor errors (DbSong, JobsService, etc.).
2. Update and expand test mocks/fixtures for new interfaces.
3. Review and repair API endpoint logic for core features.
4. Re-run and monitor tests after each fix.
5. Gradually increase test coverage and restore CI pass status.

---

_This document should be updated as issues are resolved or new blockers are discovered._
