# Karaoke Sessions

Host amazing karaoke sessions using Open Karaoke Studio's real-time queue system, performance controls, and stage management features.

## 🎤 Session Overview

Open Karaoke Studio provides a complete karaoke hosting solution with real-time queue management, performance controls, and synchronized displays for seamless karaoke experiences.

### Core Session Components
- **Stage Display** - Main screen showing current song and lyrics
- **Queue Management** - Add, reorder, and manage upcoming performances
- **Performance Controls** - Real-time audio and visual adjustments
- **Mobile Controls** - Performers can control their own experience

## 🚀 Starting a Karaoke Session

### Quick Setup
1. **Navigate to Stage** - Click the "Stage" tab
2. **Check Connection** - Verify WebSocket connection (green indicator)
3. **Connect Display** - Set up your main display/projector
4. **Test Audio** - Ensure speakers are connected and working
5. **Add First Song** - Add a song to the queue to begin

### Display Setup
**Recommended Configuration:**
- **Primary Display** - Performer interface on laptop/tablet
- **Secondary Display** - Stage view on TV/projector for audience
- **Mobile Device** - Performance controls for active performer

**Single Display Setup:**
- Use the Stage tab as your main interface
- Switch between queue management and performance view
- Mobile-friendly interface for touch control

## 🎵 Queue Management

### Adding Songs to Queue
**From Library:**
1. Browse your song library
2. Click "Add to Queue" on any song
3. Enter performer name
4. Song appears in queue automatically

**Quick Add:**
1. Use search to find songs quickly
2. Type performer name
3. Song is immediately queued

**Batch Adding:**
- Select multiple songs from library
- Add all with same performer name
- Or assign different performers to each song

### Queue Operations
**Reorder Songs:**
- Drag and drop to reorder queue
- Move urgent performers to front
- Organize by song type or performer preference

**Remove Songs:**
- Click "X" to remove individual songs
- Clear completed songs automatically
- Mass remove for session cleanup

**Queue Information:**
- See estimated wait times
- View total queue length
- Monitor processing status for upcoming songs

## 🎭 Managing Performances

### Performance Flow
1. **Song Selection** - System automatically loads next queued song
2. **Performer Setup** - Performer adjusts volume and lyrics settings
3. **Performance Start** - Click play to begin karaoke track
4. **Live Adjustments** - Real-time volume and display controls
5. **Song Completion** - Automatic queue advancement

### Real-time Controls
**Audio Controls:**
- **Vocal Volume** - Adjust backing vocal levels
- **Instrumental Volume** - Control background music volume
- **Master Volume** - Overall playback level
- **Audio Effects** *(Future)* - Reverb, echo, and voice enhancement

**Visual Controls:**
- **Lyrics Size** - Adjust text size for readability
- **Lyrics Offset** - Sync timing adjustments
- **Display Mode** - Full screen, windowed, or mobile view
- **Theme Settings** - Visual appearance customization

## 📱 Mobile Performance Controls

### Performer Mobile Interface
Open Karaoke Studio provides a dedicated mobile interface for performers:

**Access Mobile Controls:**
1. Navigate to `/controls` on your mobile device
2. Connect to the same network as the main system
3. Controls automatically sync with current performance

**Mobile Control Features:**
- **Personal Volume Controls** - Adjust your own vocal/instrumental mix
- **Lyrics Size** - Personalize text size for comfortable reading
- **Progress Control** - See song progress and remaining time
- **Emergency Controls** - Pause, restart, or skip if needed

### Multi-Device Sessions
- **Host Device** - Main queue and session management
- **Performer Devices** - Individual performance controls
- **Audience Devices** - Queue viewing and song requests *(Future)*
- **Stage Display** - Lyrics and visual output

## 🎯 Stage Display Features

### Lyrics Display
**Smart Lyrics Presentation:**
- Large, readable text optimized for stage viewing
- Automatic scrolling synchronized with audio
- Highlighting of current lyrics line
- Multiple font sizes and styles

**Lyrics Modes:**
- **Full Screen** - Maximum readability for large venues
- **Overlay Mode** - Lyrics over background visuals
- **Minimal Mode** - Clean, distraction-free display
- **Karaoke Style** - Traditional karaoke appearance

### Visual Features
**Background Elements:**
- **Song Artwork** - Album covers and thumbnails
- **Animated Backgrounds** - Dynamic visual elements
- **Theme Consistency** - Matches application design
- **Custom Backgrounds** *(Future)* - Upload custom venue backgrounds

**Information Display:**
- **Current Song** - Title, artist, and album information
- **Performer Name** - Who's currently singing
- **Queue Preview** - Upcoming songs and performers
- **Session Status** - Connection and system information

## 🔄 Real-time Synchronization

### WebSocket Technology
All session features update in real-time using WebSocket connections:

**Live Updates:**
- Queue changes appear instantly on all devices
- Performance controls sync across all connected devices
- Volume adjustments reflect immediately
- Status changes broadcast to all participants

**Connection Management:**
- Automatic reconnection on network issues
- Connection status indicators on all interfaces
- Graceful degradation when connections are lost
- Manual reconnection options

### Multi-User Coordination
**Host Controls:**
- Primary queue management authority
- Override capabilities for performance issues
- Session settings and configuration
- Emergency controls and session reset

**Performer Participation:**
- Individual performance customization
- Personal device control options
- Queue position visibility
- Song request capabilities *(Future)*

## 🎵 Advanced Session Features

### Performance Enhancements
**Audio Processing:**
- Real-time vocal separation quality
- Audio normalization for consistent levels
- Crossfade between songs for smooth transitions
- Background noise suppression *(Future)*

**Visual Enhancements:**
- Smooth lyrics scrolling with timing
- Visual feedback for volume adjustments
- Queue status animations
- Performance timer and progress indicators

### Session Analytics *(Future)*
- Track most popular songs
- Monitor session duration and participation
- Generate session reports
- Export performance statistics

### Social Features *(Future)*
- **Song Requests** - Audience can request songs via mobile
- **Voting System** - Popular vote for next songs
- **Sharing** - Share session highlights on social media
- **Recording** *(Optional)* - Record performances for replay

## 🔧 Session Management Tools

### Session Configuration
**Audio Settings:**
- Default volume levels for vocals and instrumentals
- Audio quality preferences
- Microphone input settings *(Future)*
- External audio device configuration

**Display Settings:**
- Default lyrics size and style
- Theme and visual preferences
- Display timeout and screensaver settings
- Multi-monitor configuration

**Queue Settings:**
- Maximum songs per performer
- Automatic queue clearing options
- Break management between songs
- Session time limits

### Troubleshooting Sessions

**Common Issues:**
**Audio Problems:**
- Check system audio settings and device connections
- Verify volume levels aren't muted or too low
- Test with different songs to isolate issues
- Restart audio services if needed

**Sync Issues:**
- Refresh browser connections on all devices
- Check network connectivity and stability
- Verify all devices are on the same network
- Clear browser cache if controls become unresponsive

**Display Problems:**
- Check monitor connections and display settings
- Verify stage display is set to correct screen
- Adjust browser zoom for optimal text size
- Update graphics drivers if experiencing performance issues

**Queue Management:**
- Refresh browser if queue doesn't update
- Check WebSocket connection status indicators
- Manually reconnect if automatic reconnection fails
- Clear queue and restart if synchronization is lost

## 🎉 Session Best Practices

### Hosting Tips
**Pre-Session Setup:**
- Test all equipment before guests arrive
- Have a few popular songs ready in the queue
- Set comfortable default volume levels
- Prepare backup songs in case of technical issues

**During Sessions:**
- Encourage performers to use mobile controls
- Monitor audio levels and adjust as needed
- Help new users with interface navigation
- Keep backup songs ready for technical breaks

**Managing Large Groups:**
- Set reasonable song limits per person
- Use queue reordering to manage wait times
- Encourage group songs and duets
- Take breaks between major queue segments

### Technical Optimization
**Network Setup:**
- Ensure strong WiFi signal in performance area
- Use wired connections for critical displays when possible
- Test with expected number of connected devices
- Have backup internet connection available

**Performance Optimization:**
- Close unnecessary applications on host device
- Use dedicated devices for stage display when possible
- Monitor system performance during long sessions
- Restart services periodically for long events

## 🔗 Integration with Other Features

### Library Integration
- **Smart Recommendations** - Suggest songs based on session preferences
- **Quick Access** - Favorite and recent songs highlighted
- **Search Integration** - Fast song finding during sessions
- **Metadata Display** - Rich song information for decision making

### Processing Integration
- **Background Processing** - New songs can be added and processed during sessions
- **Quality Indicators** - Show vocal separation quality for song selection
- **Processing Queue** - Monitor background jobs without disrupting session

### Analytics Integration *(Future)*
- **Session Metrics** - Track participation and song popularity
- **Historical Data** - Build profiles of successful session songs
- **Recommendation Engine** - Suggest songs based on past sessions
- **Venue Integration** - Adapt to different performance spaces

---

**Related Guides:**
- **[Library Management](library-management.md)** - Organizing songs for sessions
- **[Uploading Songs](uploading-songs.md)** - Adding new content for sessions
- **[Advanced Features](advanced-features.md)** - Power user session management
