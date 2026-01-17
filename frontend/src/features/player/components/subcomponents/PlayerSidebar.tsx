/**
 * PlayerSidebar - Sidebar for performance controls within the player
 * Supports two display modes:
 * - "floating": Overlay sidebar that doesn't affect layout (semi-transparent)
 * - "push": Sidebar that takes horizontal space and pushes content over
 */

import React, { useState, useRef, useCallback } from 'react';
import { Settings2, X, ScrollText, RotateCcw, Minus, Plus, Save, Search, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { useKaraokePlayerStore } from '@/stores/useKaraokePlayerStore';
import { useSongs } from '@/hooks/api/useSongs';
import { applyOffsetToLrc } from '@/utils/lrcUtils';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import LyricsFetchDialog from '@/features/lyrics/components/LyricsFetchDialog';
import PasteLyricsDialog from '@/features/lyrics/components/PasteLyricsDialog';
import type { LyricsResult } from '@/features/lyrics/components/LyricsFetchDialog';
import type { Song } from '@/types/Song';

export type SidebarMode = 'floating' | 'push';

interface PlayerSidebarProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  mode?: SidebarMode;
  className?: string;
}

// Content of the sidebar - separated for reuse
const SidebarContent: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const {
    songId,
    vocalVolume,
    instrumentalVolume,
    lyricsSize,
    lyricsOffset,
    autoScrollEnabled,
    setVocalVolume,
    setInstrumentalVolume,
    setLyricsSize,
    setLyricsOffset,
    setAutoScrollEnabled,
  } = useKaraokePlayerStore();

  // Fetch current song for synced lyrics
  const { useSong, useUpdateSong } = useSongs();
  const { data: song } = useSong(songId ?? '');
  const updateSongMutation = useUpdateSong();

  // Lyrics dialog state
  const [isLyricsDialogOpen, setIsLyricsDialogOpen] = useState(false);
  const [isPasteLyricsDialogOpen, setIsPasteLyricsDialogOpen] = useState(false);

  // Drag state for timing offset
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartY, setDragStartY] = useState(0);
  const [dragStartValue, setDragStartValue] = useState(0);
  const offsetRef = useRef<HTMLDivElement>(null);

  // Check if we can save (has synced lyrics and non-zero offset)
  const canSave = song?.syncedLyrics && lyricsOffset !== 0;

  const handleSaveOffset = useCallback(() => {
    if (!songId || !song?.syncedLyrics || lyricsOffset === 0) return;
    
    const updatedLyrics = applyOffsetToLrc(song.syncedLyrics, lyricsOffset);
    
    updateSongMutation.mutate({
      id: songId,
      syncedLyrics: updatedLyrics,
    }, {
      onSuccess: () => {
        setLyricsOffset(0); // Reset offset after save
      },
      onError: (error) => {
        toast.error(`Failed to save: ${error.message}`);
      }
    });
  }, [songId, song?.syncedLyrics, lyricsOffset, updateSongMutation, setLyricsOffset]);

  // Lyrics search/paste handlers
  const handleLyricsSelected = useCallback((lyricsResult: LyricsResult) => {
    if (!songId) {
      toast.error("Cannot update song: missing song ID");
      return;
    }

    updateSongMutation.mutate({
      id: songId,
      plainLyrics: lyricsResult.plainLyrics,
      syncedLyrics: lyricsResult.syncedLyrics,
    }, {
      onSuccess: () => {
        setIsLyricsDialogOpen(false);
      },
      onError: (error) => {
        toast.error(`Failed to update lyrics: ${error.message}`);
      }
    });
  }, [songId, updateSongMutation]);

  const handlePasteLyricsConfirmed = useCallback((pastedLyrics: string) => {
    if (!songId) {
      toast.error("Cannot update song: missing song ID");
      return;
    }

    updateSongMutation.mutate({
      id: songId,
      plainLyrics: pastedLyrics,
      syncedLyrics: undefined, // Clear synced lyrics when pasting plain lyrics
    }, {
      onSuccess: () => {
        setIsPasteLyricsDialogOpen(false);
      },
      onError: (error) => {
        toast.error(`Failed to save lyrics: ${error.message}`);
      }
    });
  }, [songId, updateSongMutation]);

  const handleOffsetMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    setDragStartY(e.clientY);
    setDragStartValue(lyricsOffset);
    document.body.style.cursor = 'ns-resize';
  }, [lyricsOffset]);

  const handleOffsetMouseMove = useCallback((e: MouseEvent) => {
    if (!isDragging) return;
    e.preventDefault();
    const deltaY = dragStartY - e.clientY; // Drag up = positive
    const sensitivity = 1; // pixels per 100ms step (more significant)
    const deltaSteps = Math.round(deltaY / sensitivity);
    const newValue = dragStartValue + (deltaSteps * 100);
    if (newValue !== lyricsOffset) {
      setLyricsOffset(newValue);
    }
  }, [isDragging, dragStartY, dragStartValue, lyricsOffset, setLyricsOffset]);

  const handleOffsetMouseUp = useCallback(() => {
    setIsDragging(false);
    document.body.style.cursor = 'auto';
  }, []);

  // Touch support
  const handleOffsetTouchStart = useCallback((e: React.TouchEvent) => {
    const touch = e.touches[0];
    setIsDragging(true);
    setDragStartY(touch.clientY);
    setDragStartValue(lyricsOffset);
  }, [lyricsOffset]);

  const handleOffsetTouchMove = useCallback((e: TouchEvent) => {
    if (!isDragging) return;
    e.preventDefault();
    const touch = e.touches[0];
    const deltaY = dragStartY - touch.clientY;
    const sensitivity = 1; // pixels per 100ms step (more significant)
    const deltaSteps = Math.round(deltaY / sensitivity);
    const newValue = dragStartValue + (deltaSteps * 100);
    if (newValue !== lyricsOffset) {
      setLyricsOffset(newValue);
    }
  }, [isDragging, dragStartY, dragStartValue, lyricsOffset, setLyricsOffset]);

  const handleOffsetTouchEnd = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Global event listeners for drag
  React.useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleOffsetMouseMove);
      document.addEventListener('mouseup', handleOffsetMouseUp);
      document.addEventListener('touchmove', handleOffsetTouchMove, { passive: false });
      document.addEventListener('touchend', handleOffsetTouchEnd);
      return () => {
        document.removeEventListener('mousemove', handleOffsetMouseMove);
        document.removeEventListener('mouseup', handleOffsetMouseUp);
        document.removeEventListener('touchmove', handleOffsetTouchMove);
        document.removeEventListener('touchend', handleOffsetTouchEnd);
      };
    }
  }, [isDragging, handleOffsetMouseMove, handleOffsetMouseUp, handleOffsetTouchMove, handleOffsetTouchEnd]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Settings2 className="w-5 h-5 text-orange-peel" />
          <h2 className="text-lg font-semibold text-background">Controls</h2>
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onClose}
          className="text-background/60 hover:text-background hover:bg-white/10"
        >
          <X className="w-5 h-5" />
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-6">
        {/* Lyrics Section */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-background/70 uppercase tracking-wider flex items-center gap-2">
            <ScrollText className="w-4 h-4" />
            Lyrics
          </h3>

          {/* Auto-Scroll Toggle */}
          <div className="flex items-center justify-between">
            <Label htmlFor="auto-scroll" className="text-background">
              Auto-scroll
            </Label>
            <Switch
              id="auto-scroll"
              checked={autoScrollEnabled}
              onCheckedChange={setAutoScrollEnabled}
            />
          </div>

          {/* Lyrics Size */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-background">Text Size</Label>
              <span className="text-sm text-background/60 capitalize">{lyricsSize}</span>
            </div>
            <Slider
              value={[lyricsSize === 'small' ? 1 : lyricsSize === 'medium' ? 2 : 3]}
              onValueChange={([value]) => {
                setLyricsSize(value === 1 ? 'small' : value === 2 ? 'medium' : 'large');
              }}
              min={1}
              max={3}
              step={1}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-background/40">
              <span>Small</span>
              <span>Medium</span>
              <span>Large</span>
            </div>
          </div>

          {/* Lyrics Offset - Drag to adjust */}
          <div className="space-y-2">
            <Label className="text-background">Timing Offset</Label>
            <div className="flex items-center gap-2">
              {/* Decrease button */}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setLyricsOffset(lyricsOffset - 100)}
                className="h-8 w-8 text-background/60 hover:text-background hover:bg-white/10"
              >
                <Minus className="w-4 h-4" />
              </Button>

              {/* Draggable value display */}
              <div
                ref={offsetRef}
                className={cn(
                  "flex-1 py-2 px-3 rounded-md bg-white/5 border border-white/10",
                  "cursor-ns-resize select-none text-center font-mono text-lg",
                  "hover:bg-white/10 hover:border-white/20 transition-colors",
                  isDragging && "bg-white/15 border-orange-peel ring-1 ring-orange-peel"
                )}
                onMouseDown={handleOffsetMouseDown}
                onTouchStart={handleOffsetTouchStart}
              >
                <span className="text-background">
                  {lyricsOffset > 0 ? '+' : ''}{lyricsOffset}ms
                </span>
              </div>

              {/* Increase button */}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setLyricsOffset(lyricsOffset + 100)}
                className="h-8 w-8 text-background/60 hover:text-background hover:bg-white/10"
              >
                <Plus className="w-4 h-4" />
              </Button>

              {/* Reset button */}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setLyricsOffset(0)}
                className="h-8 w-8 text-background/60 hover:text-background hover:bg-white/10"
                title="Reset to 0"
              >
                <RotateCcw className="w-4 h-4" />
              </Button>

              {/* Save button - only show when offset is non-zero and song has synced lyrics */}
              {canSave && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={handleSaveOffset}
                  disabled={updateSongMutation.isPending}
                  className="h-8 w-8 text-orange-peel hover:text-orange-peel/80 hover:bg-white/10"
                  title="Save timing adjustment permanently"
                >
                  <Save className="w-4 h-4" />
                </Button>
              )}
            </div>
            <div className="text-xs text-background/40 text-center">
              Drag up/down to adjust
            </div>
          </div>

          {/* Lyrics Search/Replace Buttons */}
          {song && (
            <div className="space-y-2">
              <Label className="text-background">Find or Replace Lyrics</Label>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsLyricsDialogOpen(true)}
                  className="flex-1 text-background border-white/20 hover:bg-white/10"
                >
                  <Search className="w-4 h-4 mr-2" />
                  Search
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsPasteLyricsDialogOpen(true)}
                  className="flex-1 text-background border-white/20 hover:bg-white/10"
                >
                  <FileText className="w-4 h-4 mr-2" />
                  Paste
                </Button>
              </div>
              <p className="text-xs text-background/40">
                Search for better lyrics or paste your own
              </p>
            </div>
          )}
        </div>

        <Separator className="bg-white/10" />

        {/* Volume Section */}
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-background/70 uppercase tracking-wider">
            🎤 Volume
          </h3>

          {/* Vocal Volume */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-background">Vocals</Label>
              <span className="text-sm text-background/60">{Math.round(vocalVolume * 100)}%</span>
            </div>
            <Slider
              value={[vocalVolume]}
              onValueChange={([value]) => setVocalVolume(value)}
              min={0}
              max={1}
              step={0.05}
              className="w-full"
            />
          </div>

          {/* Instrumental Volume */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-background">Instrumental</Label>
              <span className="text-sm text-background/60">{Math.round(instrumentalVolume * 100)}%</span>
            </div>
            <Slider
              value={[instrumentalVolume]}
              onValueChange={([value]) => setInstrumentalVolume(value)}
              min={0}
              max={1}
              step={0.05}
              className="w-full"
            />
          </div>
        </div>
      </div>

      {/* Lyrics Dialogs */}
      {song && (
        <>
          <LyricsFetchDialog
            isOpen={isLyricsDialogOpen}
            onClose={() => setIsLyricsDialogOpen(false)}
            song={{
              id: songId,
              title: song.title,
              artist: song.artist,
              album: song.album || '',
              duration: song.duration,
            } as Song}
            onLyricsSelected={handleLyricsSelected}
          />
          <PasteLyricsDialog
            isOpen={isPasteLyricsDialogOpen}
            onClose={() => setIsPasteLyricsDialogOpen(false)}
            onLyricsConfirmed={handlePasteLyricsConfirmed}
          />
        </>
      )}
    </div>
  );
};

// Toggle button for opening the sidebar
export const PlayerSidebarTrigger: React.FC<{
  onClick: () => void;
  className?: string;
}> = ({ onClick, className }) => (
  <Button
    variant="ghost"
    size="icon"
    onClick={onClick}
    className={cn(
      "text-background/60 hover:text-background hover:bg-white/10",
      className
    )}
    aria-label="Open settings"
  >
    <Settings2 className="w-5 h-5" />
  </Button>
);

const PlayerSidebar: React.FC<PlayerSidebarProps> = ({
  isOpen,
  onOpenChange,
  mode = 'floating',
  className,
}) => {
  if (!isOpen) {
    return null;
  }

  const baseClasses = cn(
    "flex flex-col bg-black/90 backdrop-blur-md border-l border-white/10",
    "w-72 min-w-72 max-w-72", // Fixed width
    className
  );

  if (mode === 'floating') {
    return (
      <>
        {/* Backdrop for floating mode */}
        <div
          className="absolute inset-0 z-40"
          onClick={() => onOpenChange(false)}
          aria-hidden="true"
        />
        {/* Floating sidebar */}
        <div
          className={cn(
            baseClasses,
            "absolute top-0 right-0 bottom-0 z-50",
            "animate-in slide-in-from-right duration-300"
          )}
        >
          <SidebarContent onClose={() => onOpenChange(false)} />
        </div>
      </>
    );
  }

  // Push mode - just renders inline, parent handles layout
  return (
    <div
      className={cn(
        baseClasses,
        "relative h-full",
        "animate-in slide-in-from-right duration-300"
      )}
    >
      <SidebarContent onClose={() => onOpenChange(false)} />
    </div>
  );
};

export default PlayerSidebar;
