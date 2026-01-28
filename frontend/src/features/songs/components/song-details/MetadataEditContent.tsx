import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Song } from "@/types/Song";
import { useMetadata } from "@/hooks/api/useMetadata";
import { useSongs } from "@/hooks/api/useSongs";
import { ITunesSearchResult } from "@/hooks/useItunesSearch";
import {
  StepIndicator,
  SearchStep,
  SelectStep,
  ReviewStep,
} from "./metadata-edit";

interface MetadataEditContentProps {
  song: Song;
  onBack: () => void;
}

type Step = "search" | "select" | "review";

const STEPS: { key: Step; label: string; step: number }[] = [
  { key: "search", label: "Search iTunes", step: 1 },
  { key: "select", label: "Select Result", step: 2 },
  { key: "review", label: "Review Changes", step: 3 },
];

export const MetadataEditContent: React.FC<MetadataEditContentProps> = ({
  song,
  onBack,
}) => {
  const [currentStep, setCurrentStep] = useState<Step>("search");
  const [selectedResult, setSelectedResult] =
    useState<ITunesSearchResult | null>(null);
  const [searchArtist, setSearchArtist] = useState(song.artist || "");
  const [searchTitle, setSearchTitle] = useState(song.title || "");
  const [searchAlbum, setSearchAlbum] = useState(song.album || "");
  const [searchResults, setSearchResults] = useState<ITunesSearchResult[]>([]);

  const { useSearchMetadata, useLookupMetadata } = useMetadata();
  const searchMutation = useSearchMetadata();
  const lookupMutation = useLookupMetadata();

  const { useUpdateSong } = useSongs();
  const updateSongMutation = useUpdateSong();

  const handleSearch = () => {
    const params = {
      artist: searchArtist,
      title: searchTitle,
      album: searchAlbum,
      limit: 10,
    };

    searchMutation.mutate(params, {
      onSuccess: (response) => {
        // Transform backend results to ITunesSearchResult format
        const transformedResults: ITunesSearchResult[] = response.results.map(
          (result: any) => ({
            trackId: parseInt(result.metadataId || result.id),
            artistId: result.artistId,
            collectionId: result.albumId,
            trackName: result.title,
            artistName: result.artist,
            collectionName: result.album,
            primaryGenreName: result.genre,
            artworkUrl100: result.rawData?.artworkUrl100,
            artworkUrl60: result.rawData?.artworkUrl60,
            artworkUrl30: result.rawData?.artworkUrl30,
            releaseYear: result.releaseYear,
            releaseDate: result.releaseDate,
            trackNumber: result.trackNumber,
            discNumber: result.discNumber,
            trackExplicitness: result.explicit ? "explicit" : "notExplicit",
            previewUrl: result.previewUrl,
            isStreamable: result.isStreamable,
            trackTimeMillis: result.rawData?.trackTimeMillis,
            durationSeconds: result.rawData?.trackTimeMillis
              ? Math.floor(result.rawData.trackTimeMillis / 1000)
              : undefined,
          }),
        );

        setSearchResults(transformedResults);
        if (transformedResults.length > 0) {
          setCurrentStep("select");
        }
      },
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !searchMutation.isPending) {
      handleSearch();
    }
  };

  const handleSelectResult = (result: ITunesSearchResult) => {
    // Call lookup API to get comprehensive metadata
    lookupMutation.mutate(result.trackId, {
      onSuccess: (lookupData) => {
        // Transform lookup response to ITunesSearchResult with comprehensive data
        const comprehensiveResult: ITunesSearchResult = {
          ...result, // Keep search result data as fallback
          // Override with comprehensive lookup data
          trackName: lookupData.title || result.trackName,
          artistName: lookupData.artist || result.artistName,
          collectionName: lookupData.album || result.collectionName,
          primaryGenreName: lookupData.genre || result.primaryGenreName,

          // Artwork URLs (all sizes from lookup)
          artworkUrl30: lookupData.artworkUrl30,
          artworkUrl60: lookupData.artworkUrl60,
          artworkUrl100: lookupData.artworkUrl100,
          artworkUrl600: lookupData.artworkUrl600,

          // Track details
          trackNumber: lookupData.trackNumber,
          trackCount: lookupData.trackCount,
          discNumber: lookupData.discNumber,
          discCount: lookupData.discCount,
          trackTimeMillis: lookupData.trackTimeMillis,
          durationSeconds: lookupData.trackTimeMillis
            ? Math.floor(lookupData.trackTimeMillis / 1000)
            : undefined,

          // Release information
          releaseDate: lookupData.releaseDate,
          releaseYear: lookupData.releaseYear,
          releaseDateFormatted: lookupData.releaseDateFormatted,

          // Content advisory
          trackExplicitness: lookupData.trackExplicitness,
          collectionExplicitness: lookupData.collectionExplicitness,
          contentAdvisoryRating: lookupData.contentAdvisoryRating,

          // Pricing and availability
          trackPrice: lookupData.trackPrice,
          collectionPrice: lookupData.collectionPrice,
          currency: lookupData.currency,
          country: lookupData.country,
          isStreamable: lookupData.isStreamable,

          // URLs
          previewUrl: lookupData.previewUrl,
          artistViewUrl: lookupData.artistViewUrl,
          collectionViewUrl: lookupData.collectionViewUrl,
          trackViewUrl: lookupData.trackViewUrl,

          // Censored names
          trackCensoredName: lookupData.trackCensoredName,
          collectionCensoredName: lookupData.collectionCensoredName,

          // Additional metadata
          copyright: lookupData.copyright,
          description: lookupData.description,

          // Genre information
          primaryGenreId: lookupData.primaryGenreId,
          genreIds: lookupData.genreIds || [],
        };

        setSelectedResult(comprehensiveResult);
        setCurrentStep("review");
      },
      onError: (error) => {
        // If lookup fails, fall back to using search result
        console.error("Lookup failed, using search result:", error);
        setSelectedResult(result);
        setCurrentStep("review");
      },
    });
  };

  const handleBackToSearch = () => {
    setCurrentStep("search");
  };

  const handleBackToSelect = () => {
    setCurrentStep("select");
  };

  const handleSave = () => {
    if (!selectedResult) return;

    const updates: Partial<Song> = {
      title: selectedResult.trackName,
      artist: selectedResult.artistName,
      album: selectedResult.collectionName,
      genre: selectedResult.primaryGenreName,
      year: selectedResult.releaseYear,
    };

    // Artwork URLs - collect all available sizes
    const artworkUrls: string[] = [];
    if (selectedResult.artworkUrl30)
      artworkUrls.push(selectedResult.artworkUrl30);
    if (selectedResult.artworkUrl60)
      artworkUrls.push(selectedResult.artworkUrl60);
    if (selectedResult.artworkUrl100)
      artworkUrls.push(selectedResult.artworkUrl100);
    if (selectedResult.artworkUrl600)
      artworkUrls.push(selectedResult.artworkUrl600);

    // Prepare comprehensive updates for backend
    const updatesForBackend = {
      id: song.id,
      ...updates,

      // iTunes metadata
      itunesTrackId: selectedResult.trackId,
      itunesArtworkUrls: artworkUrls.length > 0 ? artworkUrls : undefined,
      itunesExplicit: selectedResult.trackExplicitness === "explicit",
      itunesPreviewUrl: selectedResult.previewUrl, // 30-sec preview for song identification

      // Release information
      releaseDate:
        selectedResult.releaseDateFormatted || selectedResult.releaseDate,

      // Duration (from our audio file, not iTunes)
      duration: selectedResult.durationSeconds,
    };

    // Remove undefined values
    const cleanedUpdates = Object.fromEntries(
      Object.entries(updatesForBackend).filter(([_, v]) => v !== undefined),
    );

    updateSongMutation.mutate(
      cleanedUpdates as Partial<Song> & { id: string },
      {
        onSuccess: () => {
          onBack();
        },
      },
    );
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case "search":
        return (
          <SearchStep
            searchArtist={searchArtist}
            setSearchArtist={setSearchArtist}
            searchTitle={searchTitle}
            setSearchTitle={setSearchTitle}
            searchAlbum={searchAlbum}
            setSearchAlbum={setSearchAlbum}
            onSearch={handleSearch}
            onKeyPress={handleKeyPress}
            isLoading={searchMutation.isPending}
            song={song}
          />
        );

      case "select":
        return (
          <SelectStep
            results={searchResults}
            onSelect={handleSelectResult}
            onBackToSearch={handleBackToSearch}
            isLoading={lookupMutation.isPending}
            error={searchMutation.error as Error | null}
          />
        );

      case "review":
        return selectedResult ? (
          <ReviewStep
            song={song}
            selectedResult={selectedResult}
            onSave={handleSave}
            onBack={handleBackToSelect}
            isLoading={updateSongMutation.isPending}
          />
        ) : null;

      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h3 className="text-lg font-semibold">Edit Metadata</h3>
        <p className="text-sm text-muted-foreground">
          Search iTunes for correct metadata and update your song information
        </p>
      </div>

      {/* Step Indicator */}
      <div className="flex items-center justify-center space-x-8">
        {STEPS.map((step) => (
          <StepIndicator
            key={step.key}
            step={step.step}
            title={step.label}
            isActive={currentStep === step.key}
            isCompleted={
              STEPS.findIndex((s) => s.key === currentStep) >
              STEPS.findIndex((s) => s.key === step.key)
            }
          />
        ))}
      </div>

      {/* Error Display */}
      {updateSongMutation.error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to update song metadata. Please try again.
          </AlertDescription>
        </Alert>
      )}

      {lookupMutation.error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to fetch comprehensive metadata from iTunes. Using basic
            search data instead.
          </AlertDescription>
        </Alert>
      )}

      {/* Step Content */}
      <div className="min-h-[400px]">{renderStepContent()}</div>

      {/* Navigation Footer */}
      <div className="flex justify-between pt-4 border-t">
        <Button
          variant="outline"
          onClick={onBack}
          disabled={updateSongMutation.isPending || searchMutation.isPending}
        >
          Cancel
        </Button>
      </div>
    </div>
  );
};
