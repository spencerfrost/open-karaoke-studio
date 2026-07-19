# API Reference

The backend exposes interactive API documentation at runtime:

- **Swagger UI**: `http://localhost:5123/docs`
- **ReDoc**: `http://localhost:5123/redoc`
- **OpenAPI Schema**: `http://localhost:5123/openapi.json`

These endpoints are automatically generated from FastAPI and include all REST endpoints and their request/response schemas.

## Hand-Written Endpoint Guides

The main API surfaces have dedicated pages with examples and workflow context:

- [Songs API](api/songs.md) · [Jobs API](api/jobs.md) · [Queue API](api/queue.md)
- [Sessions API](api/sessions.md) · [Lyrics API](api/lyrics.md) · [Library API](api/library.md)
- [YouTube & Metadata Search API](api/youtube.md) · [Authentication API](api/authentication.md)
- [Error Handling Guide](api/error-handling.md) · [Usage Examples](api/examples/README.md)
- [WebSocket Protocol](/websocket-protocol)

Smaller or admin-oriented routers (`/api/host-settings`, `/api/performance-history`, `/api/health`, and the song fingerprint/audit/replace family) are documented only in Swagger/ReDoc.

## Running the Backend

```bash
cd backend && source venv/bin/activate
./run_api.sh
```

Then visit `http://localhost:5123/docs` for interactive documentation.
