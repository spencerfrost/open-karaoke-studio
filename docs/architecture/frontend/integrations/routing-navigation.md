# Routing and Navigation Architecture

## Overview

The routing and navigation system provides client-side routing capabilities using React Router v7, managing application navigation, route protection, and dynamic content loading. The architecture emphasizes mobile-first navigation patterns with a bottom navigation bar optimized for touch interfaces.

## Current Implementation Status

**Primary Files**:
- `frontend/src/App.tsx` - Main routing configuration and route definitions
- `frontend/src/components/layout/AppLayout.tsx` - Layout wrapper with navigation
- `frontend/src/components/layout/NavBar.tsx` - Bottom navigation bar component
- `frontend/src/hooks/useNavigation.ts` - Navigation utilities and helpers

**Status**: ✅ Complete with mobile-optimized navigation  
**Router Version**: React Router v7.6.0

## Core Responsibilities

### Client-Side Routing
- **Single Page Application**: Full client-side routing without page refreshes
- **Dynamic Route Matching**: Support for parameterized routes and dynamic content
- **Route Protection**: Authentication-based route access control
- **Nested Routing**: Hierarchical route structure for complex layouts

### Mobile-First Navigation
- **Bottom Navigation**: Touch-optimized bottom navigation bar
- **Tab-Based Interface**: Primary navigation through tabbed interface
- **Responsive Design**: Adaptive navigation for different screen sizes
- **Touch-Friendly**: Large touch targets and gesture support

### State Management Integration
- **Route State Persistence**: Maintain application state across route changes
- **Deep Linking**: Support for bookmarkable URLs with application state
- **Navigation History**: Browser history integration with back/forward support
- **Modal Navigation**: Overlay navigation that preserves underlying route state

## Implementation Details

### Main Router Configuration

```typescript
// App.tsx - Main routing setup
import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";

import { SongsProvider } from "./context/SongsContext";
import { SettingsProvider } from "./context/SettingsContext";

// Page components
import LibraryPage from "./pages/Library";
import AddSongPage from "./pages/AddSong";
import SettingsPage from "./pages/Settings";
import StagePage from "./pages/Stage";
import SongPlayerPage from "./pages/SongPlayer";
import PerformanceControlsPage from "./pages/PerformanceControlsPage";

const App: React.FC = () => {
  return (
    <SettingsProvider>
      <SongsProvider>
        <Router>
          <Routes>
            {/* Main application routes */}
            <Route path="/" element={<LibraryPage />} />
            <Route path="/add" element={<AddSongPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/stage" element={<StagePage />} />
            <Route path="/controls" element={<PerformanceControlsPage />} />
            
            {/* Dynamic routes with parameters */}
            <Route path="/player/:id" element={<SongPlayerPage />} />
            
            {/* Fallback route */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </SongsProvider>
    </SettingsProvider>
  );
};

export default App;
```

### Layout Integration

```typescript
// AppLayout.tsx - Layout wrapper with navigation
import React, { ReactNode } from "react";
import NavBar from "./NavBar";
import { Music, Upload, List, Sliders } from "lucide-react";

interface AppLayoutProps {
  children: ReactNode;
}

const navigationItems = [
  { name: "Library", path: "/", icon: Music },
  { name: "Add", path: "/add", icon: Upload },
  { name: "Stage", path: "/stage", icon: List },
  { name: "Controls", path: "/controls", icon: Sliders },
];

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  return (
    <div className="flex flex-col h-screen">
      {/* Background decorative elements */}
      <div className="vintage-texture-overlay" />
      <div className="vintage-sunburst-pattern" />
      
      {/* Main content area */}
      <main className="flex-1 overflow-auto p-4 relative z-10">
        {children}
      </main>
      
      {/* Bottom navigation */}
      <NavBar items={navigationItems} />
    </div>
  );
};

export default AppLayout;
```

### Navigation Bar Component

```typescript
// NavBar.tsx - Bottom navigation implementation
import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

interface NavItem {
  name: string;
  path: string;
  icon: LucideIcon;
}

interface NavBarProps {
  items: NavItem[];
}

const NavBar: React.FC<NavBarProps> = ({ items }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path: string): boolean => {
    return location.pathname === path;
  };

  return (
    <nav className="flex h-18 bg-russet border-t-1 border-border/80 sticky bottom-0 z-20 gap-4 pb-4 pt-2 md:py-1">
      {items.map((item) => {
        const active = isActive(item.path);
        const Icon = item.icon;

        return (
          <Button
            key={item.name}
            variant="ghost"
            onClick={() => navigate(item.path)}
            className={`flex-1 flex flex-col items-center justify-center gap-1 text-background h-full rounded-none ${
              active 
                ? "bg-background/20 text-background font-semibold" 
                : "hover:bg-background/10"
            }`}
          >
            <Icon className="h-6 w-6" />
            <span className="text-xs font-medium">{item.name}</span>
          </Button>
        );
      })}
    </nav>
  );
};

export default NavBar;
```

### Navigation Hooks

```typescript
// useNavigation.ts - Navigation utilities
import { useNavigate, useLocation, useParams } from 'react-router-dom';
import { useCallback } from 'react';

export const useAppNavigation = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const params = useParams();

  // Navigate to specific pages with type safety
  const navigateToLibrary = useCallback(() => {
    navigate('/');
  }, [navigate]);

  const navigateToPlayer = useCallback((songId: string) => {
    navigate(`/player/${songId}`);
  }, [navigate]);

  const navigateToAddSong = useCallback(() => {
    navigate('/add');
  }, [navigate]);

  const navigateToStage = useCallback(() => {
    navigate('/stage');
  }, [navigate]);

  const navigateToControls = useCallback(() => {
    navigate('/controls');
  }, [navigate]);

  // Navigation with state preservation
  const navigateWithState = useCallback((
    path: string, 
    state?: Record<string, any>
  ) => {
    navigate(path, { state });
  }, [navigate]);

  // Go back with fallback
  const goBack = useCallback((fallbackPath = '/') => {
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate(fallbackPath);
    }
  }, [navigate]);

  // Check if currently on specific route
  const isCurrentRoute = useCallback((path: string) => {
    return location.pathname === path;
  }, [location.pathname]);

  // Get current route parameters
  const getCurrentParams = useCallback(() => {
    return params;
  }, [params]);

  return {
    navigate,
    location,
    params,
    navigateToLibrary,
    navigateToPlayer,
    navigateToAddSong,
    navigateToStage,
    navigateToControls,
    navigateWithState,
    goBack,
    isCurrentRoute,
    getCurrentParams,
  };
};

// Hook for handling route-specific logic
export const useRouteGuard = (
  requiredConditions: () => boolean,
  redirectPath = '/'
) => {
  const { navigate } = useAppNavigation();

  React.useEffect(() => {
    if (!requiredConditions()) {
      navigate(redirectPath, { replace: true });
    }
  }, [requiredConditions, navigate, redirectPath]);
};

// Hook for preserving scroll position across routes
export const useScrollRestoration = () => {
  const location = useLocation();

  React.useEffect(() => {
    // Restore scroll position or scroll to top
    const savedPosition = sessionStorage.getItem(`scroll-${location.pathname}`);
    
    if (savedPosition) {
      window.scrollTo(0, parseInt(savedPosition, 10));
    } else {
      window.scrollTo(0, 0);
    }

    // Save scroll position when leaving route
    return () => {
      sessionStorage.setItem(`scroll-${location.pathname}`, window.scrollY.toString());
    };
  }, [location]);
};
```

### Route-Specific Components

```typescript
// Example: Library Page with navigation integration
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AppLayout from '@/components/layout/AppLayout';
import { useAppNavigation, useScrollRestoration } from '@/hooks/useNavigation';

const LibraryPage: React.FC = () => {
  const { navigateToPlayer } = useAppNavigation();
  useScrollRestoration();

  const handleSongSelect = (song: Song) => {
    navigateToPlayer(song.id);
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        <LibraryHeader />
        <SearchableInfiniteArtists 
          onSongSelect={handleSongSelect}
        />
      </div>
    </AppLayout>
  );
};

// Example: Song Player Page with parameter handling
const SongPlayerPage: React.FC = () => {
  const { params, goBack } = useAppNavigation();
  const songId = params.id;

  const { data: song, isLoading } = useSong(songId);

  if (isLoading) {
    return <LoadingPage />;
  }

  if (!song) {
    return <NotFoundPage onBack={goBack} />;
  }

  return (
    <AppLayout>
      <SongPlayer song={song} onBack={goBack} />
    </AppLayout>
  );
};
```

## Integration Points

### State Management Integration
- **Route State Persistence**: Zustand stores maintain state across navigation
- **Query Parameter Sync**: React Query state synchronized with URL parameters
- **Form State Preservation**: Form data preserved during navigation interruptions
- **Modal State Management**: Modal state persisted across route changes

### Component Integration
- **Layout Consistency**: All pages use consistent layout wrapper
- **Navigation Context**: Navigation state available throughout component tree
- **Breadcrumb Integration**: Automatic breadcrumb generation from route hierarchy
- **Loading States**: Route-level loading indicators during navigation

### Backend Integration
- **Deep Linking**: URLs correspond to backend resource identifiers
- **API Route Mapping**: Frontend routes aligned with backend API endpoints
- **Authentication Routes**: Protected routes integrate with authentication state
- **Error Handling**: Route-level error boundaries for API failures

## Design Patterns

### Route Organization Pattern
```typescript
// Centralized route configuration
export const routes = {
  library: '/',
  addSong: '/add',
  songPlayer: '/player/:id',
  stage: '/stage',
  controls: '/controls',
  settings: '/settings',
} as const;

// Type-safe route helpers
export const generatePath = {
  songPlayer: (id: string) => `/player/${id}`,
  songEdit: (id: string) => `/edit/${id}`,
} as const;

// Route validation
export const isValidRoute = (path: string): boolean => {
  return Object.values(routes).some(route => 
    new RegExp(`^${route.replace(/:[^/]+/g, '[^/]+')}$`).test(path)
  );
};
```

### Protected Route Pattern
```typescript
// Higher-order component for route protection
interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAuth?: boolean;
  requireRole?: string[];
  fallbackPath?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireAuth = false,
  requireRole = [],
  fallbackPath = '/login'
}) => {
  const { user } = useAuth();
  const { navigate } = useAppNavigation();

  useEffect(() => {
    if (requireAuth && !user) {
      navigate(fallbackPath, { replace: true });
      return;
    }

    if (requireRole.length > 0 && !requireRole.some(role => user?.roles.includes(role))) {
      navigate('/unauthorized', { replace: true });
      return;
    }
  }, [user, requireAuth, requireRole, navigate, fallbackPath]);

  if (requireAuth && !user) {
    return <LoadingSpinner />;
  }

  return <>{children}</>;
};

// Usage in route configuration
<Route 
  path="/admin" 
  element={
    <ProtectedRoute requireAuth requireRole={['admin']}>
      <AdminPage />
    </ProtectedRoute>
  } 
/>
```

### Modal Navigation Pattern
```typescript
// Modal navigation that preserves background route
const useModalNavigation = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
  const openModal = useCallback((modalPath: string) => {
    navigate(modalPath, { 
      state: { backgroundLocation: location } 
    });
  }, [location, navigate]);
  
  const closeModal = useCallback(() => {
    const backgroundLocation = location.state?.backgroundLocation;
    if (backgroundLocation) {
      navigate(backgroundLocation.pathname, { replace: true });
    } else {
      navigate(-1);
    }
  }, [location, navigate]);
  
  return { openModal, closeModal };
};

// Modal route rendering
const App = () => {
  const location = useLocation();
  const backgroundLocation = location.state?.backgroundLocation;
  
  return (
    <>
      <Routes location={backgroundLocation || location}>
        <Route path="/" element={<LibraryPage />} />
        <Route path="/add" element={<AddSongPage />} />
      </Routes>
      
      {/* Modal routes */}
      {backgroundLocation && (
        <Routes>
          <Route path="/song/:id/details" element={<SongDetailsModal />} />
          <Route path="/settings" element={<SettingsModal />} />
        </Routes>
      )}
    </>
  );
};
```

## Performance Considerations

### Code Splitting and Lazy Loading
```typescript
// Lazy load page components for better performance
const LibraryPage = lazy(() => import('./pages/Library'));
const AddSongPage = lazy(() => import('./pages/AddSong'));
const SongPlayerPage = lazy(() => import('./pages/SongPlayer'));

// Wrap lazy components with suspense
const App = () => (
  <Router>
    <Suspense fallback={<PageLoadingSpinner />}>
      <Routes>
        <Route path="/" element={<LibraryPage />} />
        <Route path="/add" element={<AddSongPage />} />
        <Route path="/player/:id" element={<SongPlayerPage />} />
      </Routes>
    </Suspense>
  </Router>
);
```

### Navigation Performance
- **Prefetching**: Preload likely next routes based on user behavior
- **Route Caching**: Cache route components to prevent re-mounting
- **Transition Optimization**: Smooth transitions without blocking UI
- **Memory Management**: Clean up resources when routes unmount

### Mobile Optimization
- **Touch Gestures**: Swipe gestures for navigation on mobile devices
- **Haptic Feedback**: Tactile feedback for navigation actions
- **Animation Performance**: Hardware-accelerated navigation transitions
- **Battery Optimization**: Minimize battery drain from navigation operations

## Accessibility Features

### Keyboard Navigation
```typescript
// Keyboard navigation support
const useKeyboardNavigation = () => {
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      // Alt + number for direct navigation
      if (event.altKey && event.key >= '1' && event.key <= '4') {
        const index = parseInt(event.key) - 1;
        const paths = ['/', '/add', '/stage', '/controls'];
        navigate(paths[index]);
      }
      
      // Escape to go back
      if (event.key === 'Escape') {
        navigate(-1);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [navigate]);
};
```

### Screen Reader Support
- **ARIA Labels**: Proper labeling of navigation elements
- **Focus Management**: Logical focus order during navigation
- **Route Announcements**: Announce route changes to screen readers
- **Skip Links**: Quick navigation to main content areas

### Visual Accessibility
- **High Contrast**: Navigation elements work with high contrast themes
- **Large Touch Targets**: Minimum 44px touch targets for navigation
- **Focus Indicators**: Clear visual focus indicators for keyboard users
- **Reduced Motion**: Respect user preferences for reduced motion

## Error Handling

### Route Error Boundaries
```typescript
// Route-level error boundary
class RouteErrorBoundary extends React.Component<
  { children: React.ReactNode; fallback?: React.ComponentType },
  { hasError: boolean; error?: Error }
> {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Route error:', error, errorInfo);
    // Report to error tracking service
    reportError(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      const FallbackComponent = this.props.fallback || DefaultErrorPage;
      return <FallbackComponent error={this.state.error} />;
    }

    return this.props.children;
  }
}

// Wrap routes with error boundaries
<Route 
  path="/player/:id" 
  element={
    <RouteErrorBoundary fallback={PlayerErrorPage}>
      <SongPlayerPage />
    </RouteErrorBoundary>
  } 
/>
```

### 404 and Navigation Errors
```typescript
// 404 Page with helpful navigation
const NotFoundPage: React.FC = () => {
  const { navigateToLibrary } = useAppNavigation();
  
  return (
    <AppLayout>
      <div className="flex flex-col items-center justify-center min-h-96 space-y-4">
        <h1 className="text-2xl font-bold">Page Not Found</h1>
        <p className="text-muted-foreground">
          The page you're looking for doesn't exist.
        </p>
        <Button onClick={navigateToLibrary}>
          Return to Library
        </Button>
      </div>
    </AppLayout>
  );
};
```

## Future Enhancements

### Advanced Navigation Features
- **Gesture Navigation**: Swipe gestures for mobile navigation
- **Voice Navigation**: Voice commands for hands-free navigation
- **Context-Aware Navigation**: Smart navigation based on user behavior
- **Progressive Web App**: PWA navigation patterns with offline support

### Performance Improvements
- **Route Preloading**: Intelligent preloading of likely next routes
- **Navigation Analytics**: Track navigation patterns for optimization
- **Memory Optimization**: Advanced memory management for large applications
- **Service Worker Integration**: Offline navigation with service workers

---

**Navigation Benefits**: This routing architecture provides a smooth, mobile-optimized navigation experience that integrates seamlessly with the application's state management and provides excellent accessibility and performance characteristics.
