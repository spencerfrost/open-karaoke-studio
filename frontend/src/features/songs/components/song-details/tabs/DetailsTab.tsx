import React, { useState } from "react";
import { Song } from "@/types/Song";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSongs } from "@/hooks/api/useSongs";
import { BpmEditor } from "../BpmEditor";
import { Pencil, Check, X, Search } from "lucide-react";
import { toast } from "sonner";

interface DetailsTabProps {
  song: Song;
  onLaunchItunesSearch?: () => void;
}

type EditingField = "title" | "artist" | "album" | "genre" | "year" | null;

export const DetailsTab: React.FC<DetailsTabProps> = ({
  song,
  onLaunchItunesSearch,
}) => {
  const { useUpdateSong } = useSongs();
  const updateSongMutation = useUpdateSong();

  const [editingField, setEditingField] = useState<EditingField>(null);
  const [editValue, setEditValue] = useState("");

  const startEditing = (field: EditingField, currentValue: string) => {
    setEditingField(field);
    setEditValue(currentValue || "");
  };

  const cancelEditing = () => {
    setEditingField(null);
    setEditValue("");
  };

  const saveField = async () => {
    if (!editingField || !editValue.trim()) return;

    try {
      await updateSongMutation.mutateAsync({
        id: song.id,
        [editingField]: editValue.trim(),
      } as Partial<Song> & { id: string });
      toast.success(
        `${editingField.charAt(0).toUpperCase() + editingField.slice(1)} updated`,
      );
      setEditingField(null);
      setEditValue("");
    } catch {
      toast.error(`Failed to update ${editingField}`);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      saveField();
    } else if (e.key === "Escape") {
      cancelEditing();
    }
  };

  const renderEditableField = (
    field: EditingField,
    label: string,
    value: string | undefined,
    icon?: React.ReactNode,
  ) => {
    const isEditing = editingField === field;
    const displayValue = value || "Not set";

    return (
      <div className="flex items-center justify-between py-3 border-b last:border-b-0">
        <div className="flex items-center gap-2 flex-1">
          {icon}
          <div className="flex-1">
            <Label className="text-xs text-muted-foreground">{label}</Label>
            {isEditing ? (
              <div className="flex items-center gap-2 mt-1">
                <Input
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onKeyDown={handleKeyPress}
                  className="h-8 flex-1"
                  autoFocus
                />
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={saveField}
                  disabled={!editValue.trim() || updateSongMutation.isPending}
                  className="h-8 w-8 p-0"
                >
                  <Check size={16} />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={cancelEditing}
                  className="h-8 w-8 p-0"
                >
                  <X size={16} />
                </Button>
              </div>
            ) : (
              <p className="font-medium mt-1">{displayValue}</p>
            )}
          </div>
        </div>
        {!isEditing && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => startEditing(field, value || "")}
            className="h-8 w-8 p-0"
          >
            <Pencil size={14} />
          </Button>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* iTunes Search Helper */}
      {onLaunchItunesSearch && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Quick Update</CardTitle>
          </CardHeader>
          <CardContent>
            <Button
              variant="outline"
              onClick={onLaunchItunesSearch}
              className="w-full flex items-center gap-2"
            >
              <Search size={16} />
              Search iTunes for Metadata
            </Button>
            <p className="text-xs text-muted-foreground mt-2">
              Automatically fill in metadata from iTunes catalog
            </p>
          </CardContent>
        </Card>
      )}

      {/* Basic Information */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Basic Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-0">
          {renderEditableField("title", "Title", song.title)}
          {renderEditableField("artist", "Artist", song.artist)}
          {renderEditableField("album", "Album", song.album)}
          {renderEditableField("genre", "Genre", song.genre)}
          {renderEditableField("year", "Year", song.year?.toString())}
        </CardContent>
      </Card>

      {/* BPM */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Tempo</CardTitle>
        </CardHeader>
        <CardContent>
          <BpmEditor song={song} />
          <p className="text-xs text-muted-foreground mt-2">
            Used for count-in timing before lyrics start
          </p>
        </CardContent>
      </Card>

      {/* Vocal Range */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Vocal Range</CardTitle>
        </CardHeader>
        <CardContent>
          {song.vocalRangeLow || song.vocalRangeHigh ? (
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm">
                {song.vocalRangeLow ?? "?"} – {song.vocalRangeHigh ?? "?"}
              </span>
            </div>
          ) : (
            <span className="text-sm text-muted-foreground">Unknown</span>
          )}
          <p className="text-xs text-muted-foreground mt-2">
            Lowest and highest notes detected in the vocal track
          </p>
        </CardContent>
      </Card>

      {/* iTunes Metadata */}
      {song.itunesTrackId && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">iTunes Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Track ID</span>
              <span className="font-mono">{song.itunesTrackId}</span>
            </div>
            {song.itunesExplicit !== undefined && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Explicit</span>
                <span>{song.itunesExplicit ? "Yes" : "No"}</span>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Source Information */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Source Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Status</span>
            <span className="capitalize">{song.status}</span>
          </div>
          {song.source && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Source</span>
              <span className="capitalize">{song.source}</span>
            </div>
          )}
          {song.videoId && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">YouTube ID</span>
              <span className="font-mono text-xs">{song.videoId}</span>
            </div>
          )}
          {song.engineType && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">Audio Engine</span>
              <span className="capitalize">{song.engineType}</span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
