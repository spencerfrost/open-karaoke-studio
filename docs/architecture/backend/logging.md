# Open Karaoke Studio - Logging Standards & Implementation

## Overview

This document describes the centralized logging system implemented for Open Karaoke Studio. The system provides both console and file output using a standardized pattern across all backend modules.

## Current Implementation

### **Centralized Configuration**

All logging is configured through `backend/app/config/logging.py` which provides:

- **Console logging** for development (with colors)
- **File logging** to `backend/logs/errors.log` for all ERROR+ messages
- **Dual output** - both console and file simultaneously
- **Automatic log rotation** to prevent disk space issues

### **File Structure**

```
backend/logs/
├── errors.log           # All ERROR and CRITICAL level messages
├── errors.log.1         # Rotated log files (automatic)
├── errors.log.2
└── ...
```

## **REQUIRED CODING PATTERN**

### **Every Python Module Must Use This Pattern:**

```python
import logging

# At the top of every .py file, after imports
logger = logging.getLogger(__name__)

# Usage throughout the module:
logger.info("Informational message")
logger.warning("Warning message")
logger.error("Error message", exc_info=True)  # Include stack trace for errors
```

### **❌ NEVER Use These (Legacy Patterns):**

```python
# DON'T - Direct logging module calls
logging.info("message")
logging.error("message")
logging.warning("message")

# DON'T - Print statements in production code
print("debug message")
print(f"Error: {e}")

# DON'T - Flask current_app.logger (inconsistent)
current_app.logger.info("message")
```

### **✅ Correct Implementation Examples:**

```python
# backend/app/services/audio.py
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def separate_audio(input_path: Path, song_dir: Path, status_callback):
    try:
        logger.info(f"Starting audio separation for {input_path.name}")
        # ... processing logic
        logger.info(f"Audio separation completed successfully")
        return True
    except Exception as e:
        logger.error(f"Audio separation failed for {input_path.name}: {e}", exc_info=True)
        raise
```

## Code Review Checklist

### **Before Merging Any Backend Code:**

- [ ] **Logger Import**: Does the file have `import logging` and `logger = logging.getLogger(__name__)`?
- [ ] **No Print Statements**: Are there any `print()` calls in production code?
- [ ] **No Direct Logging**: Are there any `logging.info/error/warning()` calls?
- [ ] **No current_app.logger**: Are there any Flask `current_app.logger` calls?
- [ ] **Proper Error Logging**: Do error handlers use `logger.error(..., exc_info=True)`?
- [ ] **Status Callbacks**: If using status callbacks, do they also call logger?

### **Log Level Guidelines:**

- **`logger.debug()`**: Detailed debugging information, only in development
- **`logger.info()`**: General information about program execution
- **`logger.warning()`**: Something unexpected happened, but program continues
- **`logger.error()`**: Serious problem occurred, use `exc_info=True` for exceptions
- **`logger.critical()`**: Very serious error, program may not continue

## Testing Your Logging

### **Verify Dual Output:**

```bash
# 1. Start the application
./scripts/dev.sh

# 2. Trigger some operations (upload song, process audio, etc.)

# 3. Check both outputs:
# Console: Should see logs in terminal
# File: Should see errors in backend/logs/errors.log
cat backend/logs/errors.log
```

## Integration Points

### **Flask Application**

Logging is initialized in `backend/app/main.py`:

```python
from .config.logging import setup_logging
setup_logging()
```

### **Key Configuration File**

`backend/app/config/logging.py` contains the centralized logging setup that:

- Configures both console and file handlers
- Sets up log rotation to prevent disk space issues
- Provides consistent formatting across all modules
- Ensures all modules use the same logging configuration

## Troubleshooting

### **Common Issues**

1. **Logs not appearing in file**

   ```bash
   # Check if logs directory exists
   ls -la backend/logs/

   # If missing, create it
   mkdir -p backend/logs
   ```

2. **ImportError with logging**

   ```python
   # Make sure you have this at the top of every Python file:
   import logging
   logger = logging.getLogger(__name__)
   ```

3. **Still seeing print statements**
   ```bash
   # Search for remaining print statements in production code:
   grep -r "print(" backend/app/ --exclude-dir=__pycache__
   ```

### **Debugging Commands**

```bash
# Check recent errors
tail -50 backend/logs/errors.log

# Watch logs in real-time
tail -f backend/logs/errors.log

# Search for specific patterns
grep "ERROR" backend/logs/errors.log | tail -20
```

## Benefits of This Implementation

### **For Development**

- **Consistent debugging** - all modules log the same way
- **Dual output** - see logs in console AND file simultaneously
- **Better error tracking** - stack traces captured with `exc_info=True`
- **No lost messages** - nothing disappears like print statements did

### **For Production**

- **Persistent error logs** - all errors saved to files
- **Automatic rotation** - prevents disk space issues
- **Centralized configuration** - easy to modify logging behavior
- **Standardized format** - easy to parse and analyze

### **For Code Quality**

- **Enforced standards** - consistent logging across all modules
- **Easy code reviews** - clear pattern to check against
- **No debugging remnants** - no print statements left in production code
- **Proper error handling** - encourages better exception handling

## Migration Notes

All backend modules have been updated to use this pattern:

- ✅ **API endpoints** (`backend/app/api/`)
- ✅ **Services** (`backend/app/services/`)
- ✅ **Database operations** (`backend/app/db/`)
- ✅ **Job processing** (`backend/app/jobs/`)
- ✅ **WebSocket handlers** (`backend/app/websockets/`)

**Print statements remain only in:**

- Test functions (e.g., `test_itunes_search()`)
- Server startup messages (`main.py`)
- Migration scripts (`migrate.py`)

This ensures production code is clean while preserving appropriate console output for debugging and system startup.
