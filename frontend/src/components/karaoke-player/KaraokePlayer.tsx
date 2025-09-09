/**
 * KaraokePlayer - Main unified karaoke player component
 * YouTube-like API: <KaraokePlayer songId="123" />
 */

import React from 'react';
import { useKaraokePlayer, usePlayerUI } from './hooks';
import {
  LyricsDisplay,
  PlayerControls,
  FullscreenContainer,
  PlayerErrorBoundary,
} from './subcomponents';
import AudioVisualizer from '@/components/karaoke-player/subcomponents/AudioVisualizer';
import ProgressBar from '@/components/karaoke-player/subcomponents/ProgressBar';
import { formatTime } from '@/utils/formatters';
import type { KaraokePlayerProps } from './KaraokePlayer.types';

const KaraokePlayer: React.FC<KaraokePlayerProps> = ({
  songId,
  autoPlay = false,
  size = 'full',
  controls = true,
  showInfo = true,
  showVisualizer = true,
  onPlay,
  onPause,
  onEnd,
  onTimeUpdate,
  onError,
  className = '',
}) => {
  // Initialize player and UI hooks
  const player = useKaraokePlayer(songId, { autoPlay });
  const ui = usePlayerUI();

  // Handle play/pause callbacks
  React.useEffect(() => {
    if (player.isPlaying && onPlay) {
      onPlay();
    } else if (!player.isPlaying && onPause) {
      onPause();
    }
  }, [player.isPlaying, onPlay, onPause]);

  // Handle error callback
  React.useEffect(() => {
    if (player.error && onError) {
      onError(player.error);
    }
  }, [player.error, onError]);

  // Handle time update callback
  React.useEffect(() => {
    if (onTimeUpdate) {
      onTimeUpdate(player.currentTime, player.duration);
    }
  }, [player.currentTime, player.duration, onTimeUpdate]);

  // Handle song end callback
  React.useEffect(() => {
    if (onEnd && player.duration > 0 && player.currentTime >= player.duration) {
      onEnd();
    }
  }, [player.currentTime, player.duration, onEnd]);

  // Volume control handlers
  const handleVolumeToggle = () => {
    if (player.vocalVolume === 0) {
      player.setVocalVolume(1);
    } else {
      player.setVocalVolume(0);
    }
  };

  // Size-based styling
  const sizeClasses = {
    compact: 'max-h-80',
    full: 'aspect-video',
    stage: 'min-h-screen',
  };

  const lyricsVisibility = {
    compact: showInfo ? 'pb-16' : 'pb-12',
    full: showInfo ? 'pb-20' : 'pb-16', 
    stage: showInfo ? 'pb-24' : 'pb-20',
  };

  // Show controls based on configuration
  const showControls = controls;
  const showPlay = showControls;
  const showVolume = showControls;
  const showProgress = showControls;
  const showFullscreen = showControls;

  // Loading state
  if (player.isLoading) {
    return (
      <div className={`${sizeClasses[size]} ${className} flex items-center justify-center bg-black/80 rounded-xl`}>
        <div className="text-lg text-orange-peel animate-pulse">
          Loading song...
        </div>
      </div>
    );
  }

  // Error state
  if (player.error) {
    return (
      <div className={`${sizeClasses[size]} ${className} flex flex-col items-center justify-center bg-black/80 rounded-xl text-center p-8`}>
        <div className="text-red-500 text-lg font-semibold mb-4">
          {player.error.message}
        </div>
        <button 
          onClick={() => player.reload()}
          className="text-orange-peel hover:text-orange-peel/80 underline"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <PlayerErrorBoundary onError={onError}>
      <FullscreenContainer
        isFullscreen={ui.isFullscreen}
        containerRef={ui.containerRef}
        fsError={ui.fsError}
        className={`${sizeClasses[size]} ${className} bg-black/80 rounded-xl overflow-hidden`}
      >
        {/* Song Info Header */}
        {showInfo && player.song && (
          <div className="absolute top-2 left-3 z-30 text-background/50">
            <h1 className={`font-bold ${size === 'stage' ? 'text-2xl' : 'text-xl'}`}>
              {player.song.title}
            </h1>
            <h2 className={`${size === 'stage' ? 'text-lg' : 'text-base'}`}>
              {player.song.artist}
            </h2>
          </div>
        )}

        {/* Main Lyrics Display */}
        <LyricsDisplay
          lyrics={player.lyrics}
          isSync={player.isLyricsSync}
          currentTime={player.currentTime}
          lyricsSize={player.lyricsSize}
          lyricsOffset={player.lyricsOffset}
          className={lyricsVisibility[size]}
          songId={songId}
          songTitle={player.song?.title}
          songArtist={player.song?.artist}
          songAlbum={player.song?.album}
          songDuration={player.song?.duration}
        />

        {/* Bottom Controls Area */}
        <div className="w-full absolute bottom-0 left-0 right-0">
          {/* Audio Visualizer */}
          {showVisualizer && <AudioVisualizer className="w-full" />}

          {/* Progress Bar */}
          {showProgress && (
            <ProgressBar
              currentTime={player.currentTime}
              duration={player.duration}
              onSeek={player.seek}
            />
          )}

          {/* Player Controls */}
          <div className="flex items-center">
            {/* Main Controls (Play/Pause, Volume) */}
            <PlayerControls
              isPlaying={player.isPlaying}
              isReady={player.isReady}
              vocalVolume={player.vocalVolume}
              isFullscreen={ui.isFullscreen}
              showVolumeSlider={ui.showVolumeSlider}
              controls={[showPlay && 'play', showVolume && 'volume'].filter(Boolean) as Array<'play' | 'volume'>}
              onPlayPause={player.togglePlay}
              onVolumeChange={player.setVocalVolume}
              onVolumeToggle={handleVolumeToggle}
              onFullscreenToggle={ui.toggleFullscreen}
              onVolumeSliderShow={ui.setShowVolumeSlider}
            />

            {/* Time Display */}
            {showProgress && (
              <div className={`flex-1 text-sm text-background/50 ${size === 'compact' ? 'text-xs' : 'text-sm'}`}>
                {formatTime(player.currentTime)} / {formatTime(player.duration)}
              </div>
            )}

            {/* Fullscreen Control */}
            {showFullscreen && (
              <PlayerControls
                isPlaying={player.isPlaying}
                isReady={player.isReady}
                vocalVolume={player.vocalVolume}
                isFullscreen={ui.isFullscreen}
                showVolumeSlider={ui.showVolumeSlider}
                controls={['fullscreen']}
                onPlayPause={player.togglePlay}
                onVolumeChange={player.setVocalVolume}
                onVolumeToggle={handleVolumeToggle}
                onFullscreenToggle={ui.toggleFullscreen}
                onVolumeSliderShow={ui.setShowVolumeSlider}
              />
            )}
          </div>
        </div>
      </FullscreenContainer>
    </PlayerErrorBoundary>
  );
};

export default KaraokePlayer;