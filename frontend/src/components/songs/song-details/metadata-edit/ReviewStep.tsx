import React from 'react';
import { Song } from '@/types/Song';
import { ITunesSearchResult } from '@/hooks/useItunesSearch';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { ITunesResultCard } from './ITunesResultCard';
import { MetadataComparisonView } from './MetadataComparisonView';

interface ReviewStepProps {
  song: Song;
  selectedResult: ITunesSearchResult;
  onSave: () => Promise<void>;
  onBack: () => void;
  isLoading: boolean;
}

export const ReviewStep: React.FC<ReviewStepProps> = ({ 
  song, 
  selectedResult, 
  onSave, 
  onBack, 
  isLoading 
}) => {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Selected iTunes Release</CardTitle>
          <CardDescription>
            Review your selection and the changes that will be applied
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ITunesResultCard
            result={selectedResult}
            isSelected={true}
            onSelect={() => {}}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Metadata Changes</CardTitle>
          <CardDescription>
            Review the changes that will be applied to your song metadata
          </CardDescription>
        </CardHeader>
        <CardContent>
          <MetadataComparisonView
            currentSong={song}
            selectedResult={selectedResult}
          />
        </CardContent>
      </Card>

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Selection
        </Button>
        <Button onClick={onSave} disabled={isLoading}>
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Saving...
            </>
          ) : (
            'Apply iTunes Metadata'
          )}
        </Button>
      </div>
    </div>
  );
};
