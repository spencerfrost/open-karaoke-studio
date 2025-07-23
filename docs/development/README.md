# Development Guide

Welcome to the Open Karaoke Studio development documentation! This guide covers everything you need to know to contribute to the project.

## 🚀 Quick Start for Developers

### New to the Project?

1. **Read the [Development Commands](dev-commands.md)** - Everything you need to start developing!
2. **[Architecture Overview](../architecture/README.md)** - Understand the system design
3. **Run `./scripts/dev.sh`** - Starts all services with local network access

### Ready to Code?

- **Frontend development** - Work in `frontend/` directory (React + TypeScript + Tailwind)
- **Backend development** - Work in `backend/` directory (Python + Flask + Celery)
- **Testing** - Each service has its own testing setup (see individual README files)

### Development Tooling

✅ **Python**: pylance/pylint work perfectly in the `backend/` directory
✅ **JavaScript**: ESLint/TypeScript work perfectly in the `frontend/` directory
✅ **No complex workspace setup** - Each service uses its native tooling
✅ **Simple script orchestration** - Just 3 essential development scripts

## 📚 Development Documentation

### Getting Started

- **[Development Setup](setup/README.md)** - _Coming Soon_ - Complete environment setup
- **[IDE Configuration](setup/ide-setup.md)** - _Coming Soon_ - Editor setup and plugins
- **[Dependencies Guide](setup/dependencies.md)** - _Coming Soon_ - Understanding the tech stack

### Contributing

- **[Contributing Overview](contributing/README.md)** - _Coming Soon_ - How to get involved
- **[Code Standards](contributing/code-standards.md)** - _Coming Soon_ - Style guides and conventions
- **[Testing Strategy](contributing/testing.md)** - _Coming Soon_ - Test requirements and practices
- **[Pull Request Process](contributing/pull-requests.md)** - _Coming Soon_ - Submission guidelines
- **[Issue Reporting](contributing/issue-reporting.md)** - _Coming Soon_ - Bug reports and feature requests

### Development Guides

- **[Adding Features](guides/adding-features.md)** - _Coming Soon_ - Feature development workflow
- **[Database Changes](guides/database-changes.md)** - _Coming Soon_ - Schema migrations and data models
- **[API Development](guides/api-development.md)** - _Coming Soon_ - Backend endpoint patterns
- **[Frontend Components](guides/frontend-components.md)** - _Coming Soon_ - React component development

### Reference Materials

- **[Coding Standards](coding-standards.md)** - Backend coding practices and error handling patterns
- **[Configuration Guide](configuration.md)** - Environment and app configuration
- **[Testing Documentation](testing.md)** - Test suite and coverage
- **[Architectural Cleanup Plan](ARCHITECTURAL_CLEANUP_PLAN.md)** - Recent infrastructure improvements

- **[Coding Patterns](reference/coding-patterns.md)** - _Coming Soon_ - Established patterns and practices
- **[Error Handling](reference/error-handling.md)** - _Coming Soon_ - Error management strategies
- **[Performance Guidelines](reference/performance.md)** - _Coming Soon_ - Optimization best practices

## 🏗️ Architecture for Developers

### System Overview

Open Karaoke Studio is built with a clean, service-oriented architecture:

- **Frontend**: React/TypeScript with feature-based organization
- **Backend**: Python/Flask with service layer pattern
- **Database**: SQLite with SQLAlchemy ORM
- **Processing**: Async jobs with Celery and Redis
- **APIs**: RESTful endpoints with WebSocket real-time features

### Key Principles

- **Service-oriented design** - Business logic in specialized services
- **Clean architecture** - Dependency inversion and interface segregation
- **Test-driven development** - Comprehensive test coverage
- **Documentation-first** - Features documented as they're developed

### Technology Stack

#### Frontend

- **React 19** with TypeScript for type safety
- **Vite** for fast development and building
- **Tailwind CSS** + **Shadcn/UI** for consistent styling
- **TanStack Query** for API state management
- **Feature-based** component organization

#### Backend

- **Flask** with blueprint architecture
- **SQLAlchemy** + **Alembic** for database management
- **Celery** + **Redis** for background processing
- **Demucs** + **PyTorch** for AI audio processing
- **Service layer** for business logic separation

## 🔧 Development Workflow

### Current Development Process

1. **Issue Creation** - Identify and document requirements
2. **Branch Creation** - Feature branches from `develop`
3. **Implementation** - Follow established patterns
4. **Testing** - Unit and integration tests
5. **Documentation** - Update relevant docs
6. **Pull Request** - Code review and merge

### Code Quality Standards

- **Type Safety** - TypeScript for frontend, type hints for Python
- **Error Handling** - Comprehensive error boundaries and logging
- **Testing** - Unit tests for services, integration tests for workflows
- **Documentation** - Code comments and user-facing docs

## 📊 Project Statistics

| Metric              | Value                      |
| ------------------- | -------------------------- |
| **Backend Files**   | 156 Python files           |
| **Lines of Code**   | 15,000+ (application code) |
| **API Endpoints**   | 35 REST endpoints          |
| **Services**        | 14 business logic services |
| **Test Coverage**   | 6,500+ lines of tests      |
| **Database Tables** | 4 core models              |

## 🎯 Current Development Focus

### Active Areas

- **Frontend Enhancement** - Improving user experience and component architecture
- **Performance Optimization** - Faster processing and better resource usage
- **Feature Stabilization** - Completing core functionality documentation
- **Test Coverage** - Expanding automated testing

### Upcoming Priorities

- **Mobile Optimization** - Responsive design improvements
- **Advanced Features** - Real-time collaboration and advanced audio processing
- **DevOps** - Deployment automation and monitoring
- **Documentation** - Comprehensive user and developer guides

## 🤝 How to Contribute

### Types of Contributions Welcome

- **Bug fixes** - Issues and improvements
- **Feature development** - New capabilities and enhancements
- **Documentation** - User guides and developer docs
- **Testing** - Test coverage and quality assurance
- **Performance** - Optimization and profiling

### Skill Levels

- **Beginner** - Documentation, bug reports, simple fixes
- **Intermediate** - Feature development, component creation
- **Advanced** - Architecture decisions, performance optimization

### Getting Started

1. **Review** [Architecture Overview](../architecture/README.md)
2. **Set up** development environment (guide coming soon)
3. **Find** a good first issue (will be labeled)
4. **Follow** contribution guidelines (coming soon)

## 🔍 Development Resources

### Internal Documentation

- **[Architecture Overview](../architecture/README.md)** - System design and patterns
- **[API Documentation](../api/README.md)** - Backend endpoints and integration
- **[Feature Documentation](../features/README.md)** - Current capabilities and implementation

### External Resources

- **React** - [React Documentation](https://react.dev/)
- **Flask** - [Flask Documentation](https://flask.palletsprojects.com/)
- **TypeScript** - [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- **Tailwind CSS** - [Tailwind Documentation](https://tailwindcss.com/docs)

## 📋 Development Status

| Area                       | Status                | Next Steps                     |
| -------------------------- | --------------------- | ------------------------------ |
| **Core Architecture**      | ✅ Stable             | Performance optimization       |
| **API Layer**              | ✅ Complete           | Additional endpoints as needed |
| **Service Layer**          | ✅ Mature             | Feature-specific enhancements  |
| **Frontend Components**    | 🟡 Active Development | Mobile optimization            |
| **Testing Infrastructure** | 🟡 In Progress        | Expanded coverage              |
| **Documentation**          | 🟡 In Progress        | Complete user guides           |

## 🛠️ Development Tools

### Recommended Setup

- **IDE**: VS Code with relevant extensions
- **Python**: 3.8+ with virtual environment
- **Node.js**: 16+ with pnpm package manager
- **Database**: SQLite browser for development
- **Git**: Version control with conventional commits

### Useful Commands

```bash
# Backend development
cd backend && source venv/bin/activate
python -m pytest  # Run tests
python app/main.py  # Start dev server

# Frontend development
cd frontend
pnpm dev  # Start dev server
pnpm test  # Run tests
pnpm build  # Production build
```

---

**Ready to contribute?** Start with the [Architecture Overview](../architecture/README.md) to understand the system, then check back here as development guides are completed.

**Questions?** Open a discussion or issue on GitHub - we're happy to help new contributors get started!
