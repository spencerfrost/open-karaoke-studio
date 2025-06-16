# API Integration Patterns

## Overview

The API integration layer provides a comprehensive set of patterns for communicating with the backend services. It features TypeScript-first design, robust error handling, optimistic updates, and seamless integration with React Query for state management and caching.

## Current Implementation Status

**Primary Files**:
- `frontend/src/services/api.ts` - Main API client and configuration
- `frontend/src/hooks/api/` - API-specific React Query hooks
- `frontend/src/types/api/` - TypeScript interfaces for API contracts
- `frontend/src/utils/apiError.ts` - Error handling utilities

**Status**: ✅ Complete with comprehensive error handling
**Integration**: Fully integrated with backend Phase 2 enhancements

## Core Responsibilities

### Backend Communication
- **RESTful API Calls**: Structured communication with Flask backend
- **Request/Response Handling**: Comprehensive data serialization and validation
- **Authentication**: JWT token management and automatic refresh
- **File Upload**: Multi-part form data handling for audio files

### State Management Integration
- **React Query Integration**: Optimized caching and background updates
- **Optimistic Updates**: Immediate UI updates with rollback capability
- **Real-time Sync**: WebSocket integration for live data updates
- **Offline Support**: Graceful degradation when backend unavailable

### Type Safety and Validation
- **TypeScript Interfaces**: Comprehensive type definitions for all API contracts
- **Runtime Validation**: Zod schema validation for API responses
- **Error Type System**: Structured error handling with specific error types
- **Data Transformation**: Automatic transformation between API and UI formats

## Implementation Details

### Core API Client

```typescript
// Main API client configuration
export class ApiClient {
  private readonly baseUrl: string;
  private readonly defaultHeaders: Record<string, string>;

  constructor(config: ApiConfig) {
    this.baseUrl = config.baseUrl;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
      ...config.defaultHeaders,
    };
  }

  // Generic request method with error handling
  private async request<T>(
    endpoint: string,
    options: RequestOptions = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;
    const config: RequestInit = {
      method: options.method || 'GET',
      headers: {
        ...this.defaultHeaders,
        ...options.headers,
        ...this.getAuthHeaders(),
      },
      body: options.body,
      signal: options.signal,
    };

    try {
      const response = await fetch(url, config);
      return await this.handleResponse<T>(response);
    } catch (error) {
      throw new ApiError('Network error', { cause: error });
    }
  }

  // Structured response handling
  private async handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
    if (!response.ok) {
      const error = await this.parseErrorResponse(response);
      throw new ApiError(error.message, {
        status: response.status,
        code: error.code,
        details: error.details,
      });
    }

    const data = await response.json();

    // Runtime validation with Zod
    return this.validateResponse<T>(data);
  }

  // Authentication header management
  private getAuthHeaders(): Record<string, string> {
    const token = authStore.getState().token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
}
```

### Service Layer Organization

```typescript
// Songs API service
export const songsApi = {
  // Get all songs with pagination and filtering
  getMany: async (params: GetSongsParams): Promise<PaginatedResponse<Song>> => {
    const queryParams = new URLSearchParams({
      offset: params.offset?.toString() || '0',
      limit: params.limit?.toString() || '50',
      ...(params.search && { search: params.search }),
      ...(params.artist && { artist: params.artist }),
      ...(params.genre && { genre: params.genre }),
    });

    return apiClient.request<PaginatedResponse<Song>>(
      `/api/songs?${queryParams}`
    );
  },

  // Get single song by ID
  getById: async (id: string): Promise<Song> => {
    return apiClient.request<Song>(`/api/songs/${id}`);
  },

  // Create new song with file upload
  create: async (songData: CreateSongRequest): Promise<Song> => {
    const formData = new FormData();

    // Handle file upload
    if (songData.audioFile) {
      formData.append('audio_file', songData.audioFile);
    }

    // Add metadata
    formData.append('metadata', JSON.stringify({
      title: songData.title,
      artist: songData.artist,
      album: songData.album,
      // Enhanced metadata from iTunes/YouTube
      itunesTrackId: songData.itunesTrackId,
      youtubeThumbnailUrls: songData.youtubeThumbnailUrls,
    }));

    return apiClient.request<Song>('/api/songs', {
      method: 'POST',
      body: formData,
      headers: {}, // Let browser set Content-Type for FormData
    });
  },

  // Update song metadata
  update: async (id: string, updates: UpdateSongRequest): Promise<Song> => {
    return apiClient.request<Song>(`/api/songs/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  },

  // Delete song
  delete: async (id: string): Promise<void> => {
    return apiClient.request<void>(`/api/songs/${id}`, {
      method: 'DELETE',
    });
  },
};
```

### React Query Hook Patterns

```typescript
// Query hooks for data fetching
export const useSongs = (params: GetSongsParams = {}) => {
  return useQuery({
    queryKey: ['songs', params],
    queryFn: () => songsApi.getMany(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
    cacheTime: 30 * 60 * 1000, // 30 minutes
    keepPreviousData: true, // Smooth pagination
  });
};

export const useSong = (id: string) => {
  return useQuery({
    queryKey: ['songs', id],
    queryFn: () => songsApi.getById(id),
    enabled: !!id,
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
};

// Mutation hooks for data modification
export const useCreateSong = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: songsApi.create,
    onSuccess: (newSong) => {
      // Optimistically update the cache
      queryClient.setQueryData<PaginatedResponse<Song>>(
        ['songs'],
        (oldData) => {
          if (!oldData) return oldData;

          return {
            ...oldData,
            songs: [newSong, ...oldData.songs],
            total: oldData.total + 1,
          };
        }
      );

      // Invalidate relevant queries
      queryClient.invalidateQueries(['songs']);
    },
    onError: (error) => {
      toast.error(`Failed to create song: ${error.message}`);
    },
  });
};

export const useUpdateSong = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, updates }: { id: string; updates: UpdateSongRequest }) =>
      songsApi.update(id, updates),
    onMutate: async ({ id, updates }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries(['songs', id]);

      // Snapshot previous value
      const previousSong = queryClient.getQueryData<Song>(['songs', id]);

      // Optimistically update
      if (previousSong) {
        queryClient.setQueryData(['songs', id], {
          ...previousSong,
          ...updates,
        });
      }

      return { previousSong };
    },
    onError: (error, variables, context) => {
      // Rollback on error
      if (context?.previousSong) {
        queryClient.setQueryData(['songs', variables.id], context.previousSong);
      }
      toast.error(`Failed to update song: ${error.message}`);
    },
    onSettled: (data, error, variables) => {
      // Always refetch after mutation
      queryClient.invalidateQueries(['songs', variables.id]);
    },
  });
};
```

### Error Handling System

```typescript
// Structured error types
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly details: {
      status?: number;
      code?: string;
      details?: Record<string, any>;
      cause?: unknown;
    } = {}
  ) {
    super(message);
    this.name = 'ApiError';
  }

  get isNetworkError(): boolean {
    return this.details.status === undefined;
  }

  get isAuthError(): boolean {
    return this.details.status === 401 || this.details.status === 403;
  }

  get isValidationError(): boolean {
    return this.details.status === 422;
  }

  get isServerError(): boolean {
    return (this.details.status ?? 0) >= 500;
  }
}

// Global error handling
export const handleApiError = (error: ApiError, context?: string) => {
  console.error(`API Error${context ? ` in ${context}` : ''}:`, error);

  if (error.isAuthError) {
    // Redirect to login
    authStore.getState().logout();
    router.push('/login');
    return;
  }

  if (error.isNetworkError) {
    toast.error('Network error. Please check your connection.');
    return;
  }

  if (error.isValidationError) {
    // Handle validation errors specifically
    const validationErrors = error.details.details as ValidationError[];
    validationErrors?.forEach((err) => {
      toast.error(`${err.field}: ${err.message}`);
    });
    return;
  }

  // Generic error message
  toast.error(error.message || 'An unexpected error occurred');
};
```

## Integration Points

### Component Integration
- **Form Submissions**: Seamless integration with React Hook Form
- **Real-time Updates**: WebSocket integration for live data sync
- **File Uploads**: Progress tracking and error handling for large files
- **Optimistic UI**: Immediate feedback with rollback capability

### State Management Integration
- **Zustand Stores**: Global state synchronization with API data
- **Cache Synchronization**: Bidirectional sync between React Query and Zustand
- **Offline Support**: Local state persistence during network issues
- **Background Sync**: Automatic sync when connection restored

### Authentication Integration
- **Token Management**: Automatic token refresh and storage
- **Request Interception**: Automatic auth header injection
- **Logout Handling**: Clean state reset on authentication failure
- **Protected Routes**: Route-level authentication enforcement

## Design Patterns

### Repository Pattern
Abstracted API access through service layer:

```typescript
// Service abstraction pattern
interface SongRepository {
  getMany(params: GetSongsParams): Promise<PaginatedResponse<Song>>;
  getById(id: string): Promise<Song>;
  create(data: CreateSongRequest): Promise<Song>;
  update(id: string, updates: UpdateSongRequest): Promise<Song>;
  delete(id: string): Promise<void>;
}

// Implementation can be swapped for testing
export const songRepository: SongRepository = songsApi;
```

### Request/Response Pipeline
Structured request and response processing:

```typescript
// Request interceptors
const requestInterceptors = [
  addAuthHeaders,
  addRequestId,
  logRequest,
  validateRequest,
];

// Response interceptors
const responseInterceptors = [
  logResponse,
  validateResponse,
  transformResponse,
  handleErrors,
];
```

### Optimistic Update Pattern
Immediate UI updates with error rollback:

```typescript
// Optimistic update pattern
const useOptimisticUpdate = <T>(
  queryKey: QueryKey,
  mutationFn: MutationFunction<T>,
  updateFn: (oldData: T, variables: any) => T
) => {
  return useMutation({
    mutationFn,
    onMutate: async (variables) => {
      await queryClient.cancelQueries(queryKey);
      const previousData = queryClient.getQueryData<T>(queryKey);

      if (previousData) {
        queryClient.setQueryData(queryKey, updateFn(previousData, variables));
      }

      return { previousData };
    },
    onError: (error, variables, context) => {
      if (context?.previousData) {
        queryClient.setQueryData(queryKey, context.previousData);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries(queryKey);
    },
  });
};
```

## Performance Considerations

### Request Optimization
- **Request Deduplication**: Automatic deduplication of identical requests
- **Request Batching**: Combine multiple requests when possible
- **Compression**: Gzip compression for large responses
- **Connection Pooling**: Efficient HTTP connection reuse

### Caching Strategy
- **Smart Caching**: Different cache times based on data volatility
- **Background Updates**: Stale-while-revalidate pattern
- **Cache Invalidation**: Precise invalidation based on data relationships
- **Memory Management**: Automatic cleanup of unused cache entries

### Network Efficiency
- **Pagination**: Efficient data loading with cursor-based pagination
- **Prefetching**: Predictive data loading based on user behavior
- **Offline Support**: Local caching for offline functionality
- **Progressive Loading**: Partial data loading for improved perceived performance

## Testing Patterns

### API Mock Strategy
- **MSW Integration**: Mock Service Worker for realistic API mocking
- **Response Variations**: Test different response scenarios
- **Error Simulation**: Comprehensive error condition testing
- **Performance Testing**: Simulated network conditions

### Integration Testing
- **End-to-End Flows**: Complete user workflow testing
- **Error Recovery**: Test error handling and recovery mechanisms
- **State Synchronization**: Verify state consistency across components
- **Authentication Flows**: Complete auth lifecycle testing

## Future Enhancements

### Advanced Features
- **GraphQL Migration**: Potential migration to GraphQL for complex queries
- **Real-time Subscriptions**: WebSocket-based real-time updates
- **Edge Caching**: CDN integration for static content
- **Request Analytics**: Performance monitoring and optimization

### Developer Experience
- **Auto-generated Types**: Automatic TypeScript generation from OpenAPI
- **API Documentation**: Interactive API documentation with examples
- **Development Tools**: Enhanced debugging and monitoring tools
- **Testing Utilities**: Simplified testing patterns and utilities

---

**Integration Benefits**: This API integration architecture provides type-safe, performant, and reliable communication with the backend while maintaining excellent developer experience and comprehensive error handling throughout the application.
