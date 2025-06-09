import React, { useState, useRef, useEffect } from "react";
import { Play, Pause, Volume2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SongPreviewPlayerProps {
  previewUrl: string;
  title: string;
  artist: string;
  className?: string;
}

export const SongPreviewPlayer: React.FC<SongPreviewPlayerProps> = ({
  previewUrl,
  title,
  artist,
  className = "",
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(30); // iTunes previews are 30 seconds
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const audioRef = useRef<HTMLAudioElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);

  // Auto-stop after 30 seconds
  useEffect(() => {
    if (currentTime >= 30 && isPlaying) {
      handleStop();
    }
  }, [currentTime, isPlaying]);

  // Audio event handlers
  const handleLoadedData = () => {
    setIsLoading(false);
    setError(null);
    if (audioRef.current) {
      setDuration(Math.min(audioRef.current.duration, 30));
    }
  };

  const handleError = () => {
    setIsLoading(false);
    setError("Failed to load preview");
    setIsPlaying(false);
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };

  const handlePlay = () => {
    if (!audioRef.current) return;
    
    setIsLoading(true);
    setError(null);
    
    audioRef.current.play()
      .then(() => {
        setIsPlaying(true);
        setIsLoading(false);
      })
      .catch(() => {
        setError("Failed to play preview");
        setIsLoading(false);
        setIsPlaying(false);
      });
  };

  const handlePause = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
  };

  const handleStop = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
      setCurrentTime(0);
    }
  };

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!audioRef.current || !progressRef.current) return;
    
    const rect = progressRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const progressWidth = rect.width;
    const clickRatio = clickX / progressWidth;
    const newTime = Math.min(clickRatio * duration, 30);
    
    audioRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const progressPercentage = (currentTime / duration) * 100;

  return (
    <div className={cn("border rounded-lg p-4 bg-muted/20", className)}>
      <audio
        ref={audioRef}
        src={previewUrl}
        onLoadedData={handleLoadedData}
        onError={handleError}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        preload="metadata"
      />
      
      <div className="flex items-center gap-3">
        <Button
          variant="outline"
          size="sm"
          onClick={isPlaying ? handlePause : handlePlay}
          disabled={isLoading || !!error}
          className="flex-shrink-0"
        >
          {isLoading ? (
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-current border-t-transparent" />
          ) : isPlaying ? (
            <Pause size={16} />
          ) : (
            <Play size={16} />
          )}
        </Button>

        <div className="flex-1">
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="font-medium truncate">
              {title} - {artist}
            </span>
            <span className="text-xs text-muted-foreground">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>
          </div>
          
          <div
            ref={progressRef}
            className="w-full h-2 bg-muted rounded-full cursor-pointer"
            onClick={handleProgressClick}
          >
            <div
              className="h-full bg-primary rounded-full transition-all duration-100"
              style={{ width: `${Math.min(progressPercentage, 100)}%` }}
            />
          </div>
          
          {error && (
            <p className="text-xs text-destructive mt-1">{error}</p>
          )}
        </div>

        <Volume2 size={16} className="text-muted-foreground flex-shrink-0" />
      </div>
      
      <p className="text-xs text-muted-foreground mt-2 leading-tight">
        30-second preview from iTunes. Hold phone to ear for best experience.
      </p>
    </div>
  );
};
