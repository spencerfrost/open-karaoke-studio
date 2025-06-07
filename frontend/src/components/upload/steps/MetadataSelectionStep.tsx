// frontend/src/components/upload/steps/MetadataSelectionStep.tsx
import { useState } from "react";
import { Search, Loader2 } from "lucide-react";
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
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Skeleton } from "@/components/ui/skeleton";
import { MetadataOption } from "@/hooks/useYoutube";

interface MetadataSelectionStepProps {
  metadataOptions: MetadataOption[];
  selectedMetadata: MetadataOption | null;
  isSearching: boolean;
  initialMetadata: {
    artist: string;
    title: string;
    album: string;
  };
  onMetadataSelect: (metadata: MetadataOption) => void;
  onConfirm: () => void;
  onSkip: () => void;
  onResearch: (query: { artist: string; title: string; album: string; sortBy?: string }) => void;
}

export function MetadataSelectionStep({
  metadataOptions,
  selectedMetadata,
  isSearching,
  initialMetadata,
  onMetadataSelect,
  onConfirm,
  onSkip,
  onResearch,
}: MetadataSelectionStepProps) {
  const [showResearch, setShowResearch] = useState(false);
  const [researchArtist, setResearchArtist] = useState("");
  const [researchTitle, setResearchTitle] = useState("");
  const [researchAlbum, setResearchAlbum] = useState("");
  const [sortBy, setSortBy] = useState("relevance");

  const handleResearch = () => {
    onResearch({
      artist: researchArtist.trim(),
      title: researchTitle.trim(),
      album: researchAlbum.trim(),
    });
    setShowResearch(false);
  };

  const handleNoneOfThese = () => {
    setShowResearch(true);
    setResearchArtist(initialMetadata.artist);
    setResearchTitle(initialMetadata.title);
    setResearchAlbum(initialMetadata.album);
  };

  if (showResearch) {
    return (
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Search for Metadata</CardTitle>
            <CardDescription>
              Try more specific search terms. Include the album name or use the
              exact artist and song title to find the right release.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="space-y-3">
              <div>
                <Label htmlFor="research-artist">Artist</Label>
                <Input
                  id="research-artist"
                  value={researchArtist}
                  onChange={(e) => setResearchArtist(e.target.value)}
                  placeholder="Artist name"
                />
              </div>

              <div>
                <Label htmlFor="research-title">Title</Label>
                <Input
                  id="research-title"
                  value={researchTitle}
                  onChange={(e) => setResearchTitle(e.target.value)}
                  placeholder="Song title"
                />
              </div>

              <div>
                <Label htmlFor="research-album">Album</Label>
                <Input
                  id="research-album"
                  value={researchAlbum}
                  onChange={(e) => setResearchAlbum(e.target.value)}
                  placeholder="Album name (optional)"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-between">
          <Button variant="outline" onClick={() => setShowResearch(false)}>
            Back
          </Button>
          <Button
            onClick={handleResearch}
            disabled={
              !researchArtist.trim() || !researchTitle.trim() || isSearching
            }
          >
            {isSearching ? (
              <>
                <Search className="h-4 w-4 mr-2 animate-spin" />
                Searching...
              </>
            ) : (
              <>
                <Search className="h-4 w-4 mr-2" />
                Search Metadata
              </>
            )}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 flex flex-col overflow-hidden">
      <Card className="flex flex-col max-h-[65vh] overflow-y-auto">
        <CardHeader>
          <CardTitle>Available Metadata</CardTitle>
          <CardDescription>
            Select the correct album and artist information for your song. If
            you don't find the right match, you can search again.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isSearching && metadataOptions.length === 0 ? (
            // Loading state
            <div className="space-y-4">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-4">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Searching for metadata...</span>
              </div>
              {[1, 2, 3].map((index) => (
                <div
                  key={index}
                  className="border-b border-muted pb-2 last:border-0"
                >
                  <div className="flex items-center space-x-2">
                    <Skeleton className="h-4 w-4 rounded-full" />
                    <div className="space-y-2 flex-1">
                      <div className="flex items-center space-x-2">
                        <Skeleton className="h-4 w-32" />
                        <span className="text-muted-foreground">-</span>
                        <Skeleton className="h-4 w-12" />
                      </div>
                      <Skeleton className="h-3 w-48" />
                      <Skeleton className="h-3 w-24" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : metadataOptions.length > 0 ? (
            <RadioGroup
              value={
                selectedMetadata
                  ? selectedMetadata.id ||
                    `metadata-${metadataOptions.findIndex((m) => m === selectedMetadata)}`
                  : ""
              }
              onValueChange={(value) => {
                // First try to find by id
                let metadata = metadataOptions.find(
                  (m) => m.id === value
                );

                // If not found, it might be a fallback index-based value
                if (!metadata && value.startsWith("metadata-")) {
                  const index = parseInt(value.split("-")[1]);
                  metadata = metadataOptions[index];
                }

                if (metadata) onMetadataSelect(metadata);
              }}
            >
              {metadataOptions.map((metadata, index) => {
                const radioValue =
                  metadata.id || `metadata-${index}`;
                return (
                  <div
                    key={radioValue}
                    className="border-b border-muted pb-2 last:border-0"
                  >
                    <div className="flex items-center space-x-2">
                      <RadioGroupItem
                        value={radioValue}
                        id={`metadata-${index}`}
                      />
                      <label
                        htmlFor={`metadata-${index}`}
                        className="text-sm font-medium cursor-pointer"
                      >
                        <div className="ml-6 text-xs text-muted-foreground space-y-1">
                          <div className="font-semibold flex items-center space-x-1">
                            <div className="text-sm">
                              {metadata.title} by {metadata.artist}
                            </div>
                            <div className="">-</div>
                            <div className="font-semibold italic">
                              {metadata.year}
                            </div>
                          </div>
                          {metadata.album && (
                            <div>
                              Album:{" "}
                              <span className="font-semibold">
                                {metadata.album}
                              </span>
                            </div>
                          )}
                          {metadata.genre && (
                            <div>
                              Genre:{" "}
                              <span className="font-semibold">
                                {metadata.genre}
                              </span>
                            </div>
                          )}
                        </div>
                      </label>
                    </div>
                  </div>
                );
              })}
            </RadioGroup>
          ) : (
            <div className="text-center text-muted-foreground py-8">
              No metadata found for this song.
            </div>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-between flex-shrink-0">
        <div className="space-x-2">
          <Button
            variant="outline"
            onClick={handleNoneOfThese}
            disabled={isSearching}
          >
            None of these
          </Button>
          <Button variant="outline" onClick={onSkip} disabled={isSearching}>
            Skip metadata
          </Button>
        </div>
        <Button onClick={onConfirm} disabled={!selectedMetadata || isSearching}>
          {isSearching ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Loading...
            </>
          ) : (
            "Confirm & Finish"
          )}
        </Button>
      </div>
    </div>
  );
}
