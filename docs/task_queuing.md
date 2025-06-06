# Open Karaoke Studio - Celery Queue System Documentation

## Overview

The Open Karaoke Studio uses Celery as an asynchronous task queue to process audio files in the background. This allows the web interface to remain responsive while CPU/GPU intensive audio separation jobs run asynchronously.

## Architecture

The system uses the following components:

- **Flask API**: Handles HTTP requests and queues audio processing jobs
- **Celery**: Manages the task queue and worker processes
- **Redis**: Acts as the message broker between Flask and Celery workers
- **Demucs**: Powers the audio source separation (vocals/instrumental)

## Configuration Files

### `celery_app.py`

This file configures the Celery application instance, setting up Redis as the broker and result backend.

```python
from celery import Celery
import os
import multiprocessing
from dotenv import load_dotenv

# Set multiprocessing start method to 'spawn' for CUDA compatibility
if multiprocessing.get_start_method(allow_none=True) != 'spawn':
    multiprocessing.set_start_method('spawn', force=True)

# Load environment variables
load_dotenv()

# Get broker and backend URLs from environment with fallbacks
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

# Create Celery app with explicit namespace
celery = Celery(
    'backend',
    broker=broker_url,
    backend=result_backend,
    include=['backend.app.jobs']
)

# Configure Celery
celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
)

def init_celery(app=None):
    """Initialize Celery with Flask app context if provided."""
    if app:
        # Add Flask context to jobs
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask

    return celery
```

### `jobs.py`

This file defines the Celery jobs, particularly the audio processing task.

```python
from datetime import datetime
from pathlib import Path
import traceback
import shutil

from celery.utils.log import get_task_logger

from . import audio
from . import file_management
from . import config
from .celery_app import celery
from .models import Job, JobStatus, JobStore

logger = get_task_logger(__name__)
job_store = JobStore()

class AudioProcessingError(Exception):
    """Custom exception for audio processing errors"""
    pass

@celery.task(bind=True)
def process_audio_task(self, job_id, filepath_str):
    """
    Celery task to process audio file

    Args:
        job_id: Unique identifier for the job
        filepath_str: Path to the audio file
    """
    logger.info(f"Starting audio processing task for job {job_id}")

    # Task implementation...
    # (Processing logic, status updates, error handling)
```

### `run_celery.sh`

This script starts the Celery worker process.

```bash
#!/bin/bash
echo "Starting Open Karaoke Studio Celery Worker..."
source venv/bin/activate

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Change to the parent directory
cd ..

# Start the Celery worker
celery -A backend.app.celery_app.celery worker \
    --loglevel=info \s
    --concurrency=1 \
    --pool=solo
```

## Task Workflow

1. **Task Creation**:

   - User uploads an audio file via the Flask API
   - API creates a job record in the JobStore
   - API enqueues a task with `process_audio_task.delay(job_id, filepath)`

2. **Task Processing**:

   - Celery worker picks up the task from Redis
   - Worker updates job status to "PROCESSING"
   - Worker performs audio separation using Demucs
   - Worker updates job progress periodically
   - Worker finalizes processing and updates job status to "COMPLETED"

3. **Task Monitoring**:
   - Frontend polls the API for job status
   - API returns job status, progress, and results

## Error Handling

The system implements several error handling strategies:

1. **CUDA Initialization**: Falls back to CPU if CUDA initialization fails
2. **Task Retries**: Not currently implemented, but could be added for transient failures
3. **Job Status Updates**: Job status is updated to "FAILED" if an error occurs
4. **Error Messages**: Detailed error messages are captured in the job record

## GPU/CPU Processing

The audio processing uses PyTorch with Demucs and can run on either GPU or CPU:

- **GPU Processing**: Uses CUDA for faster processing when available
- **CPU Fallback**: Automatically falls back to CPU if GPU is unavailable/fails
- **Multiprocessing**: Uses 'spawn' start method for CUDA compatibility

## Environment Variables

Configure the system with these environment variables:

- `REDIS_URL`: Redis server URL (default: `redis://localhost:6379/0`)
- `CELERY_BROKER_URL`: Celery broker URL (defaults to REDIS_URL)
- `CELERY_RESULT_BACKEND`: Celery result backend URL (defaults to REDIS_URL)

## Starting the System

1. **Start Redis**:

   ```bash
   redis-server
   ```

2. **Start the Flask API**:

   ```bash
   ./run_api.sh
   ```

3. **Start the Celery Worker**:
   ```bash
   ./run_celery.sh
   ```

## Troubleshooting

1. **Connection Refused**: Ensure Redis is running and accessible
2. **Task Not Found**: Check task registration and namespace
3. **CUDA Errors**: May indicate GPU memory issues or incompatible CUDA versions
4. **Worker Not Starting**: Check for proper Python environment activation

## Future Enhancements

- Implement task retries for transient failures
- Add task prioritization
- Implement periodic cleanup of old jobs
- Add more granular progress reporting
- Implement worker scaling for handling more concurrent jobs
