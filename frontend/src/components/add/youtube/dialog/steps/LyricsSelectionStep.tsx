// frontend/src/components/upload/steps/LyricsSelectionStep.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SearchForm, LyricsResults } from "@/components/forms";
import type { SearchFormData } from "@/components/forms";
import type { LyricsOption } from "@/hooks/api/useLyrics";

interface LyricsSelectionStepProps {
  lyricsOptions: LyricsOption[];
  selectedLyrics: LyricsOption | null;
  videoDuration: number;
  isSearching: boolean;
  initialMetadata: {
    artist: string;
    title: string;
    album: string;
  };
  onLyricsSelect: (lyrics: LyricsOption) => void;
  onConfirm: () => void;
  onSkip: () => void;
  onResearch: (query: { artist: string; title: string; album: string }) => void;
}

export function LyricsSelectionStep({
  lyricsOptions,
  selectedLyrics,
  videoDuration,
  isSearching,
  initialMetadata,
  onLyricsSelect,
  onConfirm,
  onSkip,
  onResearch,
}: LyricsSelectionStepProps) {
  const [showResearch, setShowResearch] = useState(false);

  const handleResearch = (query: SearchFormData) => {
    onResearch({
      artist: query.artist,
      title: query.title,
      album: query.album,
    });
    setShowResearch(false);
  };

  const handleNoneOfThese = () => {
    setShowResearch(true);
  };

  if (showResearch) {
    return (
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle>Search for Lyrics</CardTitle>
            <CardDescription>
              Try more specific search terms or check the exact song title and
              artist to find better lyrics matches.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <SearchForm
              initialValues={initialMetadata}
              onSearch={handleResearch}
              isLoading={isSearching}
              submitButtonText="Search Lyrics"
              layout="vertical"
            />

            <div className="flex justify-between mt-6">
              <Button variant="outline" onClick={() => setShowResearch(false)}>
                Back
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4 flex flex-col overflow-hidden">
      <Card className="flex flex-col max-h-[65vh] overflow-y-auto">
        <CardHeader>
          <CardTitle>Available Lyrics</CardTitle>
          <CardDescription>
            Select the best lyrics match for your song. Duration matching helps
            identify the correct version.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <LyricsResults
            options={lyricsOptions}
            selectedOption={selectedLyrics}
            onSelectionChange={onLyricsSelect}
            isLoading={isSearching}
            youtubeDurationSeconds={videoDuration}
          />
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex justify-between">
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleNoneOfThese}>
            None of these
          </Button>
          <Button variant="outline" onClick={onSkip}>
            Skip Lyrics
          </Button>
        </div>
        <Button onClick={onConfirm} disabled={!selectedLyrics}>
          Continue
        </Button>
      </div>
    </div>
  );
}
