# Open Karaoke Studio - Code Style & Conventions

## Python Backend Standards

### Logging (MANDATORY)
Every Python module MUST start with:
```python
import logging
logger = logging.getLogger(__name__)
```

**Correct Usage:**
```python
logger.info("Starting audio processing for song: %s", song_id)
logger.warning("File not found, using default: %s", default_path)
try:
    process_audio(file_path)
except Exception as e:
    logger.error("Audio processing failed for %s: %s", file_path, e, exc_info=True)
    raise
```

**Forbidden:**
- `print()` statements in production code
- `logging.info()` direct usage
- Silent exception handling (`except: pass`)

### Code Formatting
- **Black**: Code formatting with default settings
- **isort**: Import organization
- **PyLint**: Code quality checks
- **Type Hints**: Use where helpful, not mandatory for all functions

### Naming Conventions
- **Functions/Variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private methods**: `_leading_underscore`

## TypeScript Frontend Standards

### Code Quality Tools
- **ESLint**: Linting with React and TypeScript rules
- **Prettier**: Code formatting
- **TypeScript**: Strict mode enabled

### Naming Conventions
- **Components**: `PascalCase` (e.g., `SongLibrary.tsx`)
- **Files**: `kebab-case` for non-components, `PascalCase` for components
- **Functions/Variables**: `camelCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Types/Interfaces**: `PascalCase`

### React Patterns
- **Functional Components**: Prefer over class components
- **Hooks**: Custom hooks start with `use`
- **Props**: Define interfaces for all component props
- **State**: Use Zustand for global state, useState for local state

### File Organization
- **Components**: Group related components in folders
- **Hooks**: Custom hooks in `hooks/` directory
- **Utils**: Utility functions in `utils/` directory
- **Types**: Type definitions in `types/` directory

## General Conventions

### Error Handling
- Always provide meaningful error messages
- Use structured logging with context
- Handle edge cases explicitly
- Never suppress errors silently

### Testing
- Unit tests for business logic
- Integration tests for API endpoints
- Test file naming: `test_*.py` (Python), `*.test.ts` (TypeScript)
- Minimum 80% code coverage for backend

### Documentation
- README files for each major component
- Inline comments for complex logic
- API documentation for all endpoints
- Type definitions serve as documentation