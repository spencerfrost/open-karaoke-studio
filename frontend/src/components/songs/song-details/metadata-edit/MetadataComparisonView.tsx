import React from 'react';
import { Song } from '@/types/Song';
import { ITunesSearchResult } from '@/hooks/useItunesSearch';

interface MetadataComparisonViewProps {
  currentSong: Song;
  selectedResult: ITunesSearchResult;
}

export const MetadataComparisonView: React.FC<MetadataComparisonViewProps> = ({
  currentSong,
  selectedResult,
}) => {
  const changes = [
    {
      field: 'Title',
      current: currentSong.title,
      new: selectedResult.trackName,
      changed: currentSong.title !== selectedResult.trackName,
    },
    {
      field: 'Artist',
      current: currentSong.artist,
      new: selectedResult.artistName,
      changed: currentSong.artist !== selectedResult.artistName,
    },
    {
      field: 'Album',
      current: currentSong.album,
      new: selectedResult.collectionName,
      changed: currentSong.album !== selectedResult.collectionName,
    },
    {
      field: 'Genre',
      current: currentSong.genre || 'Not set',
      new: selectedResult.primaryGenreName || 'Not set',
      changed: (currentSong.genre || '') !== (selectedResult.primaryGenreName || ''),
    },
  ];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2 text-sm font-medium">
        <div>Field</div>
        <div>Current</div>
        <div>New</div>
      </div>
      
      {changes.map((change) => (
        <div 
          key={change.field}
          className={`grid grid-cols-3 gap-2 text-sm p-2 rounded ${
            change.changed ? 'bg-yellow-50 border border-yellow-200' : ''
          }`}
        >
          <div className="font-medium">{change.field}</div>
          <div className="truncate text-muted-foreground">{change.current}</div>
          <div className={`truncate ${change.changed ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>
            {change.new}
          </div>
        </div>
      ))}
      
      <div className="pt-2 text-xs text-muted-foreground space-y-1">
        <p><strong>Note:</strong> Audio Duration (from your file) will be preserved. iTunes Duration is stored separately for reference.</p>
        <p>iTunes IDs will be updated: Track ID {selectedResult.trackId}, 
        Artist ID {selectedResult.artistId}, Collection ID {selectedResult.collectionId}</p>
      </div>
    </div>
  );
};
