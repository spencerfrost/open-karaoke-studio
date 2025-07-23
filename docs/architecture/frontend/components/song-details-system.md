# Song Details System - Open Karaoke Studio Frontend

**Last Updated**: June 15, 2025  
**Status**: Implemented  
**Components**: SongDetailsDialog • SongPreviewPlayer • PrimarySongDetails • SongLyricsSection

## 🎯 Overview

The Song Details System provides a comprehensive interface for viewing song metadata, previewing audio, and managing song information. The system replaces direct-to-player navigation with a rich dialog experience that allows users to review detailed song information before making playback decisions.

## 🏗️ Architecture Overview

### Component Hierarchy

```
SongDetailsDialog (Main Container)
├── DialogHeader (Song Title & Artist)
├── Main Content Grid
│   ├── ArtworkDisplay (Large Cover Art)
│   └── PrimarySongDetails (Metadata Grid)
├── SongLyricsSection (Lyrics Display)
├── SongPreviewPlayer (iTunes Preview)
└── DialogFooter (Action Buttons)
```

### Key Integration Points

- **Song Cards** trigger dialog opening instead of direct navigation
- **Artwork Display** component reused for large cover art
- **Source Badges** and **Metadata Quality Indicators** integrated
- **iTunes Preview API** for 30-second audio previews

## 🎵 Core Components

### SongDetailsDialog

**File**: `/frontend/src/components/songs/SongDetailsDialog.tsx`

Main dialog container that orchestrates the song details display:

```typescript
interface SongDetailsDialogProps {
  song: Song | null;
  open: boolean;
  onClose: () => void;
}

function SongDetailsDialog({ song, open, onClose }: SongDetailsDialogProps) {
  // Auto-stop audio when dialog closes
  useEffect(() => {
    if (!open) {
      // Stop any playing preview audio
      const audioElements = document.querySelectorAll("audio");
      audioElements.forEach((audio) => {
        audio.pause();
        audio.currentTime = 0;
      });
    }
  }, [open]);

  if (!song) return null;

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden">
        <DialogHeader className="border-b border-border pb-4">
          <DialogTitle className="text-2xl font-bold text-rust">
            {song.title}
          </DialogTitle>
          <DialogDescription className="text-lg text-muted-foreground">
            {song.artist}
          </DialogDescription>
        </DialogHeader>

        {/* Main content grid - responsive layout */}
        <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] gap-6 py-4">
          {/* Left column: Artwork */}
          <div className="flex justify-center lg:justify-start">
            <ArtworkDisplay
              song={song}
              size="lg"
              className="w-full max-w-[300px] aspect-square rounded-lg shadow-lg"
            />
          </div>

          {/* Right column: Metadata */}
          <div className="space-y-4">
            <PrimarySongDetails song={song} />
          </div>
        </div>

        {/* Full-width sections */}
        {song.lyrics && (
          <div className="border-t border-border pt-4">
            <SongLyricsSection lyrics={song.lyrics} />
          </div>
        )}

        {song.itunesPreviewUrl && (
          <div className="border-t border-border pt-4">
            <SongPreviewPlayer
              previewUrl={song.itunesPreviewUrl}
              title={song.title}
              artist={song.artist}
            />
          </div>
        )}

        <DialogFooter className="border-t border-border pt-4">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button variant="vintage" onClick={() => handlePlay(song)}>
            <Play className="h-4 w-4 mr-2" />
            Play Song
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

**Key Features**:

- **Large Responsive Layout** - Optimized for desktop and tablet viewing
- **Auto-cleanup** - Stops audio when dialog closes
- **ESC Key Support** - Standard dialog behavior
- **Sticky Header** - Song title remains visible during scrolling
- **Modular Content** - Each section can be conditionally rendered

### SongPreviewPlayer

**File**: `/frontend/src/components/songs/SongPreviewPlayer.tsx`

iTunes 30-second preview player with progress tracking:

```typescript
interface SongPreviewPlayerProps {
  previewUrl: string;
  title: string;
  artist: string;
}

function SongPreviewPlayer({
  previewUrl,
  title,
  artist,
}: SongPreviewPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(30); // iTunes previews are 30 seconds
  const [loading, setLoading] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  const handlePlayPause = useCallback(async () => {
    if (!audioRef.current) return;

    try {
      setLoading(true);

      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        await audioRef.current.play();
        setIsPlaying(true);
      }
    } catch (error) {
      console.error("Audio playback error:", error);
      toast.error("Unable to play preview");
    } finally {
      setLoading(false);
    }
  }, [isPlaying]);

  const handleSeek = useCallback((newTime: number) => {
    if (!audioRef.current) return;

    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  }, []);

  // Auto-stop at 30 seconds
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);

      // Auto-stop at 30 seconds (iTunes preview limit)
      if (audio.currentTime >= 30) {
        audio.pause();
        setIsPlaying(false);
        audio.currentTime = 0;
        setCurrentTime(0);
      }
    };

    const handleLoadedData = () => {
      setDuration(Math.min(audio.duration, 30));
    };

    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("loadeddata", handleLoadedData);

    return () => {
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("loadeddata", handleLoadedData);
    };
  }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="font-medium text-foreground">Preview</h4>
        <Badge variant="secondary" className="text-xs">
          iTunes • 30s
        </Badge>
      </div>

      <div className="flex items-center gap-3">
        <Button
          size="sm"
          variant="outline"
          onClick={handlePlayPause}
          disabled={loading}
          className="flex-shrink-0"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : isPlaying ? (
            <Pause className="h-4 w-4" />
          ) : (
            <Play className="h-4 w-4" />
          )}
        </Button>

        <div className="flex-1 space-y-1">
          <Progress
            value={(currentTime / duration) * 100}
            className="h-2 cursor-pointer"
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const x = e.clientX - rect.left;
              const percentage = x / rect.width;
              const newTime = percentage * duration;
              handleSeek(newTime);
            }}
          />

          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>
      </div>

      {/* Hidden audio element */}
      <audio ref={audioRef} src={previewUrl} preload="metadata" />

      {/* Mobile-friendly note */}
      <p className="text-xs text-muted-foreground md:hidden">
        💡 For best audio quality, hold phone to your ear
      </p>
    </div>
  );
}
```

**Key Features**:

- **30-Second Auto-Stop** - Enforces iTunes preview limits
- **Click-to-Seek** - Users can click progress bar to jump
- **Loading States** - Visual feedback during audio loading
- **Error Handling** - Graceful fallback for audio failures
- **Mobile Optimization** - Special messaging for mobile users

### PrimarySongDetails

**File**: `/frontend/src/components/songs/PrimarySongDetails.tsx`

Organized metadata display in CSS Grid layout:

```typescript
interface PrimarySongDetailsProps {
  song: Song;
}

function PrimarySongDetails({ song }: PrimarySongDetailsProps) {
  const { getAlbumName, getMetadataQuality, formatDuration } = useSongs();

  return (
    <div className="space-y-6">
      {/* Primary metadata grid */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        <div>
          <span className="font-medium text-muted-foreground">Album</span>
          <p className="text-foreground">{getAlbumName(song)}</p>
        </div>

        <div>
          <span className="font-medium text-muted-foreground">Duration</span>
          <p className="text-foreground">{formatDuration(song.duration)}</p>
        </div>

        <div>
          <span className="font-medium text-muted-foreground">Genre</span>
          <p className="text-foreground">{song.genre || "Unknown"}</p>
        </div>

        <div>
          <span className="font-medium text-muted-foreground">Year</span>
          <p className="text-foreground">{song.year || "Unknown"}</p>
        </div>

        <div>
          <span className="font-medium text-muted-foreground">Artist</span>
          <p className="text-foreground">{song.artist}</p>
        </div>

        <div>
          <span className="font-medium text-muted-foreground">Track #</span>
          <p className="text-foreground">
            {song.trackNumber ? `${song.trackNumber}` : "Unknown"}
            {song.totalTracks && ` of ${song.totalTracks}`}
          </p>
        </div>
      </div>

      {/* Quality and source indicators */}
      <div className="flex items-center gap-2 flex-wrap">
        <MetadataQualityIndicator quality={getMetadataQuality(song)} />
        <SourceBadges song={song} />

        {song.explicit && (
          <Badge variant="destructive" className="text-xs">
            Explicit
          </Badge>
        )}
      </div>

      {/* Additional metadata */}
      {(song.fileSize || song.bitrate || song.sampleRate) && (
        <div className="border-t border-border pt-4">
          <h4 className="font-medium text-foreground mb-2">Technical Info</h4>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            {song.fileSize && (
              <div>
                <span className="font-medium text-muted-foreground">
                  File Size
                </span>
                <p className="text-foreground">
                  {formatFileSize(song.fileSize)}
                </p>
              </div>
            )}

            {song.bitrate && (
              <div>
                <span className="font-medium text-muted-foreground">
                  Bitrate
                </span>
                <p className="text-foreground">{song.bitrate} kbps</p>
              </div>
            )}

            {song.sampleRate && (
              <div>
                <span className="font-medium text-muted-foreground">
                  Sample Rate
                </span>
                <p className="text-foreground">{song.sampleRate} Hz</p>
              </div>
            )}

            {song.format && (
              <div>
                <span className="font-medium text-muted-foreground">
                  Format
                </span>
                <p className="text-foreground">{song.format.toUpperCase()}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
```

**Key Features**:

- **CSS Grid Layout** - Organized, scannable metadata display
- **Conditional Rendering** - Only shows available metadata
- **Quality Indicators** - Visual feedback for metadata completeness
- **Technical Information** - Detailed file and audio specs
- **Badge Integration** - Visual indicators for special attributes

### SongLyricsSection

**File**: `/frontend/src/components/songs/SongLyricsSection.tsx`

Comprehensive lyrics display with formatting and indicators:

```typescript
interface SongLyricsSectionProps {
  lyrics: string | null;
  synced?: boolean;
}

function SongLyricsSection({ lyrics, synced = false }: SongLyricsSectionProps) {
  if (!lyrics) {
    return (
      <div className="text-center py-8">
        <Music className="h-12 w-12 text-muted-foreground mx-auto mb-2" />
        <p className="text-muted-foreground">No lyrics available</p>
      </div>
    );
  }

  const lines = lyrics.split("\n").filter((line) => line.trim());
  const lineCount = lines.length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h4 className="font-medium text-foreground">Lyrics</h4>
          {synced && (
            <Badge variant="outline" className="text-xs">
              <Clock className="h-3 w-3 mr-1" />
              Synced
            </Badge>
          )}
        </div>
        <span className="text-xs text-muted-foreground">{lineCount} lines</span>
      </div>

      <div className="bg-muted/30 rounded-lg p-4 max-h-60 overflow-y-auto">
        <div className="space-y-1">
          {lines.map((line, index) => (
            <p key={index} className="text-sm text-foreground leading-relaxed">
              {line}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}
```

**Key Features**:

- **Graceful Fallback** - Handles missing lyrics elegantly
- **Line Processing** - Properly formats and displays lyrics
- **Synced Indicator** - Shows if lyrics are time-synchronized
- **Scrollable Container** - Prevents dialog overflow with long lyrics
- **Line Count Display** - Quick reference for lyrics length

## 🔄 User Experience Flow

### Previous Behavior

```
Song Card Click → Direct Navigation to Player
```

### Current Behavior

```
Song Card Click → Song Details Dialog → User Choice:
├── Play Now (direct to karaoke player)
├── Add to Queue (queue management)
├── View Lyrics (scroll to lyrics section)
├── Preview Audio (iTunes 30-second preview)
└── Close (return to library)
```

### Enhanced Navigation Pattern

```typescript
// Updated SongCard click handling
function SongCard({ song, onSelect }: SongCardProps) {
  const handleCardClick = useCallback(() => {
    onSelect(song);
  }, [song, onSelect]);

  return (
    <Card
      className="cursor-pointer group hover:shadow-md transition-shadow"
      onClick={handleCardClick}
      role="button"
      tabIndex={0}
      aria-label={`View details for ${song.title} by ${song.artist}`}
    >
      {/* Card content */}
    </Card>
  );
}

// Library page integration
function LibraryPage() {
  const [selectedSong, setSelectedSong] = useState<Song | null>(null);

  return (
    <>
      <SongGrid songs={songs} onSongSelect={setSelectedSong} />

      <SongDetailsDialog
        song={selectedSong}
        open={!!selectedSong}
        onClose={() => setSelectedSong(null)}
      />
    </>
  );
}
```

## 📱 Responsive Design Implementation

### Desktop Layout (lg and above)

```css
/* Two-column grid with fixed artwork width */
.grid.grid-cols-1.lg: grid-cols-[300px_1fr].gap-6;
```

### Tablet Layout (md to lg)

```css
/* Single column with centered artwork */
.grid.grid-cols-1.gap-6 .flex.justify-center;
```

### Mobile Layout (sm and below)

```css
/* Full-width dialog with optimized spacing */
.max-w-4xl /* Becomes full-width on mobile */
/* Becomes full-width on mobile */
/* Becomes full-width on mobile */
/* Becomes full-width on mobile */
.p-4; /* Reduced padding */
```

### Touch-Friendly Interactions

- **Larger touch targets** for preview controls
- **Simplified navigation** with clear action buttons
- **Optimized scrolling** for lyrics sections
- **Mobile audio messaging** for better UX

## 🔌 Integration Points

### Backend API Integration

```typescript
// Uses existing song data structure
interface Song {
  id: string;
  title: string;
  artist: string;
  album?: string;
  duration: number;
  lyrics?: string;
  itunesPreviewUrl?: string;
  genre?: string;
  year?: number;
  // ... other metadata fields
}
```

### Component Reuse Strategy

- **ArtworkDisplay** - Reused for large cover art display
- **SourceBadges** - Integrated for iTunes/YouTube indicators
- **MetadataQualityIndicator** - Shows data completeness
- **Existing hooks** - `useSongs()` for data access and formatting

### State Management Integration

```typescript
// Global song selection state
const { selectedSong, setSelectedSong } = useSongsStore();

// Server state for song data
const { data: song } = useSong(selectedSong?.id);

// Local state for dialog interactions
const [previewPlaying, setPreviewPlaying] = useState(false);
```

## 🧪 Testing Strategy

### Component Testing

```typescript
describe("SongDetailsDialog", () => {
  it("displays song information correctly", () => {
    const mockSong = createMockSong();
    render(
      <SongDetailsDialog song={mockSong} open={true} onClose={jest.fn()} />
    );

    expect(screen.getByText(mockSong.title)).toBeInTheDocument();
    expect(screen.getByText(mockSong.artist)).toBeInTheDocument();
  });

  it("stops audio when dialog closes", () => {
    const mockSong = createMockSong({ itunesPreviewUrl: "test.mp3" });
    const { rerender } = render(
      <SongDetailsDialog song={mockSong} open={true} onClose={jest.fn()} />
    );

    // Start audio playback
    const playButton = screen.getByRole("button", { name: /play/i });
    fireEvent.click(playButton);

    // Close dialog
    rerender(
      <SongDetailsDialog song={mockSong} open={false} onClose={jest.fn()} />
    );

    // Verify audio stopped
    const audioElements = document.querySelectorAll("audio");
    audioElements.forEach((audio) => {
      expect(audio.paused).toBe(true);
      expect(audio.currentTime).toBe(0);
    });
  });
});
```

### Integration Testing

```typescript
describe("Song Details System Integration", () => {
  it("opens dialog when song card is clicked", async () => {
    const mockSongs = [createMockSong()];
    render(<LibraryPageWithDialog songs={mockSongs} />);

    const songCard = screen.getByLabelText(/view details/i);
    fireEvent.click(songCard);

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });
});
```

## 📊 Performance Considerations

### Lazy Loading

- **Dialog Content** - Only renders when dialog is open
- **Audio Elements** - Created only when preview URL exists
- **Lyrics Processing** - Deferred until lyrics section is accessed

### Memory Management

- **Audio Cleanup** - Automatic audio stopping on dialog close
- **Component Unmounting** - Proper cleanup of event listeners
- **State Reset** - Clears component state when dialog closes

### Optimization Patterns

```typescript
// Memoized expensive computations
const formattedDuration = useMemo(
  () => formatDuration(song.duration),
  [song.duration]
);

// Debounced audio seeking
const debouncedSeek = useCallback(
  debounce((time: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  }, 100),
  []
);
```

---

**Next Steps**: Explore the [Queue Management System](queue-management-system.md) to understand how song selection from the details dialog integrates with the karaoke queue, or check out the [Upload Workflow](upload-workflow.md) for how new songs enter the system.
