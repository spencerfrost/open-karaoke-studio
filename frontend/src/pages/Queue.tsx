import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useQueue } from "../context/QueueContext";
import { useSongs } from "../context/SongsContext";
import QueueList from "../components/queue/QueueList";
import AppLayout from "../components/layout/AppLayout";
import {
  getQueue,
  addToQueue,
  removeFromQueue,
  skipToNext,
} from "../services/queueService";
import vintageTheme from "../utils/theme";

const QueuePage: React.FC = () => {
  const location = useLocation();
  const { state: queueState, dispatch: queueDispatch } = useQueue();
  const { state: songsState } = useSongs();
  const [singerName, setSingerName] = useState("");
  const [selectedSongId, setSelectedSongId] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const colors = vintageTheme.colors;

  // If a songId is passed via location state, select it automatically
  useEffect(() => {
    if (location.state && location.state.songId) {
      setSelectedSongId(location.state.songId);
    }
  }, [location.state]);

  // Fetch queue on component mount
  useEffect(() => {
    const fetchQueue = async () => {
      setIsLoading(true);
      const response = await getQueue();
      setIsLoading(false);

      if (response.data) {
        queueDispatch({ type: "SET_QUEUE", payload: response.data });
      }
    };

    fetchQueue();
  }, [queueDispatch]);

  // Handle singer name input
  const handleSingerNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSingerName(e.target.value);
    if (error) setError(null);
  };

  // Handle song selection
  const handleSongSelection = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedSongId(e.target.value);
    if (error) setError(null);
  };

  // Handle adding to queue
  const handleAddToQueue = async () => {
    // Validate input
    if (!singerName.trim()) {
      setError("Please enter your name");
      return;
    }

    if (!selectedSongId) {
      setError("Please select a song");
      return;
    }

    try {
      const response = await addToQueue({
        songId: selectedSongId,
        singer: singerName,
      });

      if (response.error) {
        setError(response.error);
        return;
      }

      if (response.data) {
        // Find the matching song from the songs state
        const song = songsState.songs.find((s) => s.id === selectedSongId);

        if (song) {
          // Construct the queue item with song data
          const queueItem = {
            ...response.data,
            song,
          };

          // Add to queue state
          queueDispatch({ type: "ADD_TO_QUEUE", payload: queueItem });

          // Reset form
          setSingerName("");
          setSelectedSongId("");
        }
      }
    } catch (err) {
      setError("Failed to add to queue. Please try again.");
    }
  };

  // Handle removing from queue
  const handleRemoveFromQueue = async (id: string) => {
    try {
      const response = await removeFromQueue(id);

      if (response.data && response.data.success) {
        // Remove from queue state
        queueDispatch({ type: "REMOVE_FROM_QUEUE", payload: id });
      }
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
        {queueState.currentItem && (
          <div
            className="rounded-lg p-4 mb-6"
            style={{
              backgroundColor: colors.lemonChiffon,
              color: colors.russet,
            }}
          >
            <h2
              className="font-medium mb-3"
              style={{ color: colors.orangePeel }}
            >
              Now Playing
            </h2>
            <div className="flex items-center">
              <div
                className="h-16 w-16 rounded-md flex items-center justify-center mr-4"
                style={{ backgroundColor: `${colors.orangePeel}20` }}
              >
                {queueState.currentItem.song.coverArt ? (
                  <img
                    src={queueState.currentItem.song.coverArt}
                    alt={queueState.currentItem.song.title}
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
                  {queueState.currentItem.song.title}
                </h3>
                <p className="opacity-75">
                  {queueState.currentItem.song.artist}
                </p>
                <p className="text-sm mt-1" style={{ color: colors.darkCyan }}>
                  Singer: {queueState.currentItem.singer}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Queue list */}
        <h2 className="font-medium mb-2" style={{ color: colors.orangePeel }}>
          Up Next
        </h2>
        <div
          className="rounded-lg overflow-hidden mb-6"
          style={{
            backgroundColor: `${colors.lemonChiffon}20`,
            backdropFilter: "blur(8px)",
            border: `1px solid ${colors.orangePeel}40`,
          }}
        >
          {isLoading ? (
            <div
              className="p-6 text-center"
              style={{ color: colors.lemonChiffon }}
            >
              Loading queue...
            </div>
          ) : (
            <QueueList
              items={queueState.items}
              onRemove={handleRemoveFromQueue}
              emptyMessage="No singers in the queue"
            />
          )}
        </div>

        {/* Add to queue form */}
        <div
          className="rounded-lg p-4"
          style={{
            backgroundColor: colors.lemonChiffon,
            color: colors.russet,
          }}
        >
          <h3 className="font-medium mb-3">Add Yourself to Queue</h3>

          {error && (
            <div
              className="mb-3 p-2 rounded text-sm"
              style={{
                backgroundColor: `${colors.rust}20`,
                color: colors.rust,
              }}
            >
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <input
              type="text"
              placeholder="Your Name"
              className="border rounded px-3 py-2 focus:outline-none"
              style={{
                backgroundColor: `${colors.lemonChiffon}80`,
                borderColor: colors.orangePeel,
                color: colors.russet,
              }}
              value={singerName}
              onChange={handleSingerNameChange}
            />
            <select
              className="border rounded px-3 py-2 focus:outline-none"
              style={{
                backgroundColor: `${colors.lemonChiffon}80`,
                borderColor: colors.orangePeel,
                color: colors.russet,
              }}
              value={selectedSongId}
              onChange={handleSongSelection}
            >
              <option value="">Select a Song</option>
              {songsState.songs
                .filter((song) => song.status === "processed")
                .map((song) => (
                  <option key={song.id} value={song.id}>
                    {song.title} - {song.artist}
                  </option>
                ))}
            </select>
          </div>
          <button
            className="w-full py-2 rounded transition-colors hover:opacity-90"
            style={{
              backgroundColor: colors.orangePeel,
              color: colors.russet,
              border: `1px solid ${colors.lemonChiffon}`,
            }}
            onClick={handleAddToQueue}
          >
            Add to Queue
          </button>
        </div>
      </div>
    </AppLayout>
  );
};

export default QueuePage;
