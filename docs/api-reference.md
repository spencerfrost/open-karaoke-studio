# API Reference

The backend exposes interactive API documentation at runtime:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

These endpoints are automatically generated from FastAPI and include all REST endpoints and WebSocket specifications.

## Running the Backend

```bash
source backend/venv/bin/activate
python -m uvicorn app.main:app --reload
```

Then visit `http://localhost:8000/docs` for interactive documentation.
