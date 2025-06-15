# Open Karaoke Studio - Persistent Logging Implementation

## Overview

This document describes the persistent logging system implemented for Open Karaoke Studio, including log configuration, monitoring, and maintenance tools.

## Logging Configuration

### **Log Files Structure**
```
backend/logs/
├── app.log              # Main application logs
├── celery.log           # Celery worker logs
├── jobs.log             # Job processing logs
├── errors.log           # All error-level logs
├── youtube.log          # YouTube service logs
└── audio_processing.log # Audio processing logs
```

### **Configuration**
Logging is configured via environment variables in `.env`:

```bash
# Logging Configuration
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_DIR=./backend/logs           # Directory for log files
LOG_MAX_BYTES=10485760           # Maximum log file size (10MB)
LOG_BACKUP_COUNT=5               # Number of backup files to keep
LOG_FORMAT=detailed              # simple, detailed, json
```

### **Log Levels by Environment**
- **Development**: DEBUG level, console + file logging
- **Production**: INFO level, primarily file logging with JSON format
- **Testing**: WARNING level, minimal logging

## Current Logging Features

### **✅ Implemented**
- **File-based persistent logging** with automatic rotation
- **Structured logging** with consistent formats
- **Service-specific log files** (app, celery, jobs, etc.)
- **Error aggregation** in dedicated error.log
- **Celery integration** with task-specific logging
- **WebSocket event logging** for real-time updates

### **🔧 Enhanced Job Logging**
Jobs now include structured logging with context:
```python
# Example enhanced job log entry
structured_logger.info(
    f"Job progress: {progress}% - {message}",
    extra={
        'job_id': job_id,
        'progress': progress,
        'status': 'processing',
        'filename': filename,
        'message': message
    }
)
```

## Monitoring Tools

### **1. Log Monitor Script**
Location: `backend/scripts/log_monitor.py`

**Usage:**
```bash
# Show overall status
python3 backend/scripts/log_monitor.py status

# Watch logs in real-time
python3 backend/scripts/log_monitor.py watch

# Show recent log entries
python3 backend/scripts/log_monitor.py tail --lines 100

# Analyze errors from last 24 hours
python3 backend/scripts/log_monitor.py errors --hours 24

# Job processing summary
python3 backend/scripts/log_monitor.py jobs --hours 6

# Check disk usage
python3 backend/scripts/log_monitor.py disk
```

**Features:**
- Real-time log watching
- Error pattern analysis
- Job processing statistics
- Disk usage monitoring
- Configurable time windows

### **2. Log Cleanup Script**
Location: `backend/scripts/log_cleanup.py`

**Usage:**
```bash
# Show current status
python3 backend/scripts/log_cleanup.py status

# Rotate large log files
python3 backend/scripts/log_cleanup.py rotate --max-size 10 --keep 5

# Clean up old logs
python3 backend/scripts/log_cleanup.py cleanup --days 30

# Auto maintenance (good for cron)
python3 backend/scripts/log_cleanup.py auto
```

**Features:**
- Automatic log rotation with compression
- Old log cleanup
- Configurable retention policies
- Disk space management

## Integration Points

### **Flask Application**
Logging is initialized in `backend/app/main.py`:
```python
from .config.logging import setup_logging
logging_config = setup_logging(config)
```

### **Celery Workers**
Celery logging is configured in `backend/app/jobs/celery_app.py`:
```python
from ..config.logging import setup_logging
logging_config = setup_logging(config)
celery_logging_config = logging_config.configure_celery_logging()
```

### **Job Processing**
Enhanced job logging in `backend/app/jobs/jobs.py`:
```python
from ..config.logging import get_structured_logger
structured_logger = get_structured_logger('app.jobs', {
    'module': 'jobs',
    'component': 'task_processor'
})
```

## Production Deployment

### **Systemd Service (Optional)**
For automated log maintenance, you can install the systemd service:

```bash
# Copy service files
sudo cp backend/scripts/karaoke-log-cleanup.service /etc/systemd/system/
sudo cp backend/scripts/karaoke-log-cleanup.timer /etc/systemd/system/

# Enable the timer
sudo systemctl enable karaoke-log-cleanup.timer
sudo systemctl start karaoke-log-cleanup.timer

# Check status
sudo systemctl status karaoke-log-cleanup.timer
```

### **Manual Cron Setup**
Alternative to systemd, add to crontab:
```bash
# Run log cleanup daily at 2 AM
0 2 * * * /usr/bin/python3 /home/spencer/code/open-karaoke/backend/scripts/log_cleanup.py auto
```

## Troubleshooting

### **Common Issues**

1. **Log directory not found**
   ```bash
   mkdir -p backend/logs
   ```

2. **Permission issues**
   ```bash
   chmod 755 backend/logs
   chmod +x backend/scripts/log_*.py
   ```

3. **Large log files**
   ```bash
   # Check disk usage
   python3 backend/scripts/log_monitor.py disk

   # Rotate large files
   python3 backend/scripts/log_cleanup.py rotate
   ```

### **Monitoring Commands**
```bash
# Quick health check
python3 backend/scripts/log_monitor.py status

# Real-time monitoring
python3 backend/scripts/log_monitor.py watch --file "jobs.log"

# Error investigation
python3 backend/scripts/log_monitor.py errors --hours 6
```

## Benefits of This Implementation

### **For Development**
- **Better debugging** with structured, searchable logs
- **Real-time monitoring** of job processing
- **Error pattern detection** for quick issue resolution
- **Performance insights** through job timing data

### **For Production**
- **Persistent audit trail** of all system activities
- **Automated log rotation** prevents disk space issues
- **Structured data** for log aggregation tools (ELK, Splunk, etc.)
- **Service health monitoring** through log analysis

### **For Operations**
- **Simple command-line tools** for log analysis
- **Automated maintenance** through cron/systemd
- **Configurable retention** policies
- **Disk space management** with cleanup tools

## Next Steps (Optional)

If you need more advanced monitoring:

1. **ELK Stack Integration** - Send JSON logs to Elasticsearch
2. **Prometheus Metrics** - Extract metrics from logs
3. **Alerting** - Set up alerts for error patterns
4. **Grafana Dashboards** - Visualize log data

But for your current development and small-scale production needs, this implementation provides comprehensive logging without over-engineering!
