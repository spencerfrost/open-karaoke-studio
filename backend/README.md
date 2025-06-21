# Open Karaoke Studio - Backend

This document provides information about the backend component of the Open Karaoke Studio application.

## Table of Contents

- [Project Description](#project-description)
- [Technologies](#technologies)
- [Directory Structure](#directory-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the Backend](#running-the-backend)
- [API Endpoints](#api-endpoints)
- [Audio Processing](#audio-processing)
- [File Management](#file-management)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Asynchronous Tasks](#asynchronous-tasks) (_Future Enhancement_)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## Project Description

The backend of Open Karaoke Studio is a Flask-based RESTful API that handles the core logic of the application. It's responsible for:

- Receiving audio file uploads from the frontend.
- Orchestrating the audio separation process using Demucs.
- Managing the storage and retrieval of processed audio files.
- Providing information about the song library.
- Handling requests from the frontend and sending back appropriate responses.

## Technologies

- Python 3.10+
- Flask
- Demucs
- PyTorch
- numpy
- Celery (for asynchronous task processing in production - _Future Enhancement_)
- Flask-CORS (for handling Cross-Origin Resource Sharing)

## Directory Structure

```
backend/
├── __init__.py
├── app/
│   ├── __init__.py
│   ├── audio.py          # Audio processing logic
│   ├── config.py         # Backend configuration
│   ├── file_management.py    # File/directory operations
│   └── main.py           # Flask entry point, API routes
└── requirements.txt      # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.10+
- pip

### Installation

1.  Navigate to the `backend/` directory:

    ```bash
    cd backend
    ```

2.  Create a virtual environment (recommended):

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Linux/macOS
    venv\Scripts\activate     # Windows
    ```

3.  Install dependencies:

    ```bash
    pip install -r requirements.txt
    ```

### Running the Backend

1.  Navigate to the `backend/app/` directory:

    ```bash
    cd backend/app
    ```

2.  Start the Flask development server:

    ```bash
    python main.py
    ```

3.  The server will run on a local URL (usually `http://127.0.0.1:5123/`).

## API Endpoints

The backend exposes the following RESTful API endpoints:

- **`POST /process`**:
  - Receives an audio file upload.
  - Initiates the audio separation process.
  - Returns a task ID or filename.
- **`GET /status/<filename>`**:
  - Retrieves the status of an audio processing task.
  - Returns the processing status (e.g., "pending," "processing," "success," "error").
- **`GET /songs`**:
  - Retrieves a list of processed songs in the library.
  - Returns an array of song objects.
- **`GET /download/<filename>`**:
  - Downloads a processed audio file (vocals or instrumental).

## Audio Processing

- The `app/audio.py` module contains the core audio processing logic.
- It utilizes the Demucs library to separate audio into vocal and instrumental tracks.
- The `separate_audio` function handles the Demucs processing.
- Error handling is implemented to manage potential issues during Demucs execution.
- (_Future Enhancement_) Asynchronous processing using Celery is recommended for production to prevent blocking the API.

## File Management

- The `app/file_management.py` module manages file and directory operations.
- It provides functions for:
  - Creating the song library directory.
  - Creating song-specific directories.
  - Saving uploaded audio files.
  - Retrieving lists of processed songs.
  - Generating paths for output files.

## Configuration

- The `app/config.py` module stores backend-specific configuration settings.
- Settings include:
  - Base directory for the song library.
  - Filenames for vocal and instrumental tracks.
  - Default Demucs model.
  - MP3 bitrate.
- Environment variables are recommended for sensitive configuration (e.g., database credentials).

## Error Handling

The backend implements comprehensive, standardized error handling across all API endpoints:

- **Structured Error Responses**: All errors return consistent JSON format with error codes and contextual details
- **Specific Exception Types**: Distinguishes between database errors, network failures, file system issues, and validation problems
- **HTTP Status Codes**: Appropriate status codes (400, 404, 500, 502, 503) for different error categories
- **Enhanced Logging**: Contextual logging with error categorization for debugging
- **Error Recovery**: Clear error messages and codes enable frontend applications to implement appropriate retry logic

### Error Response Format

```json
{
  "error": "Human-readable error message",
  "code": "MACHINE_READABLE_ERROR_CODE",
  "details": {
    "resource_id": "affected_resource",
    "contextual_field": "additional_context"
  }
}
```

For complete error handling documentation, see: **[API Error Handling Guide](../docs/api/error-handling.md)**

## Asynchronous Tasks (_Future Enhancement_)

- For production, Celery should be integrated to handle the Demucs processing tasks asynchronously.
- This will prevent the API from becoming unresponsive during long-running audio separation.
- A message broker (e.g., Redis, RabbitMQ) is required for Celery.

## Testing

- Unit tests should be written to verify the functionality of the backend logic.
- Integration tests should be created to test the API endpoints.
- A testing framework like `pytest` can be used.

## Deployment

- The Flask backend can be deployed to various platforms (e.g., Heroku, AWS, Google Cloud).
- A production-ready WSGI server (e.g., Gunicorn, uWSGI) should be used.
- Environment variables should be configured securely.

## Contributing

Contributions are welcome! Please follow these steps:

1.  Fork the repository.
2.  Create a new branch for your feature or bug fix.
3.  Make your changes and commit them.
4.  Push your changes to your fork.
5.  Submit a pull request.

## License
