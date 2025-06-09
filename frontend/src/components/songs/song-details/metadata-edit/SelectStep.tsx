import React from 'react';
import { ITunesSearchResult } from '@/hooks/useItunesSearch';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ITunesResultCard } from './ITunesResultCard';

interface SelectStepProps {
  results: ITunesSearchResult[];
  onSelect: (result: ITunesSearchResult) => void;
  onBackToSearch: () => void;
  isLoading: boolean;
  error: Error | null;
}

export const SelectStep: React.FC<SelectStepProps> = ({ 
  results, 
  onSelect, 
  onBackToSearch, 
  isLoading, 
  error 
}) => {
  return (
    <div className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to search iTunes: {error.message}
          </AlertDescription>
        </Alert>
      )}

      {results.length === 0 && !isLoading && (
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            No iTunes results found. 
            <Button variant="link" className="p-0 ml-1" onClick={onBackToSearch}>
              Try adjusting your search terms
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {results.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">iTunes Search Results</CardTitle>
            <CardDescription>
              Found {results.length} potential matches. Select the correct release:
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {results.map((result) => (
                <ITunesResultCard
                  key={result.trackId}
                  result={result}
                  isSelected={false}
                  onSelect={() => onSelect(result)}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="flex justify-start">
        <Button variant="outline" onClick={onBackToSearch}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Search
        </Button>
      </div>
    </div>
  );
};
