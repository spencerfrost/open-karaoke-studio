# Open Karaoke Studio - UI Documentation

## Overview

The Open Karaoke Studio UI is a modern, responsive web application designed with a vintage aesthetic inspired by retro enamel signs. The interface combines nostalgia with functionality to create an engaging karaoke experience for users.

The application is structured around two primary interfaces:
1. **Singer/Participant View** - For adding songs, managing the queue, and browsing the library
2. **Player View** - For full-screen display of lyrics and playback controls

## Design System

### Color Palette
- **Russet (#774320)** - Deep brown used for backgrounds
- **Rust (#B44819)** - Reddish-brown/orange for accents and headers
- **Lemon Chiffon (#F5F3C7)** - Creamy off-white for text and content cards
- **Orange Peel (#FD9A02)** - Vibrant orange for interactive elements and highlights
- **Dark Cyan (#01928B)** - Teal/turquoise for primary buttons and active states

### Typography
- **Body Text**: DM Sans - A clean, readable font for general content
- **Accent Text**: VT323 - A monospace retro font for headers and special elements

### Visual Elements
- **Texture Overlay**: Subtle noise pattern to mimic worn enamel
- **Sunburst Patterns**: Radiating background elements for vintage aesthetic
- **Rounded Corners**: Soft edges to mimic vintage sign shapes
- **High Contrast**: Clear visual hierarchy with strong color contrasts

## Component Architecture

### Core Structure

```
App
├── Layout Components
│   ├── AppLayout        # Standard layout with navigation
│   ├── PlayerLayout     # Full-screen karaoke view
│   └── NavBar           # Bottom navigation
├── Pages
│   ├── Library          # Song browsing
│   ├── AddSong          # Upload new songs
│   ├── Queue            # Manage singer lineup
│   ├── Settings         # Application preferences
│   └── Player           # Karaoke interface
├── Context Providers
│   ├── SongsContext     # Song library management
│   ├── QueueContext     # Singer queue management
│   ├── PlayerContext    # Playback state management
│   └── SettingsContext  # User preferences
```

### Component Breakdown

#### Layout Components

**AppLayout**
- Provides consistent page structure for standard views
- Includes navigation bar and theme elements
- Handles responsive behavior across devices

**PlayerLayout**
- Specialized full-screen layout for karaoke view
- Minimal UI focused on lyrics display
- Optional controls overlay

**NavBar**
- Bottom navigation for mobile-friendly access
- Visual indicators for active section
- Consistent access to main app functions

#### Pages

**Library**
- Browse all processed songs
- Toggle between grid and list views
- Search and filter functionality
- Song favorite management

**AddSong**
- File upload with drag-and-drop support
- YouTube URL import
- Processing queue status display
- Error handling for uploads

**Queue**
- Current song display
- Upcoming singers list
- Add to queue form
- Queue management functions

**Settings**
- Theme customization
- Audio settings (vocal/instrumental volumes)
- Processing quality options
- Display preferences

**Player**
- Karaoke experience with lyrics display
- Audio visualization
- Playback controls
- QR code for session joining when idle

#### Functional Components

**SongCard**
- Displays song information in grid or list format
- Play/Add to Queue actions
- Favorite toggle
- Status indication (processed, processing, queued)

**FileUploader**
- Drag-and-drop file input
- Upload progress display
- File validation
- Error messaging

**YouTubeImporter**
- URL input with validation
- Video preview thumbnail
- Additional metadata capture
- Processing initiation

**QueueItem**
- Singer and song information
- Position indicator
- Remove option
- Active state styling

**LyricsDisplay**
- Current and upcoming lyrics
- Size customization based on settings
- Singer name display
- Emphasized styling for current lyric

**AudioVisualizer**
- Real-time visualization of audio playback
- Responsive bar heights
- Customizable through settings
- Fallback states for paused/idle

**ProgressBar**
- Song progress indication
- Interactive seeking
- Time displays
- Visual styling consistent with theme

**ProcessingQueue**
- Status of songs being processed
- Progress indicators
- Cancel options
- Error state handling

#### Context Management

**SongsContext**
- Song library state management
- Filtering and search functionality
- Song status tracking
- Favorite status management

**QueueContext**
- Singer queue management
- Current singer tracking
- Queue ordering
- Add/remove functions

**PlayerContext**
- Playback state (playing, paused, idle)
- Current position tracking
- Volume control
- Audio source management

**SettingsContext**
- User preferences storage
- Theme settings
- Audio settings
- Processing preferences
- Persistent storage using localStorage

## User Experience Flows

### Adding a Song
1. User navigates to Add Song page
2. Selects upload method (file or YouTube)
3. Provides song file or URL
4. (Optional) Adds metadata
5. Initiates processing
6. Views progress in processing queue
7. Receives notification when processing completes

### Queuing Up to Sing
1. User navigates to Queue page
2. Enters their name
3. Selects a song from library
4. Submits to add themselves to queue
5. Views their position in line
6. Receives notification when it's their turn

### Karaoke Performance
1. Current song displays on Player view
2. Singer name is prominently shown
3. Lyrics are displayed in sync with music
4. Current line is highlighted
5. Next line is shown below in muted style
6. Audio visualization provides visual feedback
7. Progress bar shows position in song
8. Option to toggle vocal guide on/off

### Managing Library
1. User browses song collection in Library
2. Toggles between grid/list views based on preference
3. Searches for specific songs
4. Filters by status or favorites
5. Marks favorites for quick access
6. Selects songs to play or add to queue

## Integration Points

### API Services

The UI is structured around these primary service modules:

**api.ts**
- Base configuration for API requests
- Error handling and response formatting
- File upload utilities

**songService.ts**
- Song library management
- Favorite toggling
- Song status retrieval
- Download functionality

**uploadService.ts**
- File upload processing
- YouTube video processing
- Processing status tracking
- Queue management

**queueService.ts**
- Singer queue management
- Current singer tracking
- Queue reordering
- QR code generation

## Implementation Details

### Responsive Design
- Mobile-first approach prioritizing touchscreen interactions
- Adaptive layouts for different screen sizes
- Bottom navigation for thumb-friendly mobile use
- Full-screen mode optimized for TV display

### State Management
- React Context API for global state
- Reducer pattern for predictable state updates
- Local component state for UI-specific behaviors
- Persistent settings using localStorage

### Styling Approach
- Tailwind CSS for utility-first styling
- Custom theme system using CSS variables
- Component-specific styling with inline styles
- Shared theme utils for consistency

## Required Backend Integration

To make this UI fully functional, the following API endpoints need to be implemented:

1. **Songs Management**
   - `GET /songs` - Retrieve all songs
   - `GET /songs/:id` - Get specific song details
   - `PUT /songs/:id` - Update song metadata
   - `DELETE /songs/:id` - Remove a song
   - `PUT /songs/:id/favorite` - Toggle favorite status

2. **Upload Processing**
   - `POST /process` - Upload and process audio file
   - `POST /process-youtube` - Process YouTube video
   - `GET /status/:id` - Get processing status
   - `GET /processing-queue` - List all processing tasks
   - `POST /processing/:id/cancel` - Cancel processing

3. **Queue Management**
   - `GET /queue` - Get current queue
   - `GET /queue/current` - Get current playing item
   - `POST /queue` - Add to queue
   - `DELETE /queue/:id` - Remove from queue
   - `PUT /queue/reorder` - Reorder queue
   - `POST /queue/next` - Skip to next
   - `GET /queue/qr-code` - Get QR code for joining

4. **Audio Files**
   - `GET /download/:id/vocals` - Download vocals
   - `GET /download/:id/instrumental` - Download instrumental
   - `GET /download/:id/original` - Download original file

## Moving Towards Production Readiness

### Data Integration
1. **Replace Mock Data**: The current implementation uses placeholders and simulated behavior in many places
2. **API Error Handling**: Implement robust error handling for all API calls
3. **Loading States**: Add proper loading indicators during data fetching

### Authentication (if needed)
1. **User System**: Add authentication if multi-user support is required
2. **Permission Levels**: Consider host vs. participant permissions
3. **Session Management**: Implement session handling for karaoke nights

### Audio Processing
1. **Audio Player Integration**: Connect real audio player functionality
2. **Waveform Visualization**: Use actual audio data for visualizations
3. **Lyrics Synchronization**: Implement proper timing for lyrics display

### Performance Optimization
1. **Bundle Size**: Optimize JS and CSS bundles
2. **Lazy Loading**: Implement code splitting for different views
3. **Image Optimization**: Properly handle album artwork and thumbnails
4. **Caching Strategy**: Implement service workers for offline functionality

### Testing & Quality Assurance
1. **Unit Tests**: Add tests for components and utilities
2. **Integration Tests**: Test API integration points
3. **E2E Tests**: Add end-to-end testing for critical user flows
4. **Accessibility**: Ensure WCAG compliance
5. **Cross-browser Testing**: Verify compatibility across browsers

### Deployment
1. **Build Process**: Set up proper build pipeline
2. **Environment Configuration**: Handle different deployment environments
3. **Analytics**: Add usage tracking if desired
4. **Monitoring**: Implement error tracking and monitoring

### Additional Features
1. **Lyrics Editor**: Allow manual adjustment of lyrics timing
2. **Room Management**: Support for multiple concurrent karaoke rooms
3. **Song Recommendations**: Suggest songs based on user preferences
4. **Mobile App Wrapper**: Consider PWA or native wrapper for mobile use
5. **Social Features**: Sharing, voting, or other community elements