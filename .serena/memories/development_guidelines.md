# Open Karaoke Studio - Development Guidelines

## Design Patterns & Architecture

### Backend Patterns
- **Service Layer Pattern**: Business logic in service classes
- **Repository Pattern**: Data access abstraction
- **Dependency Injection**: Services injected where needed
- **Event-Driven**: WebSocket events for real-time updates
- **Background Jobs**: Celery for heavy processing tasks

### Frontend Patterns
- **Component Composition**: Small, reusable components
- **Custom Hooks**: Logic extraction from components
- **Centralized State**: Zustand for global state management
- **Data Fetching**: TanStack Query for server state
- **Type Safety**: Comprehensive TypeScript usage

## Key Principles

### Code Organization
- **Separation of Concerns**: Clear boundaries between layers
- **Single Responsibility**: Each class/function has one purpose
- **DRY (Don't Repeat Yourself)**: Reusable utilities and components
- **SOLID Principles**: Especially Single Responsibility and Dependency Inversion

### Error Handling
- **Fail Fast**: Validate inputs early
- **Graceful Degradation**: Handle failures without crashing
- **Comprehensive Logging**: All errors logged with context
- **User-Friendly Messages**: Clear error communication

### Performance Considerations
- **Lazy Loading**: Load components and data on demand
- **Caching**: Use React Query for server state caching
- **Background Processing**: Long-running tasks via Celery
- **Efficient Database Queries**: Avoid N+1 queries

## Technology-Specific Guidelines

### React/TypeScript
- Prefer functional components over class components
- Use custom hooks for reusable logic
- Define interfaces for all props and state
- Use strict TypeScript configuration
- Implement proper error boundaries

### Python/Flask
- Follow PEP 8 style guidelines
- Use type hints where beneficial
- Implement comprehensive logging
- Create service interfaces for testing
- Use SQLAlchemy ORM best practices

### Database Design
- Normalize data appropriately
- Use indexes for query performance
- Implement proper foreign key relationships
- Plan for data migration strategies
- Consider data retention policies

## Development Workflow
1. **Feature Planning**: Break down features into small tasks
2. **Branch Strategy**: Feature branches from main
3. **Code Review**: All changes reviewed before merge
4. **Testing**: Write tests for new functionality
5. **Documentation**: Update docs with changes
6. **Deployment**: Automated deployment pipeline