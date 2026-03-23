import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { createLogger } from "@/lib/logger";
import { Song } from "@/types/Song";
import { SongAudioPreview } from "@/features/songs/components/song-card/SongAudioPreview";
import FileUpload from "@/features/songs/components/upload/FileUpload";
import { useYoutubeMusicSearch } from "@/hooks/api/useYoutubeMusic";
import { uploadFile } from "@/hooks/api/useApi";
import { YoutubeMusicSearchResult } from "@/types/Youtube";

const logger = createLogger("component:SongActionPanel");

type ActiveAction =
  | "edit"
  | "fingerprint"
  | "musicbrainz"
  | "replace-yt"
  | "replace-upload"
  | null;

interface FingerprintCandidate {
  score: number;
  recordingId: string;
  title: string;
  artist: string;
}

interface SongActionPanelProps {
  song: Song;
  onDone: () => void;
}

export const SongActionPanel: React.FC<SongActionPanelProps> = ({
  song,
  onDone,
}) => {
  const { token } = useAuthStore();
  const queryClient = useQueryClient();
  const [activeAction, setActiveAction] = useState<ActiveAction>(null);

  const invalidateAndDone = () => {
    queryClient.invalidateQueries({ queryKey: ["admin-acoustid-songs"] });
    onDone();
  };

  const toggle = (action: ActiveAction) => {
    setActiveAction((prev) => (prev === action ? null : action));
  };

  const deleteMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/songs/${song.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail ?? "Failed to delete song");
      }
    },
    onSuccess: () => {
      toast.success("Song deleted");
      queryClient.invalidateQueries({ queryKey: ["admin-acoustid-songs"] });
      queryClient.invalidateQueries({ queryKey: ["songs"] });
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const skipMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/songs/${song.id}/skip-fingerprint`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail ?? "Failed to skip song");
      }
    },
    onSuccess: () => {
      toast.success("Song skipped");
      queryClient.invalidateQueries({ queryKey: ["admin-acoustid-songs"] });
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-4">
      {/* Action buttons */}
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant={activeAction === "fingerprint" ? "default" : "outline"}
          onClick={() => toggle("fingerprint")}
        >
          Lookup Fingerprint
        </Button>
        <Button
          size="sm"
          variant={activeAction === "musicbrainz" ? "default" : "outline"}
          onClick={() => toggle("musicbrainz")}
        >
          Search MusicBrainz
        </Button>
        <Button
          size="sm"
          variant={activeAction === "edit" ? "default" : "outline"}
          onClick={() => toggle("edit")}
        >
          Edit Metadata
        </Button>
        <Button
          size="sm"
          variant={activeAction === "replace-yt" ? "default" : "outline"}
          onClick={() => toggle("replace-yt")}
        >
          Replace from YouTube Music
        </Button>
        <Button
          size="sm"
          variant={activeAction === "replace-upload" ? "default" : "outline"}
          onClick={() => toggle("replace-upload")}
        >
          Upload MP3
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => skipMutation.mutate()}
          disabled={skipMutation.isPending}
        >
          {skipMutation.isPending ? "Skipping..." : "Skip"}
        </Button>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button size="sm" variant="destructive">
              Delete Song
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete song?</AlertDialogTitle>
              <AlertDialogDescription>
                This will permanently delete &ldquo;{song.title}&rdquo; and all
                associated audio files. This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {deleteMutation.isPending ? "Deleting..." : "Delete"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      {/* Edit metadata panel */}
      {activeAction === "edit" && (
        <EditMetadataPanel song={song} onDone={invalidateAndDone} />
      )}

      {/* Fingerprint lookup panel */}
      {activeAction === "fingerprint" && (
        <FingerprintLookupPanel song={song} onDone={invalidateAndDone} />
      )}

      {/* MusicBrainz search panel */}1
      {activeAction === "musicbrainz" && (
        <MusicBrainzSearchPanel song={song} onDone={invalidateAndDone} />
      )}

      {/* YouTube Music replace panel */}
      {activeAction === "replace-yt" && (
        <YouTubeMusicReplacePanel song={song} onDone={invalidateAndDone} />
      )}

      {/* Upload replace panel */}
      {activeAction === "replace-upload" && (
        <UploadReplacePanel song={song} onDone={invalidateAndDone} />
      )}

      {/* Audio preview — always visible */}
      <div className="pt-1 border-t">
        <SongAudioPreview songId={song.id} />
      </div>
    </div>
  );
};

// ─── Edit Metadata ───────────────────────────────────────────────────────────

const EditMetadataPanel: React.FC<ReplacePanelProps> = ({ song, onDone }) => {
  const { token } = useAuthStore();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(song.title ?? "");
  const [artist, setArtist] = useState(song.artist ?? "");
  const [album, setAlbum] = useState(song.album ?? "");

  const saveMutation = useMutation({
    mutationFn: async () => {
      const body: Record<string, string> = {};
      if (title.trim()) body.title = title.trim();
      if (artist.trim()) body.artist = artist.trim();
      body.album = album.trim(); // allow clearing album
      const res = await fetch(`/api/songs/${song.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail ?? "Failed to save changes");
      }
      return res.json();
    },
    onSuccess: () => {
      toast.success("Metadata saved");
      queryClient.invalidateQueries({ queryKey: ["admin-acoustid-songs"] });
      queryClient.invalidateQueries({ queryKey: ["songs"] });
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-3 pt-1">
      <div className="space-y-2">
        <div>
          <label className="text-xs font-medium text-muted-foreground">Title</label>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Song title"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground">Artist</label>
          <Input
            value={artist}
            onChange={(e) => setArtist(e.target.value)}
            placeholder="Artist name"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-muted-foreground">Album</label>
          <Input
            value={album}
            onChange={(e) => setAlbum(e.target.value)}
            placeholder="Album name (optional)"
          />
        </div>
      </div>
      <Button
        size="sm"
        onClick={() => saveMutation.mutate()}
        disabled={saveMutation.isPending || !title.trim() || !artist.trim()}
      >
        {saveMutation.isPending ? "Saving..." : "Save Changes"}
      </Button>
    </div>
  );
};

// ─── Fingerprint Lookup ───────────────────────────────────────────────────────

const FingerprintLookupPanel: React.FC<ReplacePanelProps> = ({
  song,
  onDone,
}) => {
  const { token } = useAuthStore();
  const queryClient = useQueryClient();
  const [candidates, setCandidates] = useState<FingerprintCandidate[] | null>(null);
  const [selected, setSelected] = useState<FingerprintCandidate | null>(null);

  const lookupMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch(`/api/songs/${song.id}/fingerprint/lookup`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error(err?.detail ?? "Fingerprint lookup failed");
      }
      return res.json() as Promise<{ candidates: FingerprintCandidate[] }>;
    },
    onSuccess: (data) => {
      setCandidates(data.candidates);
      logger.info("fingerprint lookup: %d candidates for song %s", data.candidates.length, song.id);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const applyMutation = useMutation({
    mutationFn: async (candidate: FingerprintCandidate) => {
      const res = await fetch(`/api/songs/${song.id}/fingerprint/apply`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          recording_id: candidate.recordingId,
          title: candidate.title,
          artist: candidate.artist,
          score: candidate.score,
        }),
      });
      if (!res.ok) throw new Error("Failed to apply candidate");
      return res.json();
    },
    onSuccess: (_data, candidate) => {
      toast.success(`Applied: "${candidate.title}" by ${candidate.artist}`);
      queryClient.invalidateQueries({ queryKey: ["admin-acoustid-songs"] });
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="space-y-3">
      {candidates === null ? (
        <Button
          size="sm"
          variant="outline"
          disabled={lookupMutation.isPending}
          onClick={() => lookupMutation.mutate()}
        >
          {lookupMutation.isPending ? "Running fingerprint..." : "Run Lookup"}
        </Button>
      ) : candidates.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No AcoustID matches found for this audio.
        </p>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            {candidates.length} candidate{candidates.length !== 1 ? "s" : ""} found — click to select
          </p>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {candidates.map((c) => (
              <div
                key={c.recordingId}
                onClick={() => setSelected(c)}
                className={`flex items-center gap-3 p-2 rounded cursor-pointer transition-colors ${
                  selected?.recordingId === c.recordingId
                    ? "bg-primary/20 border border-primary/40"
                    : "hover:bg-muted/50 border border-transparent"
                }`}
              >
                <span
                  className={`text-xs font-mono font-semibold shrink-0 w-10 text-right ${
                    c.score >= 0.85
                      ? "text-green-500"
                      : c.score >= 0.5
                        ? "text-amber-500"
                        : "text-red-500"
                  }`}
                >
                  {Math.round(c.score * 100)}%
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{c.title}</p>
                  <p className="text-xs text-muted-foreground truncate">{c.artist}</p>
                </div>
              </div>
            ))}
          </div>
          {selected && (
            <Button
              size="sm"
              disabled={applyMutation.isPending}
              onClick={() => applyMutation.mutate(selected)}
            >
              {applyMutation.isPending ? "Applying..." : `Apply "${selected.title}"`}
            </Button>
          )}
        </div>
      )}
    </div>
  );
};

// ─── MusicBrainz Search ───────────────────────────────────────────────────────

interface MusicBrainzResult {
  score: number;
  recordingId: string;
  title: string;
  artist: string;
  album: string;
  releaseDate: string;
  duration: number | null;
}

const MusicBrainzSearchPanel: React.FC<ReplacePanelProps> = ({
  song,
  onDone,
}) => {
  const { token } = useAuthStore();
  const queryClient = useQueryClient();
  const initialQuery = [
    song.title && `recording:"${song.title}"`,
    song.artist && `artist:"${song.artist}"`,
  ]
    .filter(Boolean)
    .join(" AND ");
  const [query, setQuery] = useState(initialQuery);
  const [debouncedQuery, setDebouncedQuery] = useState(initialQuery);
  const [selected, setSelected] = useState<MusicBrainzResult | null>(null);

  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleQueryChange = (value: string) => {
    setQuery(value);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setDebouncedQuery(value), 400);
  };

  const { data, isFetching } = useQuery<{ results: MusicBrainzResult[] }>({
    queryKey: ["musicbrainz-search", debouncedQuery],
    queryFn: async () => {
      const res = await fetch(
        `/api/musicbrainz/search?query=${encodeURIComponent(debouncedQuery)}&limit=15`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!res.ok) throw new Error("MusicBrainz search failed");
      return res.json();
    },
    enabled: !!debouncedQuery,
    staleTime: 60_000,
  });

  const applyMutation = useMutation({
    mutationFn: async (candidate: MusicBrainzResult) => {
      const res = await fetch(`/api/songs/${song.id}/fingerprint/apply`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          recording_id: candidate.recordingId,
          title: candidate.title,
          artist: candidate.artist,
          score: candidate.score,
        }),
      });
      if (!res.ok) throw new Error("Failed to apply recording");
      return res.json();
    },
    onSuccess: (_data, candidate) => {
      toast.success(`Applied: "${candidate.title}" by ${candidate.artist}`);
      queryClient.invalidateQueries({ queryKey: ["admin-acoustid-songs"] });
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const results = data?.results ?? [];

  return (
    <div className="space-y-3">
      <Input
        value={query}
        onChange={(e) => handleQueryChange(e.target.value)}
        placeholder="Search MusicBrainz..."
        className="h-8 text-sm"
      />

      {isFetching && (
        <p className="text-xs text-muted-foreground">Searching...</p>
      )}

      {results.length > 0 && (
        <div className="space-y-1 max-h-64 overflow-y-auto">
          {results.map((r) => (
            <div
              key={r.recordingId}
              onClick={() => setSelected(r)}
              className={`flex items-center gap-3 p-2 rounded cursor-pointer transition-colors ${
                selected?.recordingId === r.recordingId
                  ? "bg-primary/20 border border-primary/40"
                  : "hover:bg-muted/50 border border-transparent"
              }`}
            >
              <span
                className={`text-xs font-mono font-semibold shrink-0 w-10 text-right ${
                  r.score >= 0.85
                    ? "text-green-500"
                    : r.score >= 0.5
                      ? "text-amber-500"
                      : "text-red-500"
                }`}
              >
                {Math.round(r.score * 100)}%
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{r.title}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {r.artist}
                  {r.album ? ` · ${r.album}` : ""}
                  {r.releaseDate ? ` (${r.releaseDate.slice(0, 4)})` : ""}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {selected && (
        <Button
          size="sm"
          disabled={applyMutation.isPending}
          onClick={() => applyMutation.mutate(selected)}
        >
          {applyMutation.isPending
            ? "Applying..."
            : `Apply "${selected.title}"`}
        </Button>
      )}
    </div>
  );
};

// ─── YouTube Music Replace ────────────────────────────────────────────────────

interface ReplacePanelProps {
  song: Song;
  onDone: () => void;
}

interface ValidationResult {
  validated: boolean;
  acoustidStatus: string;
  acoustidScore: number | null;
  musicbrainzId: string | null;
  title: string | null;
  artist: string | null;
  message: string;
}

const YouTubeMusicReplacePanel: React.FC<ReplacePanelProps> = ({
  song,
  onDone,
}) => {
  const { token } = useAuthStore();
  const [query, setQuery] = useState(`${song.artist} ${song.title}`);
  const [debouncedQuery, setDebouncedQuery] = useState(query);
  const [selected, setSelected] = useState<YoutubeMusicSearchResult | null>(
    null,
  );
  const [validation, setValidation] = useState<ValidationResult | null>(null);

  // Simple debounce via timeout ref
  const timeoutRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleQueryChange = (value: string) => {
    setQuery(value);
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setDebouncedQuery(value), 400);
  };

  const { data, isFetching } = useYoutubeMusicSearch(debouncedQuery, !!debouncedQuery);
  const songs = data?.songs ?? [];

  const validateMutation = useMutation({
    mutationFn: async (result: YoutubeMusicSearchResult) => {
      const res = await fetch(`/api/songs/${song.id}/validate-youtube-replacement`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          video_id: result.videoId,
          title: result.title,
          artist: result.artist,
          engine_type: "three_track",
        }),
      });
      if (!res.ok) throw new Error("Validation request failed");
      return res.json() as Promise<ValidationResult>;
    },
    onSuccess: (result) => setValidation(result),
    onError: (e: Error) => toast.error(e.message),
  });

  const replaceMutation = useMutation({
    mutationFn: async (result: YoutubeMusicSearchResult) => {
      const res = await fetch(`/api/songs/${song.id}/replace-youtube`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          video_id: result.videoId,
          title: result.title,
          artist: result.artist,
          engine_type: "three_track",
        }),
      });
      if (!res.ok) throw new Error("Failed to start replacement");
      return res.json();
    },
    onSuccess: () => {
      toast.success("Replacement queued — full reprocessing started");
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const handleSelect = (result: YoutubeMusicSearchResult) => {
    setSelected(result);
    setValidation(null);
    validateMutation.mutate(result);
  };

  return (
    <div className="space-y-3">
      <Input
        value={query}
        onChange={(e) => handleQueryChange(e.target.value)}
        placeholder="Search YouTube Music..."
        className="h-8 text-sm"
      />

      {isFetching && (
        <p className="text-xs text-muted-foreground">Searching...</p>
      )}

      {songs.length > 0 && (
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {songs.map((result) => (
            <div
              key={result.videoId}
              onClick={() => handleSelect(result)}
              className={`flex items-center gap-3 p-2 rounded cursor-pointer transition-colors ${
                selected?.videoId === result.videoId
                  ? "bg-primary/20 border border-primary/40"
                  : "hover:bg-muted/50 border border-transparent"
              }`}
            >
              {result.thumbnails[0] && (
                <img
                  src={result.thumbnails[0].url}
                  alt=""
                  className="w-8 h-8 rounded object-cover shrink-0"
                />
              )}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{result.title}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {result.artist}
                  {result.duration ? ` · ${result.duration}` : ""}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {validateMutation.isPending && (
        <p className="text-xs text-muted-foreground">Checking AcoustID...</p>
      )}

      {validation && (
        <div
          className={`rounded border p-3 text-sm space-y-2 ${
            validation.validated
              ? "bg-green-500/10 border-green-500/30"
              : "bg-yellow-500/10 border-yellow-500/30"
          }`}
        >
          <p className={validation.validated ? "text-green-400" : "text-yellow-400"}>
            {validation.message}
          </p>
          {validation.acoustidStatus === "matched" && validation.title && (
            <p className="text-xs text-muted-foreground">
              Matched: <span className="text-foreground">{validation.title}</span>
              {" by "}
              <span className="text-foreground">{validation.artist}</span>
            </p>
          )}
          <div className="flex gap-2 pt-1">
            {validation.validated ? (
              <Button
                size="sm"
                disabled={replaceMutation.isPending}
                onClick={() => replaceMutation.mutate(selected!)}
              >
                {replaceMutation.isPending ? "Starting..." : "Confirm & Process"}
              </Button>
            ) : (
              <p className="text-xs text-muted-foreground italic">
                Try a different track, or use MusicBrainz to set metadata manually.
              </p>
            )}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => { setValidation(null); setSelected(null); }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Upload Replace ───────────────────────────────────────────────────────────

const UploadReplacePanel: React.FC<ReplacePanelProps> = ({ song, onDone }) => {
  const panelLogger = createLogger("component:UploadReplacePanel");
  const { token } = useAuthStore();
  const [file, setFile] = useState<File | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleFileChange = (f: File | null) => {
    setFile(f);
    setValidation(null);
  };

  const validateMutation = useMutation({
    mutationFn: async (audioFile: File) => {
      const formData = new FormData();
      formData.append("audio_file", audioFile);
      const res = await fetch(`/api/songs/${song.id}/validate-upload-replacement`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!res.ok) throw new Error("Validation request failed");
      return res.json() as Promise<ValidationResult>;
    },
    onSuccess: (result) => setValidation(result),
    onError: (e: Error) => toast.error(e.message),
  });

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    try {
      await uploadFile(`songs/${song.id}/replace-upload`, file, {
        engine_type: "three_track",
      });
      toast.success("Upload started — full reprocessing queued");
      onDone();
    } catch (e) {
      panelLogger.error("Upload failed", e);
      toast.error(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-3">
      <FileUpload value={file} onChange={handleFileChange} />

      {file && !validation && (
        <Button
          size="sm"
          variant="outline"
          disabled={validateMutation.isPending}
          onClick={() => validateMutation.mutate(file)}
        >
          {validateMutation.isPending ? "Checking AcoustID..." : "Check AcoustID Match"}
        </Button>
      )}

      {validation && (
        <div
          className={`rounded border p-3 text-sm space-y-2 ${
            validation.validated
              ? "bg-green-500/10 border-green-500/30"
              : "bg-yellow-500/10 border-yellow-500/30"
          }`}
        >
          <p className={validation.validated ? "text-green-400" : "text-yellow-400"}>
            {validation.message}
          </p>
          {validation.acoustidStatus === "matched" && validation.title && (
            <p className="text-xs text-muted-foreground">
              Matched: <span className="text-foreground">{validation.title}</span>
              {" by "}
              <span className="text-foreground">{validation.artist}</span>
            </p>
          )}
          <div className="flex gap-2 pt-1">
            {validation.validated ? (
              <Button size="sm" disabled={isUploading} onClick={handleUpload}>
                {isUploading ? "Uploading..." : "Confirm & Process"}
              </Button>
            ) : (
              <p className="text-xs text-muted-foreground italic">
                Try a different file, or use MusicBrainz to set metadata manually.
              </p>
            )}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => { setValidation(null); setFile(null); }}
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
