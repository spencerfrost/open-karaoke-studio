import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Song } from '@/types/Song';
import { useMetadata } from '@/hooks/api/useMetadata';
import {
  StepIndicator,
  SearchStep,
  SelectStep,
  ReviewStep
} from './metadata-edit';

interface MetadataEditContentProps {
  song: Song;
  onBack: () => void;
}

type Step = 'search' | 'select' | 'review';

const STEPS: { key: Step; label: string; step: number }[] = [
  { key: 'search', label: 'Search iTunes', step: 1 },
  { key: 'select', label: 'Select Result', step: 2 },
  { key: 'review', label: 'Review Changes', step: 3 }
];

export const MetadataEditContent: React.FC<MetadataEditContentProps> = ({
  song,
  onBack
}) => {
  const [currentStep, setCurrentStep] = useState<Step>('search');
  const [selectedResult, setSelectedResult] = useState<any | null>(null);
  const [searchArtist, setSearchArtist] = useState(song.artist || '');
  const [searchTitle, setSearchTitle] = useState(song.title || '');
  const [searchAlbum, setSearchAlbum] = useState(song.album || '');
  const [searchResults, setSearchResults] = useState<any[]>([]);

  const queryClient = useQueryClient();
  const { useSearchMetadata } = useMetadata();
  const searchMutation = useSearchMetadata();

  const updateSongMutation = useMutation({
    mutationFn: async (updates: Record<string, unknown>) => {
      const response = await fetch(`/api/songs/${song.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });
      
      if (!response.ok) {
        throw new Error('Failed to update song metadata');
      }
      
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['songs'] });
      queryClient.invalidateQueries({ queryKey: ['song', song.id] });
      onBack();
    },
  });

  const handleSearch = () => {
    const params = {
      artist: searchArtist,
      title: searchTitle,
      album: searchAlbum,
      limit: 10
    };

    searchMutation.mutate(params, {
      onSuccess: (results) => {
        setSearchResults(results);
        if (results.length > 0) {
          setCurrentStep('select');
        }
      }
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !searchMutation.isPending) {
      handleSearch();
    }
  };

  const handleSelectResult = (result: any) => {
    setSelectedResult(result);
    setCurrentStep('review');
  };

  const handleBackToSearch = () => {
    setCurrentStep('search');
  };

  const handleBackToSelect = () => {
    setCurrentStep('select');
  };

  const handleSave = async () => {
    if (!selectedResult) return;

    const updates: Partial<Song> = {
      title: selectedResult.trackName,
      artist: selectedResult.artistName,
      album: selectedResult.collectionName,
      genre: selectedResult.primaryGenreName,
      year: selectedResult.releaseYear ? selectedResult.releaseYear.toString() : undefined,
    };

    // Convert artwork URLs to the format expected by the backend (array of strings)
    const artworkUrls: string[] = [];
    if (selectedResult.artworkUrl60) artworkUrls.push(selectedResult.artworkUrl60);
    if (selectedResult.artworkUrl100) artworkUrls.push(selectedResult.artworkUrl100);
    if (selectedResult.artworkUrl600) {
      artworkUrls.push(selectedResult.artworkUrl600);
    } else if (selectedResult.artworkUrl100) {
      // Generate 600x600 version from 100x100
      artworkUrls.push(selectedResult.artworkUrl100.replace('100x100', '600x600'));
    }

    // Prepare updates for backend with proper types
    const updatesForBackend: Record<string, unknown> = {
      ...updates,
      itunesArtworkUrls: artworkUrls.length > 0 ? artworkUrls : undefined,
    };

    // Remove undefined values
    Object.keys(updatesForBackend).forEach(key => {
      if (updatesForBackend[key] === undefined) {
        delete updatesForBackend[key];
      }
    });

    updateSongMutation.mutate(updatesForBackend);
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 'search':
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
      
      case 'select':
        return (
          <SelectStep
            results={searchResults}
            onSelect={handleSelectResult}
            onBackToSearch={handleBackToSearch}
            isLoading={false}
            error={searchMutation.error}
          />
        );
      
      case 'review':
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
            isCompleted={STEPS.findIndex(s => s.key === currentStep) > STEPS.findIndex(s => s.key === step.key)}
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

      {/* Step Content */}
      <div className="min-h-[400px]">
        {renderStepContent()}
      </div>

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
