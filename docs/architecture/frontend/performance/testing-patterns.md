# Testing Patterns - Open Karaoke Studio Frontend

**Last Updated**: December 19, 2024  
**Status**: Development Ready  
**Technology Stack**: Vitest • React Testing Library • MSW • Playwright • Testing Library

## 🎯 Overview

The frontend testing strategy encompasses unit testing, integration testing, and end-to-end testing to ensure robust functionality, excellent user experience, and maintainable code. The testing approach emphasizes realistic user scenarios, accessibility compliance, and performance validation.

## 🏗️ Testing Architecture

### Testing Stack Overview

```typescript
// Primary testing dependencies
{
  "devDependencies": {
    // Core testing framework
    "vitest": "^2.0.5",
    "jsdom": "^25.0.1",
    
    // React testing utilities
    "@testing-library/react": "^16.0.1",
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/user-event": "^14.5.2",
    
    // API mocking
    "msw": "^2.5.4",
    
    // E2E testing
    "@playwright/test": "^1.48.2",
    
    // Testing utilities
    "test-utils": "workspace:*",
    "@types/testing-library__jest-dom": "^6.0.0"
  }
}
```

### Test Configuration

```typescript
// vitest.config.ts - Comprehensive test configuration
import { defineConfig } from 'vitest/config';
import { resolve } from 'path';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    // Test environment
    environment: 'jsdom',
    
    // Global setup
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    
    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        'dist/',
      ],
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80,
        },
      },
    },
    
    // Test matching patterns
    include: ['src/**/*.{test,spec}.{js,ts,jsx,tsx}'],
    exclude: ['node_modules/', 'dist/', '.vite/'],
    
    // Timeout configuration
    testTimeout: 10000,
    hookTimeout: 10000,
  },
  
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
});
```

### Test Setup Configuration

```typescript
// src/test/setup.ts - Global test setup
import '@testing-library/jest-dom';
import { expect, afterEach, beforeAll, afterAll } from 'vitest';
import { cleanup } from '@testing-library/react';
import { server } from './mocks/server';

// Cleanup after each test case
afterEach(() => {
  cleanup();
});

// Establish API mocking before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

// Reset any request handlers that are declared as one-time overrides
afterEach(() => server.resetHandlers());

// Clean up after the tests are finished
afterAll(() => server.close());

// Extend expect with custom matchers
expect.extend({
  toBeAccessible: async (received) => {
    // Custom accessibility matcher
    const { getByRole } = received;
    
    try {
      // Check for proper ARIA labels, roles, etc.
      getByRole('button', { name: /./i }); // Should have accessible name
      return {
        message: () => `Element is accessible`,
        pass: true,
      };
    } catch {
      return {
        message: () => `Element is not accessible`,
        pass: false,
      };
    }
  },
});

// Mock IntersectionObserver for components using infinite scroll
Object.defineProperty(window, 'IntersectionObserver', {
  writable: true,
  value: class IntersectionObserver {
    constructor(callback: Function) {
      this.callback = callback;
    }
    
    observe() {
      return null;
    }
    
    disconnect() {
      return null;
    }
    
    unobserve() {
      return null;
    }
  },
});

// Mock ResizeObserver
Object.defineProperty(window, 'ResizeObserver', {
  writable: true,
  value: class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  },
});

// Mock HTMLMediaElement methods
Object.defineProperty(HTMLMediaElement.prototype, 'play', {
  writable: true,
  value: jest.fn(() => Promise.resolve()),
});

Object.defineProperty(HTMLMediaElement.prototype, 'pause', {
  writable: true,
  value: jest.fn(),
});
```

## 🧪 Unit Testing Patterns

### Component Testing

```typescript
// src/components/songs/SongCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { SongCard } from './SongCard';
import { createMockSong } from '@/test/factories/songFactory';
import { TestWrapper } from '@/test/utils/TestWrapper';

describe('SongCard', () => {
  const mockSong = createMockSong();
  const mockOnSelect = vi.fn();
  
  beforeEach(() => {
    mockOnSelect.mockClear();
  });
  
  it('displays song information correctly', () => {
    render(
      <TestWrapper>
        <SongCard song={mockSong} onSelect={mockOnSelect} />
      </TestWrapper>
    );
    
    expect(screen.getByText(mockSong.title)).toBeInTheDocument();
    expect(screen.getByText(mockSong.artist)).toBeInTheDocument();
    expect(screen.getByText(mockSong.album)).toBeInTheDocument();
  });
  
  it('calls onSelect when clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <SongCard song={mockSong} onSelect={mockOnSelect} />
      </TestWrapper>
    );
    
    await user.click(screen.getByRole('button', { name: /view details/i }));
    
    expect(mockOnSelect).toHaveBeenCalledWith(mockSong);
    expect(mockOnSelect).toHaveBeenCalledTimes(1);
  });
  
  it('shows duration in correct format', () => {
    const songWithDuration = createMockSong({ duration: 245 }); // 4:05
    
    render(
      <TestWrapper>
        <SongCard song={songWithDuration} onSelect={mockOnSelect} />
      </TestWrapper>
    );
    
    expect(screen.getByText('4:05')).toBeInTheDocument();
  });
  
  it('handles missing album cover gracefully', () => {
    const songWithoutCover = createMockSong({ coverUrl: null });
    
    render(
      <TestWrapper>
        <SongCard song={songWithoutCover} onSelect={mockOnSelect} />
      </TestWrapper>
    );
    
    const img = screen.getByRole('img', { name: /album cover/i });
    expect(img).toHaveAttribute('src', '/placeholder-album.jpg');
  });
  
  it('is accessible', () => {
    const { container } = render(
      <TestWrapper>
        <SongCard song={mockSong} onSelect={mockOnSelect} />
      </TestWrapper>
    );
    
    // Check for proper ARIA attributes
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-label', expect.stringContaining(mockSong.title));
    
    // Check keyboard navigation
    expect(button).toHaveAttribute('tabIndex', '0');
    
    // Custom accessibility matcher
    expect(container).toBeAccessible();
  });
});
```

### Hook Testing

```typescript
// src/hooks/useDebounce.test.ts
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useDebounce } from './useDebounce';

describe('useDebounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  
  afterEach(() => {
    vi.useRealTimers();
  });
  
  it('debounces value changes', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      {
        initialProps: { value: 'initial', delay: 500 }
      }
    );
    
    expect(result.current).toBe('initial');
    
    // Change value
    rerender({ value: 'updated', delay: 500 });
    
    // Value should not change immediately
    expect(result.current).toBe('initial');
    
    // Fast-forward time
    act(() => {
      vi.advanceTimersByTime(500);
    });
    
    // Value should now be updated
    expect(result.current).toBe('updated');
  });
  
  it('cancels previous timeout on rapid changes', () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      {
        initialProps: { value: 'first', delay: 500 }
      }
    );
    
    // Rapid changes
    rerender({ value: 'second', delay: 500 });
    rerender({ value: 'third', delay: 500 });
    
    // Fast-forward less than delay
    act(() => {
      vi.advanceTimersByTime(400);
    });
    
    expect(result.current).toBe('first'); // Still original value
    
    // Complete the delay
    act(() => {
      vi.advanceTimersByTime(100);
    });
    
    expect(result.current).toBe('third'); // Final value
  });
});
```

### Store Testing (Zustand)

```typescript
// src/stores/useSongsStore.test.ts
import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { useSongsStore } from './useSongsStore';
import { createMockSong } from '@/test/factories/songFactory';

describe('useSongsStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useSongsStore.getState().clearFilters();
    useSongsStore.getState().setSongs([]);
  });
  
  it('initializes with empty state', () => {
    const { result } = renderHook(() => useSongsStore());
    
    expect(result.current.songs).toEqual([]);
    expect(result.current.filters).toEqual({
      search: '',
      genre: '',
      artist: ''
    });
    expect(result.current.selectedSong).toBeNull();
  });
  
  it('updates filters correctly', () => {
    const { result } = renderHook(() => useSongsStore());
    
    act(() => {
      result.current.setFilters({ search: 'test', genre: 'rock' });
    });
    
    expect(result.current.filters.search).toBe('test');
    expect(result.current.filters.genre).toBe('rock');
    expect(result.current.filters.artist).toBe(''); // Unchanged
  });
  
  it('filters songs based on search term', () => {
    const songs = [
      createMockSong({ title: 'Rock Song', artist: 'Rock Band' }),
      createMockSong({ title: 'Jazz Song', artist: 'Jazz Band' }),
    ];
    
    const { result } = renderHook(() => useSongsStore());
    
    act(() => {
      result.current.setSongs(songs);
      result.current.setFilters({ search: 'rock' });
    });
    
    expect(result.current.filteredSongs).toHaveLength(1);
    expect(result.current.filteredSongs[0].title).toBe('Rock Song');
  });
  
  it('selects and deselects songs', () => {
    const song = createMockSong();
    const { result } = renderHook(() => useSongsStore());
    
    act(() => {
      result.current.selectSong(song);
    });
    
    expect(result.current.selectedSong).toEqual(song);
    
    act(() => {
      result.current.clearSelection();
    });
    
    expect(result.current.selectedSong).toBeNull();
  });
});
```

## 🔌 Integration Testing

### API Integration Testing

```typescript
// src/test/mocks/handlers.ts - MSW request handlers
import { http, HttpResponse } from 'msw';
import { createMockSong } from '../factories/songFactory';

export const handlers = [
  // Songs API
  http.get('/api/songs', () => {
    return HttpResponse.json({
      success: true,
      data: [
        createMockSong({ id: '1', title: 'Test Song 1' }),
        createMockSong({ id: '2', title: 'Test Song 2' }),
      ]
    });
  }),
  
  http.get('/api/songs/:id', ({ params }) => {
    const { id } = params;
    return HttpResponse.json({
      success: true,
      data: createMockSong({ id: id as string })
    });
  }),
  
  http.post('/api/songs', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      success: true,
      data: createMockSong(body as any)
    }, { status: 201 });
  }),
  
  // Upload API
  http.post('/api/upload', () => {
    return HttpResponse.json({
      success: true,
      data: { jobId: 'mock-job-123' }
    }, { status: 202 });
  }),
  
  // Error scenarios
  http.get('/api/songs/error', () => {
    return HttpResponse.json({
      success: false,
      error: 'Song not found'
    }, { status: 404 });
  }),
];

// src/test/mocks/server.ts
import { setupServer } from 'msw/node';
import { handlers } from './handlers';

export const server = setupServer(...handlers);
```

### Component Integration Testing

```typescript
// src/pages/LibraryPage.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect } from 'vitest';
import { LibraryPage } from './LibraryPage';
import { TestWrapper } from '@/test/utils/TestWrapper';
import { server } from '@/test/mocks/server';
import { http, HttpResponse } from 'msw';

describe('LibraryPage Integration', () => {
  it('loads and displays songs from API', async () => {
    render(
      <TestWrapper>
        <LibraryPage />
      </TestWrapper>
    );
    
    // Loading state
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
    
    // Wait for songs to load
    await waitFor(() => {
      expect(screen.getByText('Test Song 1')).toBeInTheDocument();
      expect(screen.getByText('Test Song 2')).toBeInTheDocument();
    });
    
    expect(screen.queryByText(/loading/i)).not.toBeInTheDocument();
  });
  
  it('filters songs based on search input', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <LibraryPage />
      </TestWrapper>
    );
    
    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText('Test Song 1')).toBeInTheDocument();
    });
    
    // Filter songs
    const searchInput = screen.getByPlaceholderText(/search songs/i);
    await user.type(searchInput, 'Test Song 1');
    
    await waitFor(() => {
      expect(screen.getByText('Test Song 1')).toBeInTheDocument();
      expect(screen.queryByText('Test Song 2')).not.toBeInTheDocument();
    });
  });
  
  it('handles API errors gracefully', async () => {
    // Override handler to return error
    server.use(
      http.get('/api/songs', () => {
        return HttpResponse.json({
          success: false,
          error: 'Server error'
        }, { status: 500 });
      })
    );
    
    render(
      <TestWrapper>
        <LibraryPage />
      </TestWrapper>
    );
    
    await waitFor(() => {
      expect(screen.getByText(/error loading songs/i)).toBeInTheDocument();
    });
  });
  
  it('opens song details dialog when song is clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <LibraryPage />
      </TestWrapper>
    );
    
    await waitFor(() => {
      expect(screen.getByText('Test Song 1')).toBeInTheDocument();
    });
    
    // Click on song
    const songCard = screen.getByRole('button', { name: /test song 1/i });
    await user.click(songCard);
    
    // Dialog should open
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Song Details')).toBeInTheDocument();
    });
  });
});
```

### Form Testing

```typescript
// src/components/forms/AddSongForm.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import { AddSongForm } from './AddSongForm';
import { TestWrapper } from '@/test/utils/TestWrapper';

describe('AddSongForm', () => {
  const mockOnSubmit = vi.fn();
  
  beforeEach(() => {
    mockOnSubmit.mockClear();
  });
  
  it('submits form with valid data', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <AddSongForm onSubmit={mockOnSubmit} />
      </TestWrapper>
    );
    
    // Fill out form
    await user.type(screen.getByLabelText(/title/i), 'Test Song');
    await user.type(screen.getByLabelText(/artist/i), 'Test Artist');
    await user.type(screen.getByLabelText(/album/i), 'Test Album');
    
    // Submit form
    await user.click(screen.getByRole('button', { name: /submit/i }));
    
    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith({
        title: 'Test Song',
        artist: 'Test Artist',
        album: 'Test Album',
      });
    });
  });
  
  it('shows validation errors for empty required fields', async () => {
    const user = userEvent.setup();
    
    render(
      <TestWrapper>
        <AddSongForm onSubmit={mockOnSubmit} />
      </TestWrapper>
    );
    
    // Try to submit empty form
    await user.click(screen.getByRole('button', { name: /submit/i }));
    
    await waitFor(() => {
      expect(screen.getByText(/title is required/i)).toBeInTheDocument();
      expect(screen.getByText(/artist is required/i)).toBeInTheDocument();
    });
    
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });
  
  it('handles file upload', async () => {
    const user = userEvent.setup();
    const file = new File(['audio content'], 'test.mp3', { type: 'audio/mpeg' });
    
    render(
      <TestWrapper>
        <AddSongForm onSubmit={mockOnSubmit} />
      </TestWrapper>
    );
    
    const fileInput = screen.getByLabelText(/upload file/i);
    await user.upload(fileInput, file);
    
    expect(fileInput.files[0]).toBe(file);
    expect(fileInput.files).toHaveLength(1);
  });
});
```

## 🌐 End-to-End Testing

### Playwright Configuration

```typescript
// playwright.config.ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  
  // Run tests in files in parallel
  fullyParallel: true,
  
  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,
  
  // Retry on CI only
  retries: process.env.CI ? 2 : 0,
  
  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,
  
  // Reporter to use
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }]
  ],
  
  use: {
    // Base URL to use in actions like `await page.goto('/')`
    baseURL: 'http://localhost:3000',
    
    // Collect trace when retrying the failed test
    trace: 'on-first-retry',
    
    // Screenshot on failure
    screenshot: 'only-on-failure',
    
    // Video recording
    video: 'retain-on-failure',
  },
  
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
  
  // Run your local dev server before starting the tests
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

### E2E Test Examples

```typescript
// e2e/library.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Song Library', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });
  
  test('displays song library and allows filtering', async ({ page }) => {
    // Wait for songs to load
    await expect(page.getByText('Test Song 1')).toBeVisible();
    
    // Test search functionality
    await page.getByPlaceholder('Search songs...').fill('Test Song 1');
    
    await expect(page.getByText('Test Song 1')).toBeVisible();
    await expect(page.getByText('Test Song 2')).not.toBeVisible();
    
    // Clear search
    await page.getByPlaceholder('Search songs...').clear();
    
    await expect(page.getByText('Test Song 2')).toBeVisible();
  });
  
  test('opens song details dialog', async ({ page }) => {
    await page.getByRole('button', { name: /test song 1/i }).click();
    
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('Song Details')).toBeVisible();
    
    // Close dialog
    await page.getByRole('button', { name: /close/i }).click();
    
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });
  
  test('mobile navigation works correctly', async ({ page, isMobile }) => {
    test.skip(!isMobile, 'This test is only for mobile');
    
    // Check that mobile navigation is visible
    await expect(page.getByRole('navigation')).toBeVisible();
    
    // Navigate to different sections
    await page.getByRole('button', { name: /add song/i }).click();
    await expect(page).toHaveURL('/add');
    
    await page.getByRole('button', { name: /library/i }).click();
    await expect(page).toHaveURL('/');
  });
});

// e2e/accessibility.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility', () => {
  test('should not have any automatically detectable accessibility issues', async ({ page }) => {
    await page.goto('/');
    
    const accessibilityScanResults = await new AxeBuilder({ page }).analyze();
    
    expect(accessibilityScanResults.violations).toEqual([]);
  });
  
  test('keyboard navigation works correctly', async ({ page }) => {
    await page.goto('/');
    
    // Tab through the interface
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: /search/i })).toBeFocused();
    
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button').first()).toBeFocused();
    
    // Test Enter key activation
    await page.keyboard.press('Enter');
    await expect(page.getByRole('dialog')).toBeVisible();
  });
  
  test('screen reader announcements work', async ({ page }) => {
    await page.goto('/');
    
    // Check for proper ARIA labels
    await expect(page.getByRole('main')).toHaveAttribute('aria-label', 'Song Library');
    await expect(page.getByRole('search')).toHaveAttribute('aria-label', 'Search songs');
  });
});
```

## 🧩 Test Utilities

### Test Factory Functions

```typescript
// src/test/factories/songFactory.ts
import { Song } from '@/types/song';

export function createMockSong(overrides: Partial<Song> = {}): Song {
  return {
    id: 'mock-song-id',
    title: 'Mock Song Title',
    artist: 'Mock Artist',
    album: 'Mock Album',
    duration: 180,
    coverUrl: '/mock-cover.jpg',
    hasVocals: true,
    hasInstrumental: true,
    genre: 'Rock',
    year: 2023,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    ...overrides,
  };
}

export function createMockSongList(count: number = 5): Song[] {
  return Array.from({ length: count }, (_, index) =>
    createMockSong({
      id: `mock-song-${index}`,
      title: `Mock Song ${index + 1}`,
    })
  );
}
```

### Test Wrapper Component

```typescript
// src/test/utils/TestWrapper.tsx
import { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider } from 'next-themes';

interface TestWrapperProps {
  children: ReactNode;
}

export function TestWrapper({ children }: TestWrapperProps) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
  
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ThemeProvider attribute="class" defaultTheme="dark">
          {children}
        </ThemeProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

### Custom Testing Matchers

```typescript
// src/test/matchers/accessibility.ts
import { expect } from 'vitest';
import { render } from '@testing-library/react';

declare module 'vitest' {
  interface Assertion<T = any> {
    toBeAccessible(): T;
    toHaveProperSemantics(): T;
  }
}

expect.extend({
  toBeAccessible(received) {
    const { container } = render(received);
    
    // Check for basic accessibility requirements
    const buttons = container.querySelectorAll('button');
    const links = container.querySelectorAll('a');
    const inputs = container.querySelectorAll('input');
    
    const violations: string[] = [];
    
    // Check buttons have accessible names
    buttons.forEach((button, index) => {
      if (!button.textContent && !button.getAttribute('aria-label')) {
        violations.push(`Button ${index} lacks accessible name`);
      }
    });
    
    // Check links have accessible names
    links.forEach((link, index) => {
      if (!link.textContent && !link.getAttribute('aria-label')) {
        violations.push(`Link ${index} lacks accessible name`);
      }
    });
    
    // Check inputs have labels
    inputs.forEach((input, index) => {
      const id = input.getAttribute('id');
      const label = id ? container.querySelector(`label[for="${id}"]`) : null;
      const ariaLabel = input.getAttribute('aria-label');
      
      if (!label && !ariaLabel) {
        violations.push(`Input ${index} lacks associated label`);
      }
    });
    
    if (violations.length > 0) {
      return {
        message: () => `Accessibility violations found:\n${violations.join('\n')}`,
        pass: false,
      };
    }
    
    return {
      message: () => 'Component is accessible',
      pass: true,
    };
  },
});
```

## 📊 Test Coverage and Reporting

### Coverage Configuration

```typescript
// vitest.config.ts - Coverage configuration
export default defineConfig({
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      
      // Coverage thresholds
      thresholds: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80,
        },
        // Per-file thresholds
        'src/components/**/*.{ts,tsx}': {
          branches: 85,
          functions: 85,
          lines: 85,
          statements: 85,
        },
        'src/hooks/**/*.{ts,tsx}': {
          branches: 90,
          functions: 90,
          lines: 90,
          statements: 90,
        },
      },
      
      // Exclude patterns
      exclude: [
        'node_modules/',
        'src/test/',
        'src/**/*.d.ts',
        'src/**/*.config.*',
        'src/**/*.stories.*',
        'dist/',
      ],
      
      // Include patterns
      include: ['src/**/*.{ts,tsx}'],
    },
  },
});
```

### Test Scripts

```json
{
  "scripts": {
    // Unit and integration tests
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage",
    "test:watch": "vitest --watch",
    
    // E2E tests
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui",
    "test:e2e:debug": "playwright test --debug",
    
    // Test utilities
    "test:install": "playwright install",
    "test:report": "playwright show-report",
    
    // Combined test run
    "test:all": "npm run test:run && npm run test:e2e",
    
    // CI/CD scripts
    "test:ci": "npm run test:coverage && npm run test:e2e"
  }
}
```

## 🎯 Testing Best Practices

### Test Organization

1. **Test Structure**: Follow AAA pattern (Arrange, Act, Assert)
2. **Test Naming**: Use descriptive test names that explain the scenario
3. **Test Isolation**: Each test should be independent and not rely on others
4. **Mock Strategy**: Mock external dependencies, keep business logic real

### Performance Testing

```typescript
// Performance testing for components
describe('Performance Tests', () => {
  it('renders large song list efficiently', async () => {
    const largeSongList = createMockSongList(1000);
    
    const startTime = performance.now();
    
    render(
      <TestWrapper>
        <SongLibrary songs={largeSongList} />
      </TestWrapper>
    );
    
    const renderTime = performance.now() - startTime;
    
    // Should render within reasonable time
    expect(renderTime).toBeLessThan(100); // 100ms
  });
});
```

### Accessibility Testing

```typescript
// Comprehensive accessibility testing
describe('Accessibility Tests', () => {
  it('meets WCAG 2.1 AA standards', async () => {
    const { container } = render(
      <TestWrapper>
        <LibraryPage />
      </TestWrapper>
    );
    
    // Check color contrast
    const buttons = container.querySelectorAll('button');
    buttons.forEach(button => {
      const styles = getComputedStyle(button);
      // Assert minimum contrast ratio
      expect(getContrastRatio(styles.color, styles.backgroundColor)).toBeGreaterThan(4.5);
    });
    
    // Check focus management
    const firstButton = buttons[0] as HTMLElement;
    firstButton.focus();
    expect(document.activeElement).toBe(firstButton);
  });
});
```

---

**Testing Benefits**: This comprehensive testing strategy ensures reliable functionality, excellent user experience, accessibility compliance, and maintainable code across the entire frontend application.
