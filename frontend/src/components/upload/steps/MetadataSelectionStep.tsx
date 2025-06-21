// frontend/src/components/upload/steps/MetadataSelectionStep.tsx
import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { SearchForm, MetadataResults } from "@/components/forms";
import type { SearchFormData, MetadataOption } from "@/components/forms";

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
  onResearch: (query: {
    artist: string;
    title: string;
    album: string;
    sortBy?: string;
  }) => void;
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
            <CardTitle>Search for Metadata</CardTitle>
            <CardDescription>
              Try more specific search terms. Include the album name or use the
              exact artist and song title to find the right release.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <SearchForm
              initialValues={initialMetadata}
              onSearch={handleResearch}
              isLoading={isSearching}
              submitButtonText="Search Metadata"
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
          <CardTitle>Available Metadata</CardTitle>
          <CardDescription>
            Select the correct album and artist information for your song. If
            you don't find the right match, you can search again.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <MetadataResults
            options={metadataOptions}
            selectedOption={selectedMetadata}
            onSelectionChange={onMetadataSelect}
            isLoading={isSearching}
            autoSelectFirst={true}
            emptyMessage="No metadata found for this search"
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
            Skip Metadata
          </Button>
        </div>
        <Button onClick={onConfirm} disabled={!selectedMetadata}>
          Continue
        </Button>
      </div>
    </div>
  );
}
