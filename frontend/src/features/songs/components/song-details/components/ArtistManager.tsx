import React, { useState } from "react";
import { Plus, XCircle } from "lucide-react";
import { SongArtist } from "@/types/Song";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ArtistManagerProps {
  /** The song's credits, primaries first. */
  credits: SongArtist[];
  onChange: (credits: SongArtist[]) => void;
}

const CreditGroup: React.FC<{
  label: string;
  role: SongArtist["role"];
  credits: SongArtist[];
  /** The last primary can't be removed: a song needs one. */
  canRemove: boolean;
  onAdd: (name: string) => void;
  onRemove: (credit: SongArtist) => void;
}> = ({ label, role, credits, canRemove, onAdd, onRemove }) => {
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");

  const confirm = () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    onAdd(trimmed);
    setName("");
    setAdding(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      confirm();
    } else if (e.key === "Escape") {
      setName("");
      setAdding(false);
    }
  };

  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <div className="flex flex-wrap items-center gap-2">
        {credits.map((credit) => (
          <Badge key={credit.id} variant="secondary" className="gap-1 pr-1">
            {credit.name}
            {canRemove && (
              <button
                type="button"
                onClick={() => onRemove(credit)}
                aria-label={`Remove ${credit.name}`}
                className="focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring rounded-sm"
              >
                <XCircle
                  size={14}
                  className="text-muted-foreground hover:text-card-foreground transition-colors"
                />
              </button>
            )}
          </Badge>
        ))}

        {adding ? (
          <div className="flex items-center gap-1">
            <Input
              autoFocus
              className="h-7 text-sm w-36"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Artist name"
            />
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-7 text-xs px-2"
              onClick={confirm}
              disabled={!name.trim()}
            >
              Add
            </Button>
          </div>
        ) : (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs text-muted-foreground"
            onClick={() => setAdding(true)}
            aria-label={
              role === "primary" ? "Add an artist" : "Add a featured artist"
            }
          >
            <Plus size={14} />
            Add
          </Button>
        )}
      </div>
    </div>
  );
};

/**
 * The song's artists as a list: who it's by, and who it features. Saved as
 * given; the song's artist line is rebuilt from it ("A & B feat. C").
 */
export const ArtistManager: React.FC<ArtistManagerProps> = ({
  credits,
  onChange,
}) => {
  const primaries = credits.filter((c) => c.role === "primary");
  const featured = credits.filter((c) => c.role === "featured");

  const add = (name: string, role: SongArtist["role"]) => {
    // Negative ids stand in until the server gives the artist its own.
    const id = -Date.now();
    const added = { id, name, role };
    onChange(
      role === "primary"
        ? [...primaries, added, ...featured]
        : [...primaries, ...featured, added],
    );
  };
  const remove = (credit: SongArtist) =>
    onChange(credits.filter((c) => c !== credit));

  return (
    <div className="space-y-4">
      <CreditGroup
        label="Artist"
        role="primary"
        credits={primaries}
        canRemove={primaries.length > 1}
        onAdd={(name) => add(name, "primary")}
        onRemove={remove}
      />
      <CreditGroup
        label="Featuring"
        role="featured"
        credits={featured}
        canRemove
        onAdd={(name) => add(name, "featured")}
        onRemove={remove}
      />
    </div>
  );
};
