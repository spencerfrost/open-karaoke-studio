# Task Completion Checklist

## After Completing Any Backend Task

### Code Quality Checks (MANDATORY)
```bash
# 1. Check for forbidden print statements
findstr /R /S "print(" backend\app\
# Should return NO results (except test files)

# 2. Check for direct logging usage
findstr /R /S "logging\." backend\app\ | findstr /V "getLogger"
# Should return NO results

# 3. Check for missing logger declarations
# Manually verify each file has: logger = logging.getLogger(__name__)
```

### Automated Validation
```bash
# Run backend tests
cd backend
pytest

# Run code formatting
black app
isort app

# Run linting
pylint app
```

### Frontend Validation
```bash
cd frontend
# Type checking
pnpm type-check

# Linting
pnpm lint:check

# Formatting check
pnpm format:check

# All checks at once
pnpm check
```

## Before Submitting PR

### Backend Requirements
- [ ] All files have proper logging setup
- [ ] No print() statements in production code
- [ ] All API endpoints use @handle_api_error decorator
- [ ] Proper exception handling with specific error types
- [ ] Type hints on all functions
- [ ] Tests pass with >80% coverage

### Frontend Requirements
- [ ] TypeScript compilation successful
- [ ] ESLint passes with 0 warnings
- [ ] Prettier formatting applied
- [ ] Components properly typed

### Integration Testing
- [ ] Manual testing of changed functionality
- [ ] Verify WebSocket connections work
- [ ] Check API error responses are properly formatted
- [ ] Ensure logging output is structured and informative