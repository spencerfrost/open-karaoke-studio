import React, { useState } from "react";
import { useKaraokeQueueStore } from "@/stores/useKaraokeQueueStore";
import { useSongs } from "../context/SongsContext";
import QueueList from "../components/queue/KaraokeQueueList";
import AppLayout from "../components/layout/AppLayout";
import vintageTheme from "@/utils/theme";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { KaraokeQueueState } from "@/types/KaraokeQueue";

const state: KaraokeQueueState = {
  currentSong: null, // Initialize with null or a valid KaraokeQueueItemWithSong
  items: [],
};

if (state.currentSong) {
  console.log(`Now playing: ${state.currentSong.song.title}`);
}

const KaraokeQueuePage: React.FC = () => {
  const {
    addToKaraokeQueue,
    removeFromKaraokeQueue,
    currentQueueItem, // Use currentQueueItem from the store
    items,
    error,
    isLoading,
    setError,
  } = useKaraokeQueueStore();

  const { state: songsState } = useSongs();
  const [selectedSongId, setSelectedSongId] = useState<string>("");
  const [singerName, setSingerName] = useState<string>("");
  const colors = vintageTheme.colors;

  // Handle singer name input
  const handleSingerNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSingerName(e.target.value);
    if (error) setError(null);
  };

  // Handle adding to queue
  const handleAddToQueue = () => {
    if (!singerName.trim()) {
      setError("Please enter your name");
      return;
    }

    if (!selectedSongId) {
      setError("Please select a song");
      return;
    }

    const song = songsState.songs.find((s) => s.id === selectedSongId);
    if (!song) {
      setError("Selected song not found.");
      return;
    }

    const queueItem = {
      id: `${selectedSongId}-${Date.now()}`,
      songId: selectedSongId,
      singer: singerName,
      song,
      position: items.length + 1,
      addedAt: new Date().toISOString(),
    };

    try {
      addToKaraokeQueue(queueItem);

      setSingerName("");
      setSelectedSongId("");
    } catch {
      setError("Failed to add to queue. Please try again.");
    }
  };

  const handleRemoveFromQueue = async (id: string) => {
    try {
      removeFromKaraokeQueue(id);
    } catch (err) {
      console.error("Failed to remove from queue:", err);
    }
  };

  return (
    <AppLayout>
      <div>
        <h1
          className="text-2xl font-semibold mb-6"
          style={{ color: colors.orangePeel }}
        >
          Singer Queue
        </h1>

        {/* Current song (if any) */}
        {currentQueueItem ? ( // Check for currentQueueItem
          <div className="rounded-lg p-4 mb-6 bg-background text-russet">
            <h2 className="font-medium mb-3 text-primary">Now Playing</h2>
            <div className="flex items-center">
              <div className="h-16 w-16 rounded-md flex items-center justify-center mr-4 bg-primary/20">
                {currentQueueItem.song.coverArt ? (
                  <img
                    src={currentQueueItem.song.coverArt}
                    alt={currentQueueItem.song.title}
                    className="h-full w-full object-cover rounded-md"
                  />
                ) : (
                  <div className="h-12 w-12 bg-gray-600 rounded-full flex items-center justify-center">
                    <span className="text-white">♪</span>
                  </div>
                )}
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-lg">
                  {currentQueueItem.song.title}
                </h3>
                <p className="opacity-75">{currentQueueItem.song.artist}</p>
                <p className="text-sm mt-1 text-accent">
                  Singer: {currentQueueItem.singer}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-center text-gray-500 mb-6">
            No song is currently playing.
          </p>
        )}

        {/* Queue list */}
        <h2 className="font-medium mb-2 text-primary">Up Next</h2>
        <div className="rounded-lg overflow-hidden mb-6 bg-background border border-primary backdrop-blur-sm">
          {isLoading ? (
            <div className="p-6 text-center text-background">
              Loading queue...
            </div>
          ) : (
            <QueueList
              items={items}
              onRemove={handleRemoveFromQueue}
              emptyMessage="No singers in the queue"
            />
          )}
        </div>

        {/* Add to queue form */}
        <div className="rounded-lg p-4 bg-background text-russet">
          <h3 className="font-medium mb-3">Add Yourself to Queue</h3>

          {error && (
            <div className="mb-3 p-2 rounded text-sm bg-secondary/20 text-secondary">
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <Input
              type="text"
              placeholder="Your Name"
              value={singerName}
              onChange={handleSingerNameChange}
            />
            <Select
              value={selectedSongId}
              onValueChange={(value) => setSelectedSongId(value)}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select a Song" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Select a Song</SelectItem>
                {songsState.songs
                  .filter((song) => song.status === "processed")
                  .map((song) => (
                    <SelectItem key={song.id} value={song.id}>
                      {song.title} - {song.artist}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          </div>
          <Button className="w-full" onClick={handleAddToQueue}>
            Add to Queue
          </Button>
        </div>
      </div>
    </AppLayout>
  );
};

export default KaraokeQueuePage;
