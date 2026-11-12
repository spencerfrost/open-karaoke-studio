import React, { useMemo, useState } from "react";
import { Song, SongArtist } from "@/types/Song";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useLyricsLanguages,
  useRealignLyrics,
} from "@/hooks/api/useLyricsAlignment";
import { useSongs } from "@/hooks/api/useSongs";
import { toast } from "sonner";
import { createLogger } from "@/lib/logger";
import { ArtistManager } from "../components/ArtistManager";

const logger = createLogger("component:DetailsTab");

// Select items can't have an empty value; this stands for "no stored language".
const DETECT_LANGUAGE = "detect";
const languageNames = new Intl.DisplayNames(["en"], { type: "language" });

const languageName = (code: string) => languageNames.of(code) ?? code;

// "+3.2 dB" / "-6.2 dB" / "0.0 dB"
const formatSignedDb = (db: number) =>
  `${Number(db.toFixed(1)) > 0 ? "+" : ""}${db.toFixed(1)} dB`;

interface DetailsTabProps {
  song: Song;
}

/** The credits as saved, or the artist line as the one artist for a song without any. */
const initialCredits = (song: Song): SongArtist[] =>
  song.artists && song.artists.length > 0
    ? song.artists
    : [{ id: -1, name: song.artist, role: "primary" }];

const creditsKey = (credits: SongArtist[]) =>
  JSON.stringify(credits.map((c) => [c.name, c.role]));

export const DetailsTab: React.FC<DetailsTabProps> = ({ song }) => {
  const { useUpdateSong } = useSongs();
  const updateSongMutation = useUpdateSong();
  const realignLyricsMutation = useRealignLyrics();
  const { data: languageCodes } = useLyricsLanguages();

  const [title, setTitle] = useState(song.title);
  const [album, setAlbum] = useState(song.album ?? "");
  const [showName, setShowName] = useState(song.showName ?? "");
  const [year, setYear] = useState(song.year?.toString() ?? "");
  const [language, setLanguage] = useState(song.language ?? DETECT_LANGUAGE);
  const [credits, setCredits] = useState<SongArtist[]>(() =>
    initialCredits(song),
  );

  const languageOptions = useMemo(
    () =>
      (languageCodes ?? [])
        .map((code) => ({ code, name: languageName(code) }))
        .sort((a, b) => a.name.localeCompare(b.name)),
    [languageCodes],
  );

  const handleSave = () => {
    // Only a changed list is sent: saving the credits confirms them.
    const creditsChanged =
      creditsKey(credits) !== creditsKey(initialCredits(song));

    logger.debug("Saving song metadata", {
      id: song.id,
      title,
      creditsChanged,
    });

    updateSongMutation.mutate(
      {
        id: song.id,
        title,
        album: album || undefined,
        // An empty string clears it and keeps the song out of every show
        showName,
        year: year ? parseInt(year) : undefined,
        ...(creditsChanged && { artists: credits }),
        // An empty string clears it, so it's detected from the vocals again
        language: language === DETECT_LANGUAGE ? "" : language,
      },
      {
        onSuccess: () => {
          const languageChanged =
            language !== (song.language ?? DETECT_LANGUAGE);
          if (!languageChanged) {
            toast.success("Saved");
            return;
          }
          // The lyrics were timed in the old language; time them again.
          realignLyricsMutation.mutate(song.id, {
            onSuccess: () => toast.success("Saved. Re-timing the lyrics…"),
            onError: () =>
              toast.error("Saved, but the lyrics couldn't be re-timed"),
          });
        },
        onError: () => toast.error("Failed to save"),
      },
    );
  };

  const capitalize = (value: string) =>
    value.charAt(0).toUpperCase() + value.slice(1);

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="song-title">Title</Label>
          <Input
            id="song-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="song-album">Album</Label>
          <Input
            id="song-album"
            value={album}
            onChange={(e) => setAlbum(e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="song-show-name">Show Name</Label>
          <Input
            id="song-show-name"
            value={showName}
            onChange={(e) => setShowName(e.target.value)}
            placeholder="Musical or soundtrack, e.g. Wicked"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="song-year">Year</Label>
          <Input
            id="song-year"
            type="number"
            min="1800"
            max="2100"
            value={year}
            onChange={(e) => setYear(e.target.value)}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="song-language">Sung language</Label>
          <Select value={language} onValueChange={setLanguage}>
            <SelectTrigger id="song-language">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={DETECT_LANGUAGE}>
                Detect from the vocals
              </SelectItem>
              {/* Keep the stored language selectable while the list loads */}
              {languageOptions.length === 0 && song.language && (
                <SelectItem value={song.language}>
                  {languageName(song.language)}
                </SelectItem>
              )}
              {languageOptions.map(({ code, name }) => (
                <SelectItem key={code} value={code}>
                  {name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            The lyrics are timed to the singing in this language.
          </p>
        </div>

        <ArtistManager credits={credits} onChange={setCredits} />

        <Button
          className="w-full"
          onClick={handleSave}
          disabled={updateSongMutation.isPending}
        >
          {updateSongMutation.isPending ? "Saving…" : "Save"}
        </Button>
      </div>

      <div>
        <p className="text-sm font-medium text-muted-foreground mb-2">
          Song Identity
        </p>
        <div>
          {song.acoustidFingerprintStatus && (
            <div className="flex justify-between text-sm py-1 border-b">
              <span className="text-muted-foreground">Fingerprint</span>
              <span>
                {capitalize(song.acoustidFingerprintStatus)}
                {song.acoustidScore != null &&
                  ` (${Math.round(song.acoustidScore * 100)}%)`}
              </span>
            </div>
          )}

          <div className="flex justify-between text-sm py-1 border-b">
            <span className="text-muted-foreground">MusicBrainz</span>
            <span>{song.musicbrainzRecordingId ?? "Not identified"}</span>
          </div>

          {song.engineType && (
            <div className="flex justify-between text-sm py-1 border-b">
              <span className="text-muted-foreground">Engine</span>
              <span>{capitalize(song.engineType)}</span>
            </div>
          )}

          {song.loudnessLufs != null && (
            <div className="flex justify-between text-sm py-1 border-b">
              <span className="text-muted-foreground">Loudness</span>
              <span>
                {song.loudnessLufs.toFixed(1)} LUFS
                {song.truePeakDbtp != null &&
                  ` · peak ${song.truePeakDbtp.toFixed(1)} dBTP`}
              </span>
            </div>
          )}

          {song.gainDb != null && (
            <div className="flex justify-between text-sm py-1 border-b">
              <span className="text-muted-foreground">Volume correction</span>
              <span>{formatSignedDb(song.gainDb)}</span>
            </div>
          )}

          {song.source && (
            <div className="flex justify-between text-sm py-1 border-b">
              <span className="text-muted-foreground">Source</span>
              <span>{capitalize(song.source)}</span>
            </div>
          )}

          {song.videoId && (
            <div className="flex justify-between text-sm py-1 last:border-b-0">
              <span className="text-muted-foreground">Video ID</span>
              <span className="font-mono text-xs">{song.videoId}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
