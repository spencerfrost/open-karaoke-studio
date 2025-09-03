# Open Karaoke Studio - Task Completion Checklist

## After Completing Any Coding Task

### 1. Code Quality Checks
**Frontend:**
```bash
cd frontend/
pnpm run check           # Format + lint + type check
pnpm run type-check      # TypeScript validation
```

**Backend:**
```bash
cd backend/
pylint app/              # Code quality check
black app/               # Format code
isort app/               # Sort imports
```

### 2. Testing
**Backend:**
```bash
pytest                   # Run all tests
pytest --cov            # With coverage report
pytest tests/unit/       # Unit tests only
```

**Frontend:**
```bash
# Currently no automated tests set up
# Manual testing in browser required
```

### 3. Documentation Updates
- Update relevant README files if architecture changed
- Add/update docstrings for new functions
- Update API documentation if endpoints changed
- Update type definitions if data models changed

### 4. Git Commit
- Review changed files
- Provide a meaningful commit message for the changes
- Encourage the user to commit reviewed changes even if they aren't perfect

## Pre-Production Deployment Checklist

### 1. Environment Configuration
- Verify production environment variables
- Check database configuration
- Validate Redis connection settings
- Confirm Docker configuration

### 2. Security Review
- Check for hardcoded secrets
- Verify API authentication (when implemented)
- Review file upload restrictions
- Check CORS configuration

### 3. Performance Validation
- Test with large audio files
- Verify Celery worker performance
- Check memory usage during processing
- Test concurrent job processing

### 4. Backup & Recovery
- Database backup procedures
- Karaoke library backup
- Configuration backup
- Recovery testing