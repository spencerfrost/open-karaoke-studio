# API Error Handling Guide

Open Karaoke Studio provides comprehensive, standardized error handling across all API endpoints to ensure reliable and debuggable applications.

## 📋 Error Response Format

All API errors return a consistent JSON structure:

```json
{
  "error": "Human-readable error message",
  "code": "MACHINE_READABLE_ERROR_CODE",
  "details": {
    "contextual_field": "additional context",
    "resource_id": "affected resource identifier"
  }
}
```

### Example Error Response

```json
{
  "error": "Song not found",
  "code": "RESOURCE_NOT_FOUND",
  "details": {
    "resource_type": "Song",
    "resource_id": "abc-123-def"
  }
}
```

## 🚨 HTTP Status Codes

| Status Code | Description           | When Used                                                  |
| ----------- | --------------------- | ---------------------------------------------------------- |
| `400`       | Bad Request           | Invalid input, validation errors, malformed requests       |
| `404`       | Not Found             | Resource doesn't exist (songs, files, etc.)                |
| `409`       | Conflict              | Resource already exists, operation conflicts               |
| `422`       | Unprocessable Entity  | Valid JSON but business logic validation failed            |
| `500`       | Internal Server Error | Unexpected server errors, system failures                  |
| `502`       | Bad Gateway           | External service failures (YouTube API, metadata services) |
| `503`       | Service Unavailable   | Database connection issues, system overload                |

## 🔧 Error Categories & Codes

### **Validation Errors (400)**

| Error Code             | Description                  | Example Scenario                     |
| ---------------------- | ---------------------------- | ------------------------------------ |
| `MISSING_PARAMETERS`   | Required fields missing      | POST request without required fields |
| `INVALID_PARAMETERS`   | Invalid field values         | Invalid sort field, malformed UUID   |
| `INVALID_IMAGE_FORMAT` | Unsupported image extension  | Requesting .bmp thumbnail            |
| `INVALID_TRACK_TYPE`   | Invalid audio track type     | Requesting "unknown" track type      |
| `MISSING_REQUEST_DATA` | No JSON data provided        | Empty POST/PATCH request body        |
| `SECURITY_VIOLATION`   | Security constraint violated | File outside library bounds          |

### **Resource Errors (404)**

| Error Code           | Description                      | Example Scenario                  |
| -------------------- | -------------------------------- | --------------------------------- |
| `RESOURCE_NOT_FOUND` | Requested resource doesn't exist | Song ID doesn't exist             |
| `FILE_NOT_FOUND`     | Required file missing            | Thumbnail image not found         |
| `LYRICS_NOT_FOUND`   | No lyrics available              | Lyrics search returned no results |

### **System Errors (500)**

| Error Code                  | Description                  | Example Scenario             |
| --------------------------- | ---------------------------- | ---------------------------- |
| `DATABASE_ERROR`            | Database operation failed    | Query execution error        |
| `DATABASE_CONNECTION_ERROR` | Cannot connect to database   | Database server down         |
| `FILE_OPERATION_ERROR`      | File system operation failed | Disk full, permission denied |
| `SERVICE_ERROR`             | Internal service error       | Unexpected processing error  |
| `AUDIO_PROCESSING_ERROR`    | Audio processing failed      | Demucs separation error      |

### **Network Errors (502/503)**

| Error Code                  | Description                  | Example Scenario        |
| --------------------------- | ---------------------------- | ----------------------- |
| `NETWORK_ERROR`             | External service failure     | YouTube API unreachable |
| `LYRICS_CONNECTION_ERROR`   | Lyrics service unreachable   | LRCLIB API down         |
| `LYRICS_TIMEOUT_ERROR`      | Lyrics request timed out     | Slow network response   |
| `METADATA_CONNECTION_ERROR` | Metadata service unreachable | iTunes Search API down  |
| `YOUTUBE_SEARCH_ERROR`      | YouTube search failed        | API quota exceeded      |

## 💡 Client Error Handling Best Practices

### **Frontend Implementation Pattern**

```typescript
interface ApiError {
  error: string;
  code: string;
  details: Record<string, any>;
}

async function handleApiCall<T>(apiCall: () => Promise<T>): Promise<T> {
  try {
    return await apiCall();
  } catch (error) {
    if (error.response?.data) {
      const apiError: ApiError = error.response.data;

      // Handle specific error types
      switch (apiError.code) {
        case "RESOURCE_NOT_FOUND":
          showNotification("Resource not found", "error");
          break;
        case "DATABASE_CONNECTION_ERROR":
          showNotification("Database temporarily unavailable", "warning");
          break;
        case "NETWORK_ERROR":
          showNotification("External service unavailable", "warning");
          break;
        default:
          showNotification(apiError.error, "error");
      }

      // Log for debugging
      console.error("API Error:", apiError);
    }
    throw error;
  }
}
```

### **Error Recovery Strategies**

| Error Type                  | Recommended Action                                       |
| --------------------------- | -------------------------------------------------------- |
| `RESOURCE_NOT_FOUND`        | Show "not found" message, redirect to listing            |
| `DATABASE_CONNECTION_ERROR` | Show retry button, temporary message                     |
| `NETWORK_ERROR`             | Show retry button, indicate external service issue       |
| `VALIDATION_ERROR`          | Highlight specific form fields, show validation messages |
| `FILE_OPERATION_ERROR`      | Check disk space, suggest retry                          |

## 🔍 Debugging with Error Codes

### **Common Error Scenarios**

**Song Upload Fails:**

```json
{
  "error": "Failed to create song directory",
  "code": "FILE_OPERATION_ERROR",
  "details": {
    "operation": "create_directory",
    "path": "/path/to/song/dir",
    "error": "Permission denied"
  }
}
```

**Solution:** Check file system permissions on the library directory.

**YouTube Download Fails:**

```json
{
  "error": "YouTube API request timed out",
  "code": "YOUTUBE_TIMEOUT_ERROR",
  "details": {
    "video_id": "abc123",
    "error": "Request timeout after 30s"
  }
}
```

**Solution:** Check network connectivity and YouTube API status.

**Database Query Fails:**

```json
{
  "error": "Database connection failed during song search",
  "code": "DATABASE_CONNECTION_ERROR",
  "details": {
    "query": "search term",
    "error": "Connection refused"
  }
}
```

**Solution:** Check database server status and connection configuration.

## 🛠️ Development Guidelines

### **Adding New Endpoints**

When creating new API endpoints, follow this error handling pattern:

```python
from ..utils.error_handlers import handle_api_error
from ..utils.validation import validate_json_request
from ..exceptions import DatabaseError, ValidationError, ResourceNotFoundError

@bp.route("/new-endpoint", methods=["POST"])
@handle_api_error
@validate_json_request(RequestSchema)
def new_endpoint(validated_data: RequestSchema):
    try:
        # Endpoint logic here
        return jsonify({"success": True})

    except ValidationError:
        raise  # Let error handlers deal with it
    except ConnectionError as e:
        raise DatabaseError(
            "Database connection failed",
            "DATABASE_CONNECTION_ERROR",
            {"error": str(e)}
        )
    except Exception as e:
        raise ServiceError(
            "Unexpected error in new endpoint",
            "NEW_ENDPOINT_ERROR",
            {"error": str(e)}
        )
```

### **Testing Error Scenarios**

```python
def test_error_handling(client):
    # Test validation error
    response = client.post('/api/songs', json={})
    assert response.status_code == 400
    error_data = response.get_json()
    assert error_data['code'] == 'MISSING_PARAMETERS'

    # Test resource not found
    response = client.get('/api/songs/nonexistent')
    assert response.status_code == 404
    error_data = response.get_json()
    assert error_data['code'] == 'RESOURCE_NOT_FOUND'
```

## 📚 Related Documentation

- **[Coding Standards](../development/coding-standards.md)** - General backend coding practices
- **[API Reference](README.md)** - Complete API endpoint documentation
- **[Architecture Overview](../architecture/backend/README.md)** - Backend system design

---

_This error handling system ensures consistent, debuggable, and maintainable API responses across the entire Open Karaoke Studio platform._
