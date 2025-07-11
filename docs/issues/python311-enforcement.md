# Enforce Python 3.11 for Backend Environment

## Problem Statement
After migrating to a new development machine, the backend is running on Python 3.13, which is incompatible with some dependencies and may cause runtime errors. The project requires Python 3.11 for reliable operation, but there is currently no enforcement or check for the correct Python version. Developers may accidentally use the wrong version, leading to subtle bugs and failed installations.

## Impact
- Backend may fail to start or behave unpredictably on unsupported Python versions (e.g., 3.13).
- Dependency installation may break due to version mismatches.
- Contributors may waste time debugging environment issues.

## Desired Solution
- **Enforce Python 3.11** for all backend development and production environments.
- **Fail fast** if Python 3.11 is not available, with a clear error message.
- **Update setup scripts** to use `python3.11` for virtual environment creation and dependency installation.
- **Add runtime checks** in `run_api.sh` and `run_celery.sh` to prevent starting the backend with the wrong Python version.
- **Document the requirement** in `requirements.txt` and `README.md`.

## Acceptance Criteria
- `setup.sh` checks for `python3.11` and aborts if not found.
- Virtual environment is always created with Python 3.11.
- `run_api.sh` and `run_celery.sh` refuse to run if the active Python version is not 3.11.x.
- Clear error messages guide the user to install Python 3.11 if missing.
- Documentation is updated to reflect the Python version requirement.

## Additional Notes
- Do not set Python 3.11 as the system default; just require it for the project.
- Consider using `pyenv` or similar tools for local development if multiple Python versions are needed.
- This change will prevent future environment drift and ensure consistent builds.

---
**Tags:** environment, python, setup, backend, reliability
