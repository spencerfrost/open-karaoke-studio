# Frontend Architecture Overview - Open Karaoke

## Tech Stack & Foundation
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Routing**: React Router DOM
- **State Management**: 
  - Zustand for client state (stores)
  - React Context for app-wide state
  - TanStack React Query for server state
- **UI Framework**: Tailwind CSS with shadcn/ui components
- **Package Manager**: pnpm

## Application Architecture

### Entry Point & Root Structure
```
main.tsx → App.tsx → Router → Pages
     ↓
QueryClientProvider (TanStack React Query)
     ↓  
SettingsProvider → SongsProvider → AppLayout
```

### Routing Structure
- **/** - Library (main page)
- **/add** - Add Song page
- **/settings** - Settings page  
- **/stage** - Stage view (performance mode)
- **/player/:id** - Song Player
- **/controls** - Performance Controls

### State Management Layers

#### 1. Zustand Stores (Client State)
- `useSongsStore` - Song library state and filtering
- `useKaraokePlayerStore` - Player state management
- `useKaraokeQueueStore` - Queue management
- `useSettingsStore` - Application settings

#### 2. React Context (App-wide State)
- `SongsContext` - Legacy song state management (reducer pattern)
- `SettingsContext` - Application settings context

#### 3. TanStack React Query (Server State)
- API caching and synchronization
- Background refetching
- Optimistic updates

## Component Architecture

### Layout Components
- `AppLayout` - Main app wrapper with navigation
- `NavBar` - Bottom navigation with vintage styling

### Feature-Based Component Organization

#### Library Components (`/library/`)
- `LibraryContent` - Main library display
- `LibrarySearchInput` - Search functionality
- `ArtistAccordion` - Artist grouping display
- `ArtistSection` - Artist-based organization
- `SongResultsGrid` - Grid layout for songs
- `SearchableInfiniteArtists` - Infinite scroll for artists

#### Song Components (`/songs/`)
- `SongCard` - Basic song display card
- `HorizontalSongCard` - Horizontal layout variant
- `PrimarySongDetails` - Main song information
- `MetadataEditor` - Song metadata editing

##### Song Details Sub-components (`/songs/song-details/`)
- `SongDetailsDialog` - Modal for song details
- `ArtworkDisplay` - Album artwork display
- `MetadataQualityIndicator` - Data quality status
- `PrimaryActionsSection` - Main action buttons
- `SecondaryActionsPanel` - Additional actions
- `SongLyricsSection` - Lyrics display
- `SongPreviewPlayer` - Preview playback
- `TwoColumnContentLayout` - Layout wrapper

##### Metadata Edit Sub-components (`/metadata-edit/`)
- `ITunesResultCard` - iTunes search results
- `MetadataComparisonView` - Compare metadata versions
- `ReviewStep`, `SearchStep`, `SelectStep` - Stepper workflow
- `StepIndicator` - Progress indicator

#### Player Components (`/player/`)
- `AudioVisualizer` - Audio visualization
- `ProgressBar` - Playback progress
- `UnifiedLyricsDisplay` - Lyrics during playback

#### Queue Components (`/queue/`)
- `KaraokeQueueList` - Queue management
- `KaraokeQueueItem` - Individual queue items
- `QRCodeDisplay` - QR code for mobile access

#### Upload Components (`/upload/`)
- `FileUpload` - File upload interface
- `SongAdditionStepper` - Multi-step upload process
- `JobsQueue` - Upload job status
- `MetadataDialog` - Metadata input during upload
- `YouTubeSearch` - YouTube integration
- `VerificationDialog` - Upload verification

##### Upload Steps (`/upload/steps/`)
- `ConfirmDetailsStep` - Final confirmation
- `LyricsSelectionStep` - Lyrics selection
- `MetadataSelectionStep` - Metadata selection

#### Form Components (`/forms/`)
- `SearchForm` - Generic search functionality
- `LyricsResults` - Lyrics search results
- `MetadataResults` - Metadata search results

#### Lyrics Components (`/lyrics/`)
- `LyricsFetchDialog` - Lyrics fetching interface

#### UI Components (`/ui/`)
- **shadcn/ui components**: accordion, alert-dialog, badge, button, card, dialog, form, input, select, etc.
- `LoadingSpinner` - Custom loading component
- `Stepper` - Multi-step process component

### Custom Hooks (`/hooks/`)

#### Data Management Hooks
- `useApi` - Generic API interaction
- `useSongs` - Song CRUD operations
- `useMetadata` - Metadata management
- `useLyrics` - Lyrics operations
- `useYoutube` - YouTube integration
- `useItunesSearch` - iTunes metadata search

#### UI/UX Hooks  
- `useDebouncedValue` - Input debouncing
- `useInfiniteScroll` - Infinite scrolling
- `useInfiniteFuzzySearch` - Search with infinite scroll
- `useInfiniteLibraryBrowsing` - Library browsing
- `useLibraryBrowsing` - Basic library browsing

#### Real-time Hooks
- `useJobsWebSocket` - WebSocket for job updates
- `useKaraokeQueue` - Queue management

### Services (`/services/`)
- `api.ts` - Core API client with error handling
- `jobsWebSocketService.ts` - WebSocket service for jobs
- `uploadService.ts` - File upload handling

### Types (`/types/`)
- `Song.ts` - Song data structure
- `Player.ts` - Player state types
- `Settings.ts` - Application settings
- `KaraokeQueue.ts` - Queue data structures

### Utilities (`/utils/`)
- `formatters.ts` - Data formatting utilities
- `validators.ts` - Input validation

## Key Architectural Patterns

### 1. Feature-Based Organization
Components are organized by feature domain (library, songs, player, upload) rather than technical concerns.

### 2. Compound Component Pattern
Complex features like song details use compound components with clear parent-child relationships.

### 3. Hook-Based Logic Separation
Business logic is extracted into custom hooks, keeping components focused on rendering.

### 4. Layered State Management
- Local state for component-specific needs
- Zustand stores for client-side app state
- React Query for server state
- Context for app-wide coordination

### 5. Progressive Enhancement
Components work independently and can be composed together for enhanced functionality.

## Data Flow Patterns

### Song Library Flow
```
LibraryPage → useInfiniteFuzzySearch → useSongs 
     ↓              ↓                     ↓
LibraryContent → SongCard → SongDetailsDialog
```

### Upload Flow  
```
AddSongPage → SongAdditionStepper → Upload Steps
     ↓              ↓                    ↓
FileUpload → uploadService → JobsQueue → WebSocket Updates
```

### Player Flow
```
SongPlayer → useKaraokePlayerStore → AudioVisualizer + UnifiedLyricsDisplay
     ↓              ↓                         ↓
Player Controls → ProgressBar → Real-time Updates
```

## WebSocket Integration
- `jobsWebSocketService` handles real-time job updates
- `useJobsWebSocket` hook provides reactive job status
- Connected to upload progress, processing status, and queue updates

## Routing & Navigation
- React Router DOM for client-side routing
- Bottom navigation (`NavBar`) with vintage styling
- Deep linking support for song player and details
- Fallback route redirects to library

This architecture supports a comprehensive karaoke application with dual-display capabilities, real-time job processing, and a rich metadata management system.