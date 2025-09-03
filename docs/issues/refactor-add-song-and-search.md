# Refactor: Add Song and Search Experience

## 🎯 Overview

This document outlines a comprehensive refactor of the YouTube song addition feature to create a unified, streamlined experience that prioritizes YouTube Music while maintaining flexibility for YouTube video search.

## 🚨 Current Problems

### Architecture Issues
- **Dual Search Systems**: Separate `youtube/` and `YoutubeMusicSearch/` implementations with inconsistent patterns
- **God Components**: `YoutubeVideoSearch.tsx` (~300+ lines) and `SongAdditionStepper.tsx` (~270+ lines) handle too many responsibilities
- **Poor State Management**: Multiple `useState` calls for related state across components
- **Mixed Responsibilities**: Components handle UI, business logic, API calls, and state management

### User Experience Issues
- **Side-by-side search**: Confusing interface with two separate search experiences
- **Unnecessary steps**: Metadata confirmation step when YouTube Music provides reliable data
- **No search refinement**: Users can't improve search results for lyrics/metadata without starting over
- **Inconsistent flows**: Different interaction patterns between search types

## 🎯 Goals

### Primary Objectives
1. **Unified Search Interface**: Single tabbed interface prioritizing YouTube Music
2. **Streamlined Workflows**: Eliminate unnecessary confirmation steps
3. **Search Refinement**: Allow users to improve results without restarting
4. **Clean Architecture**: Separated concerns, testable components, maintainable code

### User Experience Goals
1. **YouTube Music Priority**: Default to highest quality audio source
2. **Flexible Search**: Easy switching between sources with consistent patterns
3. **Progressive Enhancement**: Users can refine searches for better results
4. **Simplified Confirmation**: Only confirm what actually needs confirmation

## 🔄 New User Flows

### YouTube Music Flow (Simplified)
```
1. Search with single query input on page
2. View YouTube Music results displayed on page (trusted metadata)
3. Select result → creates song with YouTube Music metadata → opens SongAdditionStepper dialog
4. Lyrics confirmation (with search refinement in dialog)
5. Background iTunes metadata search with trusted metadata. Autoselect first result.
6. Complete
```

### YouTube Flow (Standard)
```
1. Search with single query input on page
2. View YouTube results displayed on page (untrusted metadata)
3. Select result → creates song with search query as title → opens SongAdditionStepper dialog
4. Lyrics confirmation (with search refinement in dialog)
5. iTunes Metadata confirmation (with search refinement in dialog)
6. Complete
```

## 🏗️ New Architecture

### Directory Structure
```
frontend/src/components/add/
├── search/
│   ├── SongSearchContainer.tsx               # Main search container (replaces AddSong.tsx content)
│   ├── SearchInput.tsx                     # Single search field
│   ├── SearchTabs.tsx                      # Source switching tabs
│   ├── SearchResults.tsx                   # Results container
│   ├── YoutubeMusicResults.tsx             # YTM-specific results display
│   ├── YouTubeResults.tsx                  # YouTube-specific results display
│   ├── YoutubeMusicResultCard.tsx          # Individual YTM result card
│   └── YouTubeResultCard.tsx               # Individual YouTube result card
├── dialog/
│   ├── SongAdditionStepper.tsx             # Existing dialog (enhanced with refinement)
│   └── steps/
│       ├── LyricsSelectionStep.tsx         # Enhanced with search refinement
│       ├── MetadataSelectionStep.tsx       # Enhanced with search refinement
│       └── SearchRefinementInput.tsx       # Persistent search input component
└── shared/
    ├── ResultCard.tsx                      # Base result card component
    ├── LoadingStates.tsx                   # Loading/error states
    └── EmptyStates.tsx                     # Empty result states
```

### Hook Structure
```
frontend/src/hooks/
├── useYoutubeMusicSearch.ts                # YTM search logic (existing, enhanced)
├── useYoutubeVideoSearch.ts                     # YouTube search logic (existing, enhanced)
├── useSearchRefinement.ts                  # Search refinement logic for dialog steps
├── useLyricsSearch.ts                      # Lyrics search with refinement
├── useMetadataSearch.ts                    # Metadata search with refinement
└── useSongCreation.ts                      # Song creation workflow (existing)
```
```

### Page Integration
```
pages/AddSong.tsx
├── JobsQueue
└── SongSearchContainer (replaces current dual search components)
    ├── SearchInput + SearchTabs
    └── Tabbed Results Display (YouTube Music / YouTube)
        └── Individual result cards with "Add to Library" buttons
            └── Clicking button → creates song → opens existing SongAdditionStepper dialog
```

## 🔧 Implementation Details

### 1. Search Interface

#### Main Search Component
```typescript
// components/add/search/SongSearchContainer.tsx
export const SongSearchContainer = () => {
  const [query, setQuery] = useState('');
  const [activeSource, setActiveSource] = useState<'youtube-music' | 'youtube'>('youtube-music');
  
  // Use existing hooks, only search when tab is active
  const youtubeMusicSearch = useYoutubeMusicSearch(
    query, 
    activeSource === 'youtube-music' && !!query
  );
  
  const youtubeSearch = useYoutubeVideoSearch(
    query,
    activeSource === 'youtube' && !!query
  );

  const handleSearch = (searchQuery: string) => {
    setQuery(searchQuery);
    // Search will automatically trigger based on activeSource
  };

  const handleResultSelect = (result: SearchResult, source: SearchSource) => {
    // Create song based on source type
    if (source === 'youtube-music') {
      createSongWithMetadata(result); // Use YouTube Music metadata
    } else {
      createSongWithQuery(query, result); // Use search query as title
    }
    // Opens existing SongAdditionStepper dialog
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Add Song to Library</CardTitle>
        <SearchInput 
          query={query}
          onSearch={handleSearch}
          placeholder="Search for any song..."
        />
        <SearchTabs 
          activeSource={activeSource}
          onSourceChange={setActiveSource}
          counts={{
            'youtube-music': youtubeMusicSearch.data?.length || 0,
            'youtube': youtubeSearch.data?.length || 0
          }}
        />
      </CardHeader>
      
      <CardContent>
        {activeSource === 'youtube-music' && (
          <YoutubeMusicResults 
            results={youtubeMusicSearch.data}
            isLoading={youtubeMusicSearch.isLoading}
            onSelect={(result) => handleResultSelect(result, 'youtube-music')}
          />
        )}
        
        {activeSource === 'youtube' && (
          <YouTubeResults 
            results={youtubeSearch.data}
            isLoading={youtubeSearch.isLoading}
            onSelect={(result) => handleResultSelect(result, 'youtube')}
          />
        )}
      </CardContent>
    </Card>
  );
};
```

#### Enhanced Existing Dialog
```typescript
// components/add/dialog/SongAdditionStepper.tsx (enhanced existing component)
export const SongAdditionStepper = ({
  isOpen,
  selectedResult,
  source, // 'youtube-music' | 'youtube'
  createdSong,
  onClose,
  onComplete
}) => {
  const [currentStep, setCurrentStep] = useState<'lyrics' | 'metadata'>('lyrics');
  const [searchQuery, setSearchQuery] = useState(
    source === 'youtube-music' 
      ? `${selectedResult.artist} ${selectedResult.title}` 
      : originalSearchQuery
  );

  const steps = source === 'youtube-music' ? ['lyrics'] : ['lyrics', 'metadata'];

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle>Confirm Song Details</DialogTitle>
          <DialogDescription>
            Adding: {selectedResult.title}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {currentStep === 'lyrics' && (
            <LyricsSelectionStep
              searchQuery={searchQuery}
              onQueryChange={setSearchQuery}
              onNext={() => source === 'youtube-music' ? onComplete() : setCurrentStep('metadata')}
              onSkip={() => source === 'youtube-music' ? onComplete() : setCurrentStep('metadata')}
            />
          )}

          {currentStep === 'metadata' && (
            <MetadataSelectionStep
              searchQuery={searchQuery}
              onQueryChange={setSearchQuery}
              onComplete={onComplete}
              onSkip={onComplete}
            />
          )}
        </div>

        <DialogFooter className="border-t pt-4">
          <SearchRefinementInput
            query={searchQuery}
            onQueryChange={setSearchQuery}
            placeholder="Refine search for better results..."
          />
          
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button onClick={handleNext}>
              {currentStep === 'lyrics' && source === 'youtube' ? 'Continue' : 'Complete'}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
```

### 2. Enhanced Existing Dialog Steps
#### Enhanced Lyrics Step with Search Refinement
```typescript
// components/add/dialog/steps/LyricsSelectionStep.tsx (enhanced existing)
export const LyricsSelectionStep = ({
  searchQuery,
  onQueryChange,
  onNext,
  onSkip
}) => {
  const { data: lyricsOptions, isLoading, refetch } = useLyricsSearch(searchQuery);

  // Refetch when query changes
  useEffect(() => {
    if (searchQuery) {
      refetch();
    }
  }, [searchQuery, refetch]);

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-4">Select Lyrics</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Choose the best lyrics for this song, or skip if you'll add them later.
        </p>
      </div>

      {isLoading ? (
        <LyricsLoadingState />
      ) : lyricsOptions.length === 0 ? (
        <EmptyLyricsState onSkip={onSkip} />
      ) : (
        <LyricsResultsList 
          options={lyricsOptions}
          onSelect={handleLyricsSelect}
        />
      )}

      <div className="flex justify-end gap-2 pt-4 border-t">
        <Button variant="outline" onClick={onSkip}>
          Skip Lyrics
        </Button>
        <Button onClick={onNext}>
          Continue
        </Button>
      </div>
    </div>
  );
};
```

#### Search Refinement Input Component
```typescript
// components/add/dialog/steps/SearchRefinementInput.tsx
export const SearchRefinementInput = ({
  query,
  onQueryChange,
  placeholder
}) => {
  const [localQuery, setLocalQuery] = useState(query);
  const debouncedQuery = useDebouncedValue(localQuery, 800);

  useEffect(() => {
    if (debouncedQuery !== query) {
      onQueryChange(debouncedQuery);
    }
  }, [debouncedQuery, onQueryChange, query]);

  return (
    <div className="space-y-2 flex-1">
      <Label htmlFor="search-refinement" className="text-sm font-medium">
        Search Query
      </Label>
      <Input
        id="search-refinement"
        value={localQuery}
        onChange={(e) => setLocalQuery(e.target.value)}
        placeholder={placeholder}
        className="w-full"
      />
      <p className="text-xs text-muted-foreground">
        Edit this search to get better lyrics or metadata results
      </p>
    </div>
  );
};
```

## 📋 Implementation Phases

### Phase 1: Foundation & Infrastructure (Week 1)
#### Goals
- Set up new unified search components directory
- Create base types and interfaces
- Enhance existing hooks for tab-based searching

#### Tasks
1. **Create directory structure**
   ```bash
   mkdir -p frontend/src/components/add/search
   mkdir -p frontend/src/components/add/dialog/steps
   ```

2. **Define core types**
   - Extend existing search result types for unified interface
   - Add source-aware types for dialog enhancement

3. **Enhance existing hooks**
   - `useYoutubeMusicSearch.ts` - Add conditional searching based on tab
   - `useYoutubeVideoSearch.ts` - Add conditional searching based on tab
   - `useSearchRefinement.ts` - New hook for dialog search refinement

4. **Create shared components**
   - `SearchRefinementInput.tsx` - Reusable search input for dialog
   - Base result card components

#### Deliverables
- [ ] Directory structure created
- [ ] Search hooks enhanced for conditional searching
- [ ] Base shared components created
- [ ] Search refinement hook implemented

### Phase 2: Search Interface (Week 2)
#### Goals
- Create tabbed search interface on AddSong page
- Implement conditional search based on active tab
- Display results directly on page (not in dialog)

#### Tasks
1. **Build search components**
   - `SongSearchContainer.tsx` - Main container with tabs and results
   - `SearchInput.tsx` - Single search field
   - `SearchTabs.tsx` - Tab switching between YouTube Music and YouTube
   - `SearchResults.tsx` - Conditional results display based on active tab

2. **Create source-specific result displays**
   - `YoutubeMusicResults.tsx` - YouTube Music results with "Add to Library" buttons
   - `YouTubeResults.tsx` - YouTube video results with "Add to Library" buttons
   - Result card components with consistent interaction patterns

3. **Update AddSong page**
   - Replace current dual search components with unified interface
   - Test tab switching and conditional searching
   - Ensure results display properly on page

4. **Connect to song creation**
   - Wire up "Add to Library" buttons to create song records
   - Open existing SongAdditionStepper dialog after song creation
   - Pass source information to dialog for flow determination

#### Deliverables
- [ ] Unified search interface implemented on AddSong page
- [ ] Tab-based conditional searching working
- [ ] Results displaying properly on page
- [ ] Song creation integrated with existing dialog
- [ ] Source information passed to dialog

### Phase 3: Enhanced Dialog with Search Refinement (Week 3)
#### Goals
- Enhance existing SongAdditionStepper with search refinement
- Add persistent search input at bottom of dialog
- Implement source-aware step flows

#### Tasks
1. **Enhance existing dialog**
   - Add `source` prop to `SongAdditionStepper` 
   - Implement source-aware step flow (1 step for YouTube Music, 2 for YouTube)
   - Add persistent search refinement input to dialog footer

2. **Enhance existing step components**
   - `LyricsSelectionStep.tsx` - Add search query prop and refinement capability
   - `MetadataSelectionStep.tsx` - Add search query prop and refinement capability
   - Auto-refetch results when search query changes

3. **Add search refinement component**
   - `SearchRefinementInput.tsx` - Debounced search input for dialog footer
   - Position above or below cancel/confirm buttons (to be decided)
   - Pre-populate with appropriate search query based on source

4. **Update song creation workflow**
   - YouTube Music: Create song with trusted metadata from result
   - YouTube: Create song with search query as title
   - Pass source and original query to dialog

#### Deliverables
- [ ] SongAdditionStepper enhanced with source-aware flows
- [ ] Search refinement working in dialog footer
- [ ] Existing step components enhanced with query refinement
- [ ] Source-specific song creation implemented
- [ ] Dialog flows tested for both sources

### Phase 4: Integration & Testing (Week 4)
#### Goals
- Connect all components into complete workflow
- Comprehensive testing across user flows
- Performance optimization and polish

#### Tasks
1. **End-to-end integration**
   - Connect search → selection → confirmation → completion
   - Test YouTube Music flow (search → lyrics → complete)
   - Test YouTube flow (search → lyrics → metadata → complete)

2. **Error handling & edge cases**
   - No search results scenarios
   - API failure recovery
   - Network connectivity issues
   - Invalid search queries

3. **Performance optimization**
   - Implement search result caching
   - Optimize re-renders with React.memo
   - Add skeleton loading states
   - Implement virtual scrolling for large result sets

4. **Polish & accessibility**
   - Keyboard navigation support
   - Screen reader compatibility
   - Focus management in dialog
   - Loading and error states polish

#### Deliverables
- [ ] Complete user flows tested
- [ ] Error handling implemented
- [ ] Performance optimized
- [ ] Accessibility verified
- [ ] User testing completed

### Phase 5: Cleanup & Documentation (Week 5)
#### Goals
- Remove old components and code
- Update documentation and types
- Prepare for production deployment

#### Tasks
1. **Remove deprecated components**
   - Delete `components/add/youtube/`
   - Delete `components/add/YoutubeMusicSearch/`
   - Update imports and references
   - Clean up unused hooks and services

2. **Update documentation**
   - Component API documentation
   - User flow documentation
   - Developer setup guide
   - Troubleshooting guide

3. **Final testing & validation**
   - Regression testing on existing functionality
   - Cross-browser compatibility testing
   - Mobile responsiveness verification
   - Performance benchmarking

4. **Deployment preparation**
   - Bundle size analysis
   - Production build testing
   - Feature flag implementation (if needed)
   - Rollback plan documentation

#### Deliverables
- [ ] Old components removed
- [ ] Documentation updated
- [ ] Final testing completed
- [ ] Ready for production deployment

## 🎯 Success Metrics

### User Experience Metrics
- **Search Time**: Time from query input to result selection
- **Completion Rate**: Percentage of searches that result in added songs
- **Error Rate**: Frequency of search or creation failures
- **User Satisfaction**: Feedback on new unified interface

### Technical Metrics
- **Component Count**: Reduction in total components
- **Code Complexity**: Reduction in cyclomatic complexity
- **Bundle Size**: Impact on application bundle size
- **Performance**: Search response times, rendering performance

### Expected Improvements
- **50% reduction** in component count and complexity
- **30% faster** search-to-completion workflow
- **90% reduction** in user-reported search issues
- **Improved maintainability** with separated concerns

## 🚨 Risks & Mitigation

### Technical Risks
1. **API Compatibility**: Changes might break existing integrations
   - *Mitigation*: Maintain API interfaces, comprehensive testing

2. **Performance Regression**: New architecture might be slower
   - *Mitigation*: Performance monitoring, optimization focus

3. **User Adoption**: Users might prefer familiar interface
   - *Mitigation*: User testing, gradual rollout, feedback collection

### Rollback Plan
- Feature flag to switch between old and new interfaces
- Database migrations are backwards compatible
- Old components preserved until new system is proven stable

## 📝 Notes

- This refactor prioritizes YouTube Music as the primary source while maintaining YouTube video search as a fallback
- Search refinement eliminates the need for separate confirmation steps
- The simplified dialog structure reduces cognitive load while maintaining necessary quality controls
- Architecture supports future search sources (Spotify, Apple Music, etc.)
