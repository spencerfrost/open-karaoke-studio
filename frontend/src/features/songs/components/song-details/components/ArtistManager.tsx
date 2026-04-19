import React, { useState } from "react";
import { Plus, XCircle } from "lucide-react";
import { SongArtist } from "@/types/Song";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ArtistManagerProps {
  primaryArtist: string;
  featuredArtists: SongArtist[];
  onPrimaryChange: (value: string) => void;
  onFeaturedChange: (artists: SongArtist[]) => void;
}

export const ArtistManager: React.FC<ArtistManagerProps> = ({
  primaryArtist,
  featuredArtists,
  onPrimaryChange,
  onFeaturedChange,
}) => {
  const [showAddInput, setShowAddInput] = useState(false);
  const [addInputValue, setAddInputValue] = useState("");

  const handleRemoveFeatured = (id: number) => {
    onFeaturedChange(featuredArtists.filter((a) => a.id !== id));
  };

  const handleConfirmAdd = () => {
    const trimmed = addInputValue.trim();
    if (!trimmed) return;
    onFeaturedChange([
      ...featuredArtists,
      { id: Date.now(), name: trimmed, role: "featured" },
    ]);
    setAddInputValue("");
    setShowAddInput(false);
  };

  const handleAddKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleConfirmAdd();
    } else if (e.key === "Escape") {
      setAddInputValue("");
      setShowAddInput(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="primary-artist">Primary Artist</Label>
        <Input
          id="primary-artist"
          value={primaryArtist}
          onChange={(e) => onPrimaryChange(e.target.value)}
        />
      </div>

      <div className="space-y-1.5">
        <Label>Featured Artists</Label>
        <div className="flex flex-wrap gap-2">
          {featuredArtists.map((artist) => (
            <Badge key={artist.id} variant="secondary" className="gap-1 pr-1">
              {artist.name}
              <button
                type="button"
                onClick={() => handleRemoveFeatured(artist.id)}
                aria-label={`Remove ${artist.name}`}
                className="focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded-sm"
              >
                <XCircle size={14} className="text-muted-foreground hover:text-foreground transition-colors" />
              </button>
            </Badge>
          ))}

          {showAddInput ? (
            <div className="flex items-center gap-1">
              <Input
                autoFocus
                className="h-7 text-sm w-36"
                value={addInputValue}
                onChange={(e) => setAddInputValue(e.target.value)}
                onKeyDown={handleAddKeyDown}
                placeholder="Artist name"
              />
              <Button
                type="button"
                size="sm"
                variant="outline"
                className="h-7 text-xs px-2"
                onClick={handleConfirmAdd}
                disabled={!addInputValue.trim()}
              >
                Add
              </Button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowAddInput(true)}
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded-sm"
              aria-label="Add featured artist"
            >
              <Plus size={14} />
              Add
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
