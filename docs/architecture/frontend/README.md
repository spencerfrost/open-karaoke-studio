# Frontend Architecture - Open Karaoke Studio

**Last Updated**: June 15, 2025  
**Status**: Active Development  
**Technology Stack**: React 19+ • TypeScript • Vite • Tailwind CSS • Shadcn/UI

## 🎯 Overview

The Open Karaoke Studio frontend is a modern React application built with TypeScript that provides an intuitive interface for managing karaoke libraries, searching for songs, and controlling playback. The architecture emphasizes component reusability, type safety, and excellent user experience across desktop and mobile devices.

## 🏗️ Architecture Principles

### Core Technologies
- **React 19+** with functional components and hooks
- **TypeScript** for full type safety and developer experience
- **Vite** for fast development and optimized builds
- **Tailwind CSS** for utility-first styling
- **Shadcn/UI** for high-quality, accessible components

### State Management Strategy
- **Zustand** for global application state
- **React Context** for configuration and settings
- **TanStack Query** for server state management and caching
- **React Hooks** for local component state

### Integration & Communication
- **Socket.IO** for real-time WebSocket connections
- **RESTful API** integration with the Flask backend
- **React Router** for client-side routing

## 📁 Project Structure

```
frontend/src/
├── components/           # Reusable UI components
│   ├── songs/           # Song-related components
│   ├── ui/              # Base UI components (Shadcn)
│   ├── layout/          # Layout and navigation
│   └── forms/           # Form components
├── hooks/               # Custom React hooks
├── lib/                 # Utility functions and configurations
├── pages/               # Route-level components
├── services/            # API integration and external services
├── stores/              # Zustand state stores
├── types/               # TypeScript type definitions
└── styles/              # Global styles and Tailwind config
```

## 🧩 Component Architecture

### Design System
The frontend uses a layered component architecture:

1. **Base Components** (Shadcn/UI) - Accessible, reusable primitives
2. **Composite Components** - Domain-specific combinations
3. **Feature Components** - Complete user workflows
4. **Page Components** - Route-level containers

### Key Component Categories

#### Song Management
- **Song Library Interface** - Browse, search, and filter songs
- **Song Details Dialog** - Rich metadata display and preview
- **Song Upload Flow** - Multi-step song addition workflow

#### User Interface
- **Responsive Navigation** - Mobile-first navigation patterns
- **Search Interface** - Advanced search with filters
- **Real-time Updates** - Live status and progress indicators

## 📊 State Management

### Global State (Zustand)
- **Library State** - Song library data and filters
- **Player State** - Current playback information
- **UI State** - Modal states, navigation, and preferences

### Server State (TanStack Query)
- **Song Data** - Cached song metadata and search results
- **Upload Progress** - Real-time upload status
- **System Status** - Backend health and capabilities

### Local State (React Hooks)
- **Form State** - Input validation and submission
- **Component State** - UI interactions and temporary data

## 🔌 Backend Integration

### API Client Architecture
- **Service Layer** - Abstracted API communication
- **Error Handling** - Consistent error boundaries and user feedback
- **Loading States** - Skeleton screens and progress indicators
- **Caching Strategy** - Optimistic updates and background refresh

### Real-time Features
- **WebSocket Integration** - Live updates for uploads and processing
- **Status Synchronization** - Real-time library state updates
- **Progress Tracking** - Live feedback for long-running operations

## 📱 Responsive Design

### Mobile-First Approach
- **Breakpoint Strategy** - Tailwind responsive utilities
- **Touch-Friendly Interface** - Appropriate touch targets
- **Progressive Enhancement** - Desktop features enhance mobile base

### Performance Optimization
- **Code Splitting** - Route-based lazy loading
- **Bundle Optimization** - Tree shaking and dependency analysis
- **Image Optimization** - Responsive images and lazy loading

## 🧪 Development Patterns

### TypeScript Integration
- **Strict Type Checking** - Comprehensive type coverage
- **Interface Definitions** - API response and component props
- **Generic Components** - Reusable, type-safe patterns

### Testing Strategy
- **Component Testing** - Unit tests for component logic
- **Integration Testing** - API integration and user workflows
- **Accessibility Testing** - Screen reader and keyboard navigation

## 📚 Documentation Structure

### Component Documentation
- **[Component Architecture](component-architecture.md)** - Design patterns and organization
- **[UI Design System](ui-design-system.md)** - Shadcn/Tailwind integration
- **[State Management](state-management.md)** - State handling patterns

### Feature Documentation
- **[Song Library Interface](components/song-library-interface.md)** - Library browsing and management
- **[Song Details System](components/song-details-system.md)** - Metadata display and editing
- **[Upload Workflow](components/upload-workflow.md)** - Multi-step song upload and processing
- **[iTunes Integration](components/itunes-integration.md)** - Direct iTunes API integration for metadata
- **[Infinite Scrolling](components/infinite-scrolling.md)** - Performance-optimized infinite scroll implementation

### Integration Documentation
- **[API Integration](integrations/api-integration.md)** - Backend communication patterns
- **[WebSocket Client](integrations/websocket-client.md)** - Real-time update handling
- **[Routing & Navigation](integrations/routing-navigation.md)** - Navigation and URL management

### Performance Documentation
- **[Bundle Optimization](performance/bundle-optimization.md)** - Build optimization and code splitting
- **[Testing Patterns](performance/testing-patterns.md)** - Component and integration testing
- **[Accessibility Implementation](performance/accessibility.md)** - WCAG 2.1 AA compliance and inclusive design

## 🚀 Getting Started

### Development Setup
```bash
cd frontend
pnpm install
pnpm dev
```

### Key Development Commands
```bash
pnpm dev          # Start development server
pnpm build        # Build for production
pnpm type-check   # TypeScript type checking
pnpm lint         # ESLint code quality
pnpm test         # Run test suite
```

## 🔗 Related Documentation

- **[Backend Architecture](../backend/README.md)** - API and service layer
- **[Integration Architecture](../integration/README.md)** - Frontend/backend communication
- **[Project Overview](../project-overview.md)** - Complete system architecture

---

**Next Steps**: Explore the component architecture documentation to understand the specific patterns and implementations used throughout the application.
