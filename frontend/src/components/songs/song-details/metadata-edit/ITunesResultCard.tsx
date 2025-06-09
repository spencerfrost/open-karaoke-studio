import React from 'react';
import { ITunesSearchResult } from '@/hooks/useItunesSearch';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ExternalLink } from 'lucide-react';

interface ITunesResultCardProps {
  result: ITunesSearchResult;
  isSelected: boolean;
  onSelect: () => void;
}

export const ITunesResultCard: React.FC<ITunesResultCardProps> = ({ 
  result, 
  isSelected, 
  onSelect 
}) => {
  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'Unknown';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  return (
    <Card 
      className={`cursor-pointer transition-colors ${
        isSelected ? 'ring-2 ring-primary border-primary' : 'hover:bg-accent'
      }`}
      onClick={onSelect}
    >
      <CardContent className="p-4">
        <div className="flex gap-4">
          {/* Artwork */}
          <div className="flex-shrink-0">
            {result.artworkUrl100 ? (
              <img
                src={result.artworkUrl100}
                alt={`${result.collectionName} artwork`}
                className="w-16 h-16 rounded object-cover"
              />
            ) : (
              <div className="w-16 h-16 rounded bg-muted flex items-center justify-center text-xs text-muted-foreground">
                No Image
              </div>
            )}
          </div>
          
          {/* Metadata */}
          <div className="flex-1 min-w-0 space-y-1">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <h4 className="font-medium text-sm truncate">{result.trackName}</h4>
                <p className="text-sm text-muted-foreground truncate">{result.artistName}</p>
                <p className="text-sm text-muted-foreground truncate">{result.collectionName}</p>
              </div>
              <div className="flex-shrink-0 text-right text-xs space-y-1">
                <div>{formatDuration(result.durationSeconds)}</div>
                {result.releaseYear && (
                  <Badge variant="secondary" className="text-xs">
                    {result.releaseYear}
                  </Badge>
                )}
              </div>
            </div>
            
            {/* Additional info */}
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {result.primaryGenreName && (
                <Badge variant="outline" className="text-xs">
                  {result.primaryGenreName}
                </Badge>
              )}
              {result.trackExplicitness === 'explicit' && (
                <Badge variant="destructive" className="text-xs">
                  Explicit
                </Badge>
              )}
              {result.previewUrl && (
                <a 
                  href={result.previewUrl} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 flex items-center gap-1"
                  onClick={(e) => e.stopPropagation()}
                >
                  <ExternalLink className="h-3 w-3" />
                  Preview
                </a>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
