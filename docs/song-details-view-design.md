# Song Details View Design

## Overview
A comprehensive song details dialog that appears when users click on a song card, replacing the current direct-to-player navigation. This provides a detailed metadata view and editing capabilities before proceeding to karaoke playback.

## Current Behavior vs. Proposed Behavior

### Current Behavior
- User clicks on song card image → immediately goes to karaoke player page
- Limited metadata editing via separate "Edit Metadata" button
- No comprehensive view of all song details

### Proposed Behavior
- User clicks anywhere on song card → opens Song Details Dialog
- Dialog shows comprehensive metadata in organized sections
- Multiple action options available from within dialog
- Eventually navigate to player from dialog (not directly from card)

## Dialog Design Specifications

### Layout & Structure
- **Large dialog** covering most of the screen (desktop focus for now)
- **Landscape orientation** preferred for desktop
- **Modal dialog** (not separate page) - may evolve to separate page later
- **Mobile considerations**: Full screen on mobile (implementation TBD)

### Main Content Sections

#### 1. Primary Song Details (Top Section - Prominent)
**Purpose**: Core song information that belongs to the song itself (not tied to specific APIs)
**Content**:
- Song title, artist, album
- Primary artwork (large display)
- Duration, genre, year
- Metadata quality indicator
- Source badges (iTunes/YouTube indicators)

#### 2. iTunes Metadata Section
**Purpose**: iTunes-specific data and identifiers
**Content**:
- iTunes Track ID, Artist ID, Collection ID
- iTunes artwork URLs (all sizes)
- iTunes preview URL
- Explicit content flag
- iTunes-specific metadata

#### 3. YouTube Metadata Section  
**Purpose**: YouTube-specific data and identifiers
**Content**:
- Video ID, Channel ID, Channel Name
- YouTube thumbnail URLs (all sizes)
- YouTube tags and categories
- Upload date, duration
- Description (truncated)

#### 4. Lyrics Section
**Purpose**: Display and manage song lyrics
**Content**:
- Current lyrics (if available)
- Synced lyrics indicator
- Language information
- Lyrics source information

#### 5. Actions Section
**Purpose**: User interactions and editing capabilities
**Content**: Large, prominent buttons for key actions

## Core User Actions

### 1. Lyrics Management
- **Edit/Correct Lyrics**: Manual lyrics editing capability
- **Refetch Lyrics**: Trigger new lyrics search/fetch
- **Sync Lyrics**: Timing synchronization tools (future)

### 2. Image Selection & Management
- **Choose Primary Image**: Select between cover art and thumbnail
- **Upload Custom Image**: Allow user-provided images
- **Paste Image URL**: Direct URL input for custom artwork
- **Download/Cache Logic**: Handle image processing behind scenes

### 3. Metadata Correction
- **Re-search iTunes**: Trigger new iTunes API search with user input
- **Manual Override**: Allow users to correct automated metadata
- **Verification Tools**: Help users identify correct releases/versions
- **Batch Update Options**: For fixing automated script results

## Implementation Strategy

### Phase 1: Basic Dialog Structure
- Create large modal dialog component
- Implement basic sectioned layout
- Migrate existing metadata display into sections
- Update card click behavior to open dialog

### Phase 2: Enhanced Metadata Display  
- Implement all metadata sections (iTunes, YouTube, Core)
- Add metadata quality indicators
- Integrate existing rich display components
- Ensure responsive design

### Phase 3: Action Integration
- Implement lyrics editing/refetching
- Add image selection interface  
- Create iTunes re-search functionality
- Add prominent action buttons

### Phase 4: Advanced Features
- Custom image upload/URL functionality
- Batch metadata correction tools
- Advanced lyrics synchronization
- Mobile optimization

## Technical Considerations

### Dialog Component Structure
```
SongDetailsDialog
├── PrimarySongDetails (top section)
├── MetadataTabs or Sections
│   ├── CoreMetadataSection
│   ├── ITunesMetadataSection  
│   ├── YouTubeMetadataSection
│   └── LyricsSection
└── ActionsSection (bottom)
```

### State Management
- Dialog open/close state
- Editing mode toggles
- Unsaved changes tracking
- API call status indicators

### Integration Points
- Update SongCard click handlers
- Integrate with existing metadata components
- Connect to iTunes/YouTube APIs
- Link to lyrics management system

## User Experience Flow

### Primary Flow
1. User browses song library
2. User clicks on song card (anywhere on card)
3. Song Details Dialog opens with comprehensive view
4. User can view all metadata, make edits, or take actions
5. User can navigate to player from dialog or close to return to library

### Editing Flow
1. User opens song details
2. User identifies incorrect/missing metadata
3. User selects appropriate action (re-search, manual edit, etc.)
4. System processes request and updates display
5. User confirms changes or makes additional edits

## Future Enhancements (Ideas to Remember)

### Advanced Image Management
- Integration with additional image sources
- Automatic image quality detection
- Bulk image update tools
- Custom image cropping/editing

### Metadata Intelligence
- Machine learning for metadata correction suggestions
- Duplicate detection and merging
- Metadata confidence scoring
- Automated quality improvement suggestions

### Collaborative Features
- User-contributed metadata corrections
- Community verification system
- Metadata change history/versioning
- Shared custom artwork library

### Mobile Optimization
- Touch-optimized interface
- Swipe navigation between sections
- Simplified action buttons
- Portrait-friendly layouts

## Implementation Priority

### High Priority (016C Completion)
- Basic dialog structure and metadata display
- Integration with existing rich metadata components
- Core navigation behavior change

### Medium Priority (Next Sprint)
- Action buttons and basic editing capabilities
- iTunes re-search functionality
- Image selection interface

### Low Priority (Future Releases)
- Advanced editing features
- Mobile optimization
- Collaborative features

## Notes & Considerations

### Design Philosophy
- **Progressive Disclosure**: Show basic info prominently, detailed info in organized sections
- **User Control**: Allow users to correct automated metadata decisions
- **Contextual Actions**: Place editing tools where users naturally expect them
- **Non-Destructive**: Always preserve original metadata alongside user edits

### Technical Debt Considerations
- Current "Edit Metadata" button can be removed once dialog is implemented
- Direct-to-player navigation may need user preference option
- Consider performance impact of loading all metadata for dialog
- Plan for eventual migration to dedicated page if dialog becomes too complex

### Success Metrics
- Reduced user confusion about song details
- Increased metadata accuracy through user corrections  
- Improved user engagement with song management features
- Faster access to comprehensive song information

---

*This document captures the vision for enhanced song details management. Implementation should be iterative, starting with core functionality and expanding based on user feedback and technical feasibility.*
