import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Play, Pause, SkipForward, Volume2, VolumeX } from 'lucide-react';
import { usePlayer } from '../context/PlayerContext';
import { useQueue } from '../context/QueueContext';
import PlayerLayout from '../components/layout/PlayerLayout';
import LyricsDisplay from '../components/player/LyricsDisplay';
import AudioVisualizer from '../components/player/AudioVisualizer';
import ProgressBar from '../components/player/ProgressBar';
import QRCodeDisplay from '../components/queue/QRCodeDisplay';
import QueueList from '../components/queue/QueueList';
import { skipToNext } from '../services/queueService';
import vintageTheme from '../utils/theme';
import { useSettings } from '../context/SettingsContext';

const PlayerPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { state: playerState, dispatch: playerDispatch } = usePlayer();
  const { state: queueState, dispatch: queueDispatch } = useQueue();
  const { settings } = useSettings();
  const [vocalsMuted, setVocalsMuted] = useState(false);
  const colors = vintageTheme.colors;

  // Load song data when id changes
  useEffect(() => {
    // In a real implementation, you would load the audio files here
    // For now, we'll just simulate loading a song by ID
    
    if (id) {
      // Find song in queue or fetch from API
      const queueItem = queueState.items.find(item => item.song.id === id) || 
                        (queueState.currentItem?.song.id === id ? queueState.currentItem : null);
      
      if (queueItem) {
        // Set as current song
        playerDispatch({ type: 'SET_CURRENT_SONG', payload: queueItem });
        
        // Set duration (in a real app, this would come from the audio element)
        playerDispatch({ type: 'SET_DURATION', payload: queueItem.song.duration });
        
        // Optional: set as current item in queue
        queueDispatch({ type: 'SET_CURRENT_ITEM', payload: queueItem });
      }
      
      // Start playing
      setTimeout(() => {
        playerDispatch({ type: 'SET_STATUS', payload: 'playing' });
      }, 500);
    }
  }, [id, playerDispatch, queueDispatch, queueState.items, queueState.currentItem]);

  // Toggle play/pause
  const handlePlayPause = () => {
    playerDispatch({ type: 'TOGGLE_PLAY_PAUSE' });
  };

  // Skip to next song
  const handleSkipNext = async () => {
    try {
      const response = await skipToNext();
      
      if (response.data) {
        // Set new current item
        queueDispatch({ type: 'SET_CURRENT_ITEM', payload: response.data });
        
        // Set as current song in player
        if (response.data) {
          playerDispatch({ type: 'SET_CURRENT_SONG', payload: response.data });
          playerDispatch({ type: 'SET_DURATION', payload: response.data.song.duration });
          playerDispatch({ type: 'SET_STATUS', payload: 'playing' });
        } else {
          // No more songs
          playerDispatch({ type: 'SET_CURRENT_SONG', payload: null });
          playerDispatch({ type: 'SET_STATUS', payload: 'idle' });
        }
      }
    } catch (err) {
      console.error('Failed to skip to next song:', err);
    }
  };

  // Toggle vocals
  const handleToggleVocals = () => {
    if (vocalsMuted) {
      // Restore vocal volume
      playerDispatch({ 
        type: 'SET_VOCAL_VOLUME', 
        payload: settings.audio.defaultVocalVolume 
      });
      setVocalsMuted(false);
    } else {
      // Mute vocals
      playerDispatch({ type: 'SET_VOCAL_VOLUME', payload: 0 });
      setVocalsMuted(true);
    }
  };

  // Handle seeking (in a real app, this would control the audio element)
  const handleSeek = (time: number) => {
    // For now, just update the current time
    playerDispatch({ type: 'SET_CURRENT_TIME', payload: time });
  };

  return (
    <PlayerLayout>
      {playerState.status === 'idle' || !playerState.currentSong ? (
        // Queue display when no song is playing
        <div className="flex flex-col h-full p-6 relative z-20">
          <div className="text-center mb-8 mt-12">
            <h1 
              className="text-4xl font-mono tracking-wide mb-2"
              style={{
                color: colors.lemonChiffon,
                textShadow: `2px 2px 0 ${colors.darkCyan}80`
              }}
            >
              OPEN KARAOKE STUDIO
            </h1>
            <p 
              className="text-lg opacity-80"
              style={{ color: colors.lemonChiffon }}
            >
              Scan the QR code to add songs to the queue
            </p>
          </div>
          
          {/* QR code to join */}
          <QRCodeDisplay 
            value={`${window.location.origin}/join`}
            title="Join the karaoke session"
            description="Use your phone to add songs and join the queue"
            className="mb-10"
          />
          
          <h2 
            className="text-2xl font-semibold text-center mb-4"
            style={{ color: colors.orangePeel }}
          >
            Up Next
          </h2>
          
          <div 
            className="max-w-2xl mx-auto w-full rounded-xl overflow-hidden"
            style={{
              backgroundColor: `${colors.lemonChiffon}20`,
              backdropFilter: 'blur(8px)',
              border: `1px solid ${colors.orangePeel}40`
            }}
          >
            <QueueList 
              items={queueState.items}
              emptyMessage="No songs in the queue"
            />
          </div>
        </div>
      ) : (
        // Karaoke Player View when song is playing
        <div className="flex flex-col h-full relative z-20">
          {/* Main lyrics and visualization area */}
          <div className="flex-1 flex flex-col items-center justify-center">
            {/* Audio visualization */}
            {settings.display.showAudioVisualizations && (
              <AudioVisualizer className="mb-6" />
            )}
            
            {/* Lyrics display */}
            <LyricsDisplay />
          </div>
          
          {/* Bottom controls */}
          <div 
            className="p-4 bg-gradient-to-t from-black to-transparent"
            style={{ zIndex: 30 }}
          >
            {/* Progress bar */}
            {settings.display.showProgress && (
              <ProgressBar 
                onChange={handleSeek} 
                className="mb-4"
              />
            )}
            
            {/* Playback controls */}
            <div className="flex justify-center items-center gap-4">
              <button
                className="p-3 rounded-full"
                style={{
                  backgroundColor: colors.darkCyan,
                  color: colors.lemonChiffon,
                }}
                onClick={handleToggleVocals}
                aria-label={vocalsMuted ? "Unmute vocals" : "Mute vocals"}
              >
                {vocalsMuted ? <VolumeX size={24} /> : <Volume2 size={24} />}
              </button>
              
              <button
                className="p-4 rounded-full"
                style={{
                  backgroundColor: colors.orangePeel,
                  color: colors.russet,
                }}
                onClick={handlePlayPause}
                aria-label={playerState.status === 'playing' ? "Pause" : "Play"}
              >
                {playerState.status === 'playing' ? (
                  <Pause size={32} />
                ) : (
                  <Play size={32} style={{ marginLeft: '3px' }} />
                )}
              </button>
              
              <button
                className="p-3 rounded-full"
                style={{
                  backgroundColor: colors.darkCyan,
                  color: colors.lemonChiffon,
                }}
                onClick={handleSkipNext}
                aria-label="Skip to next song"
              >
                <SkipForward size={24} />
              </button>
            </div>
          </div>
        </div>
      )}
    </PlayerLayout>
  );
};

export default PlayerPage;
