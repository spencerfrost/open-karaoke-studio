# Fuzzy Search with Dual Display Design

## Overview

Transform the current artist-only library browsing into a comprehensive fuzzy search system with dual display - showing song results prominently at the top and artist results below. This addresses the core karaoke use case where users typically search for specific songs rather than browsing by artist.

## Current State Analysis

### Existing Components

- **SongCard.tsx**: Grid-based song card with artwork, currently used in some contexts
- **HorizontalSongCard.tsx**: Compact horizontal layout used in artist accordions
- **ArtistAccordion.tsx/ArtistSection.tsx**: Current artist-based browsing with expandable sections
- **useInfiniteLibraryBrowsing.ts**: Infinite scrolling for artists and songs within artists

### Current Search Behavior

- Search only filters artists by name
- Songs are hidden within collapsed artist accordions
- No direct song search capability
- No fuzzy matching

## Proposed Solution: Dual Display Architecture

### Search Logic

**Single search input** with fuzzy matching against both:

1. **Artist names** - Keep artists in traditional accordion layout
2. **Song titles** - Display in prominent song grid above artists

### Display Layout

```
┌─────────────────────────────────────────┐
│ [Search Input Field]                    │
└─────────────────────────────────────────┘

┌─ Song Results (when search active) ────┐
│ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐        │
│ │ ♪   │ │ ♪   │ │ ♪   │ │ ♪   │        │
│ │Card │ │Card │ │Card │ │Card │        │
│ └─────┘ └─────┘ └─────┘ └─────┘        │
│ ┌─────┐ ┌─────┐ ...                    │
│ │ ♪   │ │ ♪   │                        │
│ │Card │ │Card │                        │
│ └─────┘ └─────┘                        │
└─────────────────────────────────────────┘

┌─ Artist Results ─────────────────────────┐
│ ▶ Artist Name 1 (X songs)               │
│ ▶ Artist Name 2 (Y songs)               │
│ ▼ Artist Name 3 (Z songs) - expanded    │
│   └─ [horizontal song cards...]         │
└─────────────────────────────────────────┘
```

## User Experience Scenarios

### Scenario 1: Song Search ("what")

**Input**: User types "what"
**Results**:

- **Song Section**: Shows "What I Got - Sublime", "What's Up - 4 Non Blondes", etc. in grid cards
- **Artist Section**: Shows "What So Not" artist (collapsed)

### Scenario 2: Artist Search ("sublime")

**Input**: User types "sublime"  
**Results**:

- **Song Section**: Empty or minimal (only if song titles contain "sublime")
- **Artist Section**: Shows "Sublime" artist prominently

### Scenario 3: Empty Search

**Input**: Empty search field
**Results**:

- **Song Section**: Hidden/empty
- **Artist Section**: Default alphabetical artist list

## Technical Implementation Plan

### Phase 1: Backend API Changes

#### New Search Endpoint

```
POST /api/songs/search
{
  "query": "search term",
  "songLimit": 20,
  "songOffset": 0,
  "artistLimit": 200,
  "artistOffset": 0
}

Response: {
  "songs": [Song[]],
  "artists": [Artist[]],
  "pagination": {
    "songs": PaginationInfo,
    "artists": PaginationInfo
  }
}
```

#### Fuzzy Search Logic

- SQL `LIKE` queries with wildcards: `%search%`
- Search both `songs.title` and `artists.name`
- Order by relevance (exact matches first, then partial matches)

### Phase 2: Frontend Hook Updates

#### New Hook: `useInfiniteFuzzySearch`

```typescript
interface FuzzySearchResult {
  songs: Song[];
  artists: Artist[];
  songsPagination: {
    hasNextPage: boolean;
    isFetchingNextPage: boolean;
    fetchNextPage: () => void;
  };
  artistsPagination: {
    hasNextPage: boolean;
    isFetchingNextPage: boolean;
    fetchNextPage: () => void;
  };
  isLoading: boolean;
  error: Error | null;
}

export const useInfiniteFuzzySearch = (
  searchTerm: string,
  songPageSize: number = 20,
  artistPageSize: number = 200
): FuzzySearchResult
```

### Phase 3: UI Components

#### Complete Component Structure

```
Library.tsx (existing page)
├── LibrarySearchInput.tsx (new)
└── LibraryContent.tsx (new layout component)
    ├── SongResultsSection.tsx (new)
    │   └── SongResultsGrid.tsx (new)
    │       └── SongCard.tsx (existing - reused)
    └── ArtistResultsSection.tsx (new)
        └── ArtistAccordion.tsx (existing - reused)
```

#### Component Details

**1. Library.tsx (Top-level page - existing)**

- Manages search state and debouncing
- Orchestrates the `useInfiniteFuzzySearch` hook
- Passes down data and handlers to child components

**2. LibrarySearchInput.tsx (new)**

```typescript
interface LibrarySearchInputProps {
  searchTerm: string;
  onSearchChange: (term: string) => void;
  isLoading: boolean;
}
```

- Enhanced search input with debouncing
- Loading spinner and clear button
- Search suggestions (future enhancement)

**3. LibraryContent.tsx (new layout component)**

```typescript
interface LibraryContentProps {
  searchResults: FuzzySearchResult;
  onSongSelect: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
  searchTerm: string;
}
```

- Layout container that manages the dual display
- Conditionally shows/hides sections based on search state
- Handles responsive layout switching

**4. SongResultsSection.tsx (new)**

```typescript
interface SongResultsSectionProps {
  songs: Song[];
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  onSongSelect: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
  searchTerm: string;
}
```

- Section header ("Songs" with count)
- Manages infinite scrolling for songs
- Shows/hides based on search results

**5. SongResultsGrid.tsx (new)**

```typescript
interface SongResultsGridProps {
  songs: Song[];
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  onSongSelect: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
}
```

- Responsive grid layout: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`
- Infinite scroll logic with intersection observer
- Loading states and pagination

**6. ArtistResultsSection.tsx (new)**

```typescript
interface ArtistResultsSectionProps {
  artists: Artist[];
  hasNextPage: boolean;
  isFetchingNextPage: boolean;
  fetchNextPage: () => void;
  onSongSelect: (song: Song) => void;
  onAddToQueue: (song: Song) => void;
  searchTerm: string;
}
```

- Section header ("Artists" with count)
- Manages infinite scrolling for artists
- Shows "Browse All Artists" when no search term

#### Component Reuse Strategy

- **SongCard.tsx**: Existing component reused in grid layout
- **ArtistAccordion.tsx**: Existing component reused as-is
- **HorizontalSongCard.tsx**: Existing component reused within artist accordions

### Phase 4: Search Input Enhancement

#### Features

- Debounced input (300ms delay)
- Loading spinner during search
- Clear search button
- Search suggestions/history (future enhancement)

#### Search State Management

```typescript
const [searchTerm, setSearchTerm] = useState("");
const [debouncedSearch, setDebouncedSearch] = useState("");

// Debounce search term
useEffect(() => {
  const timer = setTimeout(() => {
    setDebouncedSearch(searchTerm);
  }, 300);

  return () => clearTimeout(timer);
}, [searchTerm]);
```

## Implementation Benefits

### User Experience

- **Faster song discovery**: Songs prominently displayed
- **Maintains familiar browsing**: Artist accordion still available
- **Single search paradigm**: No need for separate search modes
- **Visual consistency**: Reuses existing, proven components

### Technical Advantages

- **Component reuse**: Leverages existing `SongCard.tsx`
- **Scalable architecture**: Infinite scrolling for both sections
- **Progressive enhancement**: Doesn't break existing functionality
- **API efficiency**: Single endpoint for comprehensive search

## Migration Strategy

### Step 1: Backend Implementation

- Create new search endpoint
- Implement fuzzy search logic
- Add pagination support for both result types

### Step 2: Frontend Hook Development

- Build `useInfiniteFuzzySearch` hook
- Test with existing components
- Ensure proper error handling and loading states

### Step 3: UI Integration

- Create `DualDisplayLibrary` component
- Integrate with existing Library page
- Add proper responsive design

### Step 4: Testing & Refinement

- Test search performance with large libraries
- Refine relevance scoring
- Optimize mobile experience

## Future Enhancements

### Search Improvements

- **Fuzzy matching algorithms**: Implement Levenshtein distance for better typo tolerance
- **Search analytics**: Track popular searches to improve algorithms
- **Search filters**: Add genre, year, source filters
- **Voice search**: Integrate speech-to-text for hands-free searching

### UI Enhancements

- **Search highlighting**: Highlight matching terms in results
- **Recent searches**: Show search history dropdown
- **Keyboard navigation**: Arrow keys to navigate results

## Success Metrics

### User Engagement

- **Search usage**: % of library interactions that start with search
- **Song discovery**: Songs played from search vs. browse
- **Search completion**: % of searches that result in song selection

### Performance

- **Search latency**: < 200ms response time
- **Relevance**: User clicks on top 3 results > 80% of time
- **Mobile usability**: Touch target sizes and scroll performance

## Notes & Considerations

### Design Decisions

- **Grid vs. List**: Grid chosen for song results to maximize visual appeal with artwork
- **Component reuse**: Prioritize existing components to maintain consistency
- **Search behavior**: Fuzzy matching balances discovery with performance

### Technical Constraints

- **Database performance**: May need indexing for title/artist columns
- **Mobile performance**: Grid layout needs optimization for smaller screens
- **Cache strategy**: Consider caching popular searches

### Open Questions

- **Search result limits**: How many songs/artists to show initially?
- **Empty states**: What to show when no results found?
- **Search analytics**: What metrics to track for improving search?

---

**Next Steps**: Review this design document, discuss any modifications, then proceed with backend API implementation followed by frontend hook development.
