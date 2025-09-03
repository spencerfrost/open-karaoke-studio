# YouTube Music Duplicate Detection Feature

## Overview
Implementation plan for adding duplicate detection to YouTube Music search functionality. This feature prevents users from accidentally adding duplicate songs to their library while still allowing legitimate cases (different versions, remixes, etc.).

## Problem Statement
Currently, users can add the same song multiple times from YouTube Music search results without any warning or prevention mechanism. This leads to:
- Cluttered library with duplicate content
- Wasted processing resources
- Poor user experience
- Confusion during karaoke sessions

## Solution Design
A two-tier duplicate detection system:
1. **Inline indicators** - Visual warnings on search results showing duplicate status
2. **Modal confirmation** - Friction dialog for potential duplicates with detailed comparison

## Architecture & Components

### 1. Backend API Enhancement

#### 1.1 New Duplicate Detection Service
**File**: `backend/app/services/duplicate_detection_service.py`

```python
import logging
from typing import List, Optional
from app.db.models.song import DbSong
from app.repositories.song_repository import SongRepository

logger = logging.getLogger(__name__)

class DuplicateDetectionService:
    """Service for detecting potential duplicate songs from YouTube Music search."""
    
    def __init__(self, song_repository: SongRepository):
        self.song_repository = song_repository
        
    def find_potential_duplicates(self, youtube_song: dict) -> List[DuplicateMatch]:
        """
        Find potential duplicates using multiple strategies:
        1. Exact videoId match (confidence: 1.0)
        2. Fuzzy title/artist matching (confidence: 0.6-0.95)
        3. Duration-based matching (confidence modifier)
        4. Album context matching (confidence modifier)
        
        Args:
            youtube_song: YoutubeMusicSearchResult dict with title, artist, videoId, etc.
            
        Returns:
            List of DuplicateMatch objects sorted by confidence (highest first)
        """
        logger.info("Checking for duplicates: %s by %s", 
                   youtube_song.get('title'), youtube_song.get('artist'))
        
        matches = []
        
        # Strategy 1: Exact videoId match
        if youtube_song.get('videoId'):
            exact_match = self._find_by_video_id(youtube_song['videoId'])
            if exact_match:
                matches.append(DuplicateMatch(
                    song=exact_match,
                    confidence=1.0,
                    match_reasons=[MatchReason('videoId', 1.0, 'Identical YouTube video')]
                ))
                return matches  # Exact match found, no need to check further
        
        # Strategy 2: Fuzzy title/artist matching
        title_artist_matches = self._find_by_title_artist_fuzzy(
            youtube_song.get('title', ''),
            youtube_song.get('artist', '')
        )
        
        for db_song in title_artist_matches:
            confidence = self.calculate_match_confidence(youtube_song, db_song)
            if confidence >= 0.5:  # Minimum threshold for potential duplicate
                matches.append(DuplicateMatch(
                    song=db_song,
                    confidence=confidence,
                    match_reasons=self._get_match_reasons(youtube_song, db_song)
                ))
        
        # Sort by confidence (highest first)
        matches.sort(key=lambda x: x.confidence, reverse=True)
        
        logger.info("Found %d potential duplicates with confidence >= 0.5", len(matches))
        return matches
    
    def calculate_match_confidence(self, youtube_song: dict, db_song: DbSong) -> float:
        """
        Calculate confidence score (0-1) for potential match.
        
        Factors:
        - Title similarity (weighted 40%)
        - Artist similarity (weighted 40%) 
        - Duration similarity (weighted 10%)
        - Album similarity (weighted 10%)
        """
        title_sim = self._calculate_string_similarity(
            youtube_song.get('title', ''),
            db_song.title
        )
        
        artist_sim = self._calculate_string_similarity(
            youtube_song.get('artist', ''),
            db_song.artist
        )
        
        duration_sim = self._calculate_duration_similarity(
            youtube_song.get('duration', ''),
            db_song.duration_ms
        )
        
        album_sim = self._calculate_string_similarity(
            youtube_song.get('album', ''),
            db_song.album or ''
        )
        
        # Weighted confidence calculation
        confidence = (
            title_sim * 0.4 +
            artist_sim * 0.4 +
            duration_sim * 0.1 +
            album_sim * 0.1
        )
        
        return min(confidence, 0.99)  # Cap at 0.99 to reserve 1.0 for exact videoId matches
        
    def get_duplicate_status(self, youtube_song: dict) -> DuplicateStatus:
        """
        Get comprehensive duplicate status with categorized matches.
        
        Returns:
            DuplicateStatus with exact/potential matches and overall status
        """
        matches = self.find_potential_duplicates(youtube_song)
        
        if not matches:
            return DuplicateStatus(
                has_duplicates=False,
                status='none',
                exact_match=None,
                potential_matches=[]
            )
        
        # Categorize matches
        exact_match = matches[0] if matches[0].confidence >= 0.9 else None
        potential_matches = [m for m in matches if 0.5 <= m.confidence < 0.9]
        
        if exact_match:
            status = 'exact'
        elif potential_matches:
            status = 'potential'
        else:
            status = 'none'
        
        return DuplicateStatus(
            has_duplicates=bool(exact_match or potential_matches),
            status=status,
            exact_match=exact_match,
            potential_matches=potential_matches[:3]  # Limit to top 3 potential matches
        )
    
    def _find_by_video_id(self, video_id: str) -> Optional[DbSong]:
        """Find song by exact YouTube video ID match."""
        return self.song_repository.find_by_video_id(video_id)
    
    def _find_by_title_artist_fuzzy(self, title: str, artist: str) -> List[DbSong]:
        """Find songs by fuzzy title/artist matching."""
        # Implementation would use database LIKE queries or full-text search
        # Return songs with similar titles/artists for further analysis
        pass
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using Levenshtein distance or similar."""
        # Implementation using difflib.SequenceMatcher or similar
        pass
    
    def _calculate_duration_similarity(self, youtube_duration: str, db_duration_ms: Optional[int]) -> float:
        """Calculate duration similarity score."""
        # Parse YouTube duration (ISO 8601 or mm:ss format)
        # Compare with database duration in milliseconds
        # Return similarity score based on time difference
        pass
    
    def _get_match_reasons(self, youtube_song: dict, db_song: DbSong) -> List[MatchReason]:
        """Generate detailed match reasons for UI display."""
        reasons = []
        
        # Add reasons based on similarity scores
        title_sim = self._calculate_string_similarity(youtube_song.get('title', ''), db_song.title)
        if title_sim >= 0.8:
            reasons.append(MatchReason('title', title_sim, f'Similar title: "{db_song.title}"'))
        
        artist_sim = self._calculate_string_similarity(youtube_song.get('artist', ''), db_song.artist)
        if artist_sim >= 0.8:
            reasons.append(MatchReason('artist', artist_sim, f'Same artist: "{db_song.artist}"'))
        
        # Add duration, album reasons if applicable
        
        return reasons

# Data classes for type safety
@dataclass
class MatchReason:
    type: str  # 'videoId', 'title', 'artist', 'duration', 'album'
    similarity: float  # 0-1
    message: str

@dataclass  
class DuplicateMatch:
    song: DbSong
    confidence: float
    match_reasons: List[MatchReason]

@dataclass
class DuplicateStatus:
    has_duplicates: bool
    status: str  # 'exact', 'potential', 'none'
    exact_match: Optional[DuplicateMatch]
    potential_matches: List[DuplicateMatch]
```

#### 1.2 New API Endpoint
**File**: `backend/app/api/youtube_music.py` (extend existing)

```python
@youtube_music_bp.route("/check-duplicates", methods=["POST"])
@handle_api_error 
def check_duplicates_batch():
    """
    Check multiple YouTube Music songs for duplicates in batch.
    
    Request Body:
        {
            "songs": [
                {
                    "videoId": "string",
                    "title": "string", 
                    "artist": "string",
                    "duration": "string",
                    "album": "string"
                }
            ]
        }
    
    Response:
        {
            "results": [
                {
                    "videoId": "string",
                    "duplicateStatus": {
                        "hasDuplicates": boolean,
                        "status": "exact|potential|none",
                        "exactMatch": {...},
                        "potentialMatches": [...]
                    }
                }
            ]
        }
    """
    try:
        data = request.get_json()
        songs = data.get('songs', [])
        
        if not songs or len(songs) > 50:  # Limit batch size
            raise ValidationError("Invalid songs array (1-50 items required)")
        
        with get_db_session() as session:
            repo = SongRepository(session)
            duplicate_service = DuplicateDetectionService(repo)
            
            results = []
            for song in songs:
                duplicate_status = duplicate_service.get_duplicate_status(song)
                results.append({
                    "videoId": song.get('videoId'),
                    "duplicateStatus": duplicate_status.to_dict()
                })
        
        logger.info("Checked %d songs for duplicates", len(songs))
        return jsonify({"results": results})
        
    except ValidationError:
        raise
    except Exception as e:
        logger.error("Error checking duplicates: %s", e, exc_info=True)
        raise DatabaseError("Failed to check duplicates", "DUPLICATE_CHECK_ERROR")
```

#### 1.3 Enhanced YouTube Music Search Response
Modify existing search endpoint to optionally include duplicate information:

```python
@youtube_music_bp.route("/search", methods=["GET"])
@handle_api_error
def search_youtube_music():
    """
    Enhanced YouTube Music search with optional duplicate detection.
    
    Query Parameters:
        q: Search query (required)
        include_duplicates: Include duplicate status in response (default: false)
    """
    # Existing search logic...
    
    include_duplicates = request.args.get('include_duplicates', 'false').lower() == 'true'
    
    if include_duplicates and results:
        with get_db_session() as session:
            repo = SongRepository(session)
            duplicate_service = DuplicateDetectionService(repo)
            
            # Add duplicate status to each result
            for result in results:
                duplicate_status = duplicate_service.get_duplicate_status(result)
                result['duplicateStatus'] = duplicate_status.to_dict()
    
    return jsonify({"results": results, "error": None})
```

### 2. Frontend Type Definitions

#### 2.1 New Types
**File**: `frontend/src/types/Duplicates.ts`

```typescript
export interface MatchReason {
  type: 'videoId' | 'title' | 'artist' | 'duration' | 'album';
  similarity: number; // 0-1
  message: string;
}

export interface DuplicateMatch {
  song: Song;
  confidence: number; // 0-1
  matchReasons: MatchReason[];
}

export interface DuplicateStatus {
  hasDuplicates: boolean;
  status: 'exact' | 'potential' | 'none';
  exactMatch?: DuplicateMatch; // confidence >= 0.9
  potentialMatches: DuplicateMatch[]; // confidence 0.5-0.89
}

export interface YoutubeMusicSearchResultWithDuplicates extends YoutubeMusicSearchResult {
  duplicateStatus?: DuplicateStatus;
}

export interface DuplicateCheckRequest {
  songs: YoutubeMusicSearchResult[];
}

export interface DuplicateCheckResponse {
  results: Array<{
    videoId: string;
    duplicateStatus: DuplicateStatus;
  }>;
}
```

#### 2.2 Enhanced YouTube Music Types
**File**: `frontend/src/types/YoutubeMusic.ts` (extend existing)

```typescript
// Add import for duplicate types
import { DuplicateStatus } from './Duplicates';

export interface YoutubeMusicSearchResponse {
  results: YoutubeMusicSearchResultWithDuplicates[]; // Enhanced with duplicate info
  error: string | null;
}

// Re-export for convenience
export type { YoutubeMusicSearchResultWithDuplicates } from './Duplicates';
```

### 3. Frontend API Hooks

#### 3.1 Duplicate Detection Hook
**File**: `frontend/src/hooks/api/useDuplicateDetection.ts`

```typescript
import { useMutation } from '@tanstack/react-query';
import { YoutubeMusicSearchResult } from '@/types/YoutubeMusic';
import { DuplicateCheckRequest, DuplicateCheckResponse, DuplicateStatus } from '@/types/Duplicates';

export function useDuplicateDetection() {
  const checkDuplicatesMutation = useMutation<
    DuplicateCheckResponse,
    Error,
    DuplicateCheckRequest
  >({
    mutationFn: async ({ songs }) => {
      const response = await fetch('/api/youtube-music/check-duplicates', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ songs }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to check duplicates');
      }

      return response.json();
    },
  });

  const checkDuplicates = async (songs: YoutubeMusicSearchResult[]): Promise<DuplicateStatus[]> => {
    if (!songs.length) return [];
    
    try {
      const result = await checkDuplicatesMutation.mutateAsync({ songs });
      
      // Map results back to original song order
      return songs.map(song => {
        const result_item = result.results.find(r => r.videoId === song.videoId);
        return result_item?.duplicateStatus || {
          hasDuplicates: false,
          status: 'none',
          potentialMatches: [],
        };
      });
    } catch (error) {
      console.error('Failed to check duplicates:', error);
      // Return empty statuses on error (graceful degradation)
      return songs.map(() => ({
        hasDuplicates: false,
        status: 'none' as const,
        potentialMatches: [],
      }));
    }
  };

  const checkSingleDuplicate = async (song: YoutubeMusicSearchResult): Promise<DuplicateStatus> => {
    const results = await checkDuplicates([song]);
    return results[0];
  };

  return {
    checkDuplicates,
    checkSingleDuplicate,
    isLoading: checkDuplicatesMutation.isPending,
    error: checkDuplicatesMutation.error,
  };
}
```

#### 3.2 Enhanced YouTube Music Hook
**File**: `frontend/src/hooks/api/useYoutubeMusic.ts` (modify existing)

```typescript
import { useQuery } from '@tanstack/react-query';
import { YoutubeMusicSearchResponse, YoutubeMusicSearchResultWithDuplicates } from '@/types/YoutubeMusic';
import { useDuplicateDetection } from './useDuplicateDetection';

export const useYoutubeMusicSearch = (
  query: string, 
  enabled: boolean,
  includeDuplicates: boolean = true
) => {
  const { checkDuplicates } = useDuplicateDetection();

  return useQuery<YoutubeMusicSearchResultWithDuplicates[], string[], Error>({
    queryKey: ['youtube-music', 'search', query, includeDuplicates],
    queryFn: async () => {
      // First, get search results
      const searchParams = new URLSearchParams({ q: query });
      if (includeDuplicates) {
        searchParams.append('include_duplicates', 'true');
      }
      
      const response = await fetch(`/api/youtube-music/search?${searchParams}`, {
        credentials: 'include',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Search failed');
      }

      const data: YoutubeMusicSearchResponse = await response.json();
      
      if (data.error) {
        throw new Error(data.error);
      }

      let results = data.results;

      // If backend didn't include duplicates, check them on frontend
      if (includeDuplicates && results.length > 0 && !results[0].duplicateStatus) {
        try {
          const duplicateStatuses = await checkDuplicates(results);
          results = results.map((song, index) => ({
            ...song,
            duplicateStatus: duplicateStatuses[index],
          }));
        } catch (error) {
          console.error('Failed to check duplicates on frontend:', error);
          // Continue without duplicate info
        }
      }

      return results;
    },
    enabled: enabled && !!query.trim(),
    staleTime: 1000 * 60 * 5, // 5 minutes
    gcTime: 1000 * 60 * 10, // 10 minutes
  });
};
```

### 4. UI Components

#### 4.1 Duplicate Status Indicator
**File**: `frontend/src/components/add/YoutubeMusicSearch/DuplicateStatusIndicator.tsx`

```typescript
import React from 'react';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';
import { DuplicateStatus } from '@/types/Duplicates';

interface DuplicateStatusIndicatorProps {
  status: DuplicateStatus;
  compact?: boolean;
}

export const DuplicateStatusIndicator: React.FC<DuplicateStatusIndicatorProps> = ({
  status,
  compact = false,
}) => {
  if (!status.hasDuplicates) {
    if (compact) return null;
    
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge variant="outline" className="text-green-600 border-green-600">
              <CheckCircle2 className="w-3 h-3 mr-1" />
              New
            </Badge>
          </TooltipTrigger>
          <TooltipContent>
            <p>This song is not in your library</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  const getStatusConfig = () => {
    switch (status.status) {
      case 'exact':
        return {
          icon: XCircle,
          label: 'Exact Match',
          variant: 'destructive' as const,
          className: 'text-red-600 border-red-600',
          tooltip: `Exact duplicate found: ${status.exactMatch?.song.title}`,
        };
      case 'potential':
        return {
          icon: AlertTriangle,
          label: 'Similar',
          variant: 'outline' as const,
          className: 'text-yellow-600 border-yellow-600',
          tooltip: `${status.potentialMatches.length} similar song(s) found`,
        };
      default:
        return null;
    }
  };

  const config = getStatusConfig();
  if (!config) return null;

  const { icon: Icon, label, variant, className, tooltip } = config;

  if (compact) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Icon className="w-4 h-4 text-current" />
          </TooltipTrigger>
          <TooltipContent>
            <p>{tooltip}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge variant={variant} className={className}>
            <Icon className="w-3 h-3 mr-1" />
            {label}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <div className="space-y-1">
            <p>{tooltip}</p>
            {status.potentialMatches.length > 0 && (
              <div className="text-xs">
                <p className="font-medium">Similar songs:</p>
                {status.potentialMatches.slice(0, 2).map((match, index) => (
                  <p key={index}>
                    • {match.song.title} by {match.song.artist}
                  </p>
                ))}
                {status.potentialMatches.length > 2 && (
                  <p>• ...and {status.potentialMatches.length - 2} more</p>
                )}
              </div>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};
```

#### 4.2 Duplicate Confirmation Modal
**File**: `frontend/src/components/add/YoutubeMusicSearch/DuplicateConfirmationModal.tsx`

```typescript
import React from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { AlertTriangle, Music, Clock, User, Album } from 'lucide-react';
import { YoutubeMusicSearchResult } from '@/types/YoutubeMusic';
import { DuplicateStatus, DuplicateMatch } from '@/types/Duplicates';

interface DuplicateConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  youtubeSong: YoutubeMusicSearchResult;
  duplicateStatus: DuplicateStatus;
  onConfirm: () => void;
  onCancel: () => void;
  isAdding?: boolean;
}

export const DuplicateConfirmationModal: React.FC<DuplicateConfirmationModalProps> = ({
  isOpen,
  onClose,
  youtubeSong,
  duplicateStatus,
  onConfirm,
  onCancel,
  isAdding = false,
}) => {
  const handleCancel = () => {
    onCancel();
    onClose();
  };

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  const formatDuration = (duration: string | number | undefined): string => {
    if (!duration) return 'Unknown';
    // Handle different duration formats (ISO 8601, mm:ss, milliseconds)
    // Implementation depends on how durations are formatted
    return duration.toString();
  };

  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.9) return 'text-red-600';
    if (confidence >= 0.7) return 'text-yellow-600';
    return 'text-blue-600';
  };

  const renderSongComparison = (match: DuplicateMatch) => (
    <div className="p-4 border rounded-lg space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Music className="w-4 h-4" />
          <span className="font-medium">Similar Song Found</span>
        </div>
        <Badge variant="outline" className={getConfidenceColor(match.confidence)}>
          {Math.round(match.confidence * 100)}% match
        </Badge>
      </div>
      
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <p className="text-muted-foreground">YouTube Music</p>
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <Music className="w-3 h-3" />
              <span className="font-medium">{youtubeSong.title}</span>
            </div>
            <div className="flex items-center space-x-2">
              <User className="w-3 h-3" />
              <span>{youtubeSong.artist}</span>
            </div>
            {youtubeSong.album && (
              <div className="flex items-center space-x-2">
                <Album className="w-3 h-3" />
                <span>{youtubeSong.album}</span>
              </div>
            )}
            <div className="flex items-center space-x-2">
              <Clock className="w-3 h-3" />
              <span>{formatDuration(youtubeSong.duration)}</span>
            </div>
          </div>
        </div>
        
        <div>
          <p className="text-muted-foreground">In Your Library</p>
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <Music className="w-3 h-3" />
              <span className="font-medium">{match.song.title}</span>
            </div>
            <div className="flex items-center space-x-2">
              <User className="w-3 h-3" />
              <span>{match.song.artist}</span>
            </div>
            {match.song.album && (
              <div className="flex items-center space-x-2">
                <Album className="w-3 h-3" />
                <span>{match.song.album}</span>
              </div>
            )}
            <div className="flex items-center space-x-2">
              <Clock className="w-3 h-3" />
              <span>{formatDuration(match.song.durationMs)}</span>
            </div>
          </div>
        </div>
      </div>
      
      {match.matchReasons.length > 0 && (
        <div>
          <p className="text-sm font-medium mb-2">Match Reasons:</p>
          <div className="space-y-1">
            {match.matchReasons.map((reason, index) => (
              <div key={index} className="text-xs text-muted-foreground">
                • {reason.message}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const isExactMatch = duplicateStatus.status === 'exact';
  const totalMatches = (duplicateStatus.exactMatch ? 1 : 0) + duplicateStatus.potentialMatches.length;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            <AlertTriangle className="w-5 h-5 text-yellow-600" />
            <span>
              {isExactMatch ? 'Exact Duplicate Found' : 'Similar Songs Found'}
            </span>
          </DialogTitle>
          <DialogDescription>
            {isExactMatch
              ? 'This exact song is already in your library.'
              : `Found ${totalMatches} similar song${totalMatches > 1 ? 's' : ''} in your library.`}
            {' '}Are you sure you want to add this song anyway?
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[60vh]">
          <div className="space-y-4">
            {duplicateStatus.exactMatch && renderSongComparison(duplicateStatus.exactMatch)}
            
            {duplicateStatus.exactMatch && duplicateStatus.potentialMatches.length > 0 && (
              <Separator />
            )}
            
            {duplicateStatus.potentialMatches.map((match, index) => (
              <React.Fragment key={index}>
                {renderSongComparison(match)}
                {index < duplicateStatus.potentialMatches.length - 1 && <Separator />}
              </React.Fragment>
            ))}
          </div>
        </ScrollArea>

        <DialogFooter className="space-x-2">
          <Button variant="outline" onClick={handleCancel} disabled={isAdding}>
            Cancel
          </Button>
          <Button 
            onClick={handleConfirm} 
            disabled={isAdding}
            variant={isExactMatch ? "destructive" : "default"}
          >
            {isAdding ? 'Adding...' : 'Add Anyway'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
```

#### 4.3 Enhanced Song Result Item
**File**: `frontend/src/components/add/YoutubeMusicSearch/SongResultItem.tsx` (modify existing)

```typescript
import React from "react";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { SongResultItemProps } from "./YoutubeMusicSearch.types";
import { DuplicateStatusIndicator } from "./DuplicateStatusIndicator";

export const SongResultItem: React.FC<SongResultItemProps> = ({
  song,
  isAdding,
  onAddToLibrary,
}) => {
  const duplicateStatus = song.duplicateStatus;
  const hasExactDuplicate = duplicateStatus?.status === 'exact';
  const hasPotentialDuplicates = duplicateStatus?.status === 'potential';

  const getButtonText = () => {
    if (isAdding) return "Processing...";
    if (hasExactDuplicate) return "Already in Library";
    if (hasPotentialDuplicates) return "Add Anyway";
    return "Add to Library";
  };

  const getButtonVariant = () => {
    if (hasExactDuplicate) return "outline";
    if (hasPotentialDuplicates) return "outline";
    return "default";
  };

  return (
    <li className="py-3 flex items-center">
      {song.thumbnails?.[0]?.url && (
        <img
          src={song.thumbnails[0].url}
          alt={song.title}
          className="w-12 h-12 rounded mr-3 object-cover"
        />
      )}
      <div className="flex-1">
        <div className="flex items-center space-x-2">
          <span className="font-medium">{song.title}</span>
          {duplicateStatus && (
            <DuplicateStatusIndicator status={duplicateStatus} compact />
          )}
        </div>
        <div className="text-sm text-muted-foreground">
          {song.artist} • {song.duration}
        </div>
        {song.album && (
          <div className="text-xs text-muted-foreground">
            Album: {song.album}
          </div>
        )}
        {duplicateStatus && !hasExactDuplicate && (
          <div className="mt-1">
            <DuplicateStatusIndicator status={duplicateStatus} />
          </div>
        )}
      </div>
      <Button
        onClick={() => onAddToLibrary(song)}
        disabled={isAdding || hasExactDuplicate}
        variant={getButtonVariant()}
        className="ml-4"
      >
        {isAdding ? (
          <>
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            {getButtonText()}
          </>
        ) : (
          getButtonText()
        )}
      </Button>
    </li>
  );
};
```

#### 4.4 Enhanced Search Results
**File**: `frontend/src/components/add/YoutubeMusicSearch/SearchResults.tsx` (modify existing)

```typescript
import React, { useState } from "react";
import { SongResultItem } from "./SongResultItem";
import { DuplicateConfirmationModal } from "./DuplicateConfirmationModal";
import { SearchResultsProps } from "./YoutubeMusicSearch.types";
import { YoutubeMusicSearchResultWithDuplicates } from "@/types/YoutubeMusic";

export const SearchResults: React.FC<SearchResultsProps> = ({
  results,
  isLoading,
  error,
  query,
  onAddToLibrary,
  addingStates,
}) => {
  const [duplicateModalState, setDuplicateModalState] = useState<{
    isOpen: boolean;
    song: YoutubeMusicSearchResultWithDuplicates | null;
  }>({
    isOpen: false,
    song: null,
  });

  const handleAddToLibrary = async (song: YoutubeMusicSearchResultWithDuplicates) => {
    const duplicateStatus = song.duplicateStatus;
    
    // Show modal for potential duplicates
    if (duplicateStatus?.hasDuplicates && duplicateStatus.status === 'potential') {
      setDuplicateModalState({
        isOpen: true,
        song,
      });
      return;
    }
    
    // Direct add for new songs (no duplicates)
    await onAddToLibrary(song);
  };

  const handleModalConfirm = async () => {
    if (duplicateModalState.song) {
      await onAddToLibrary(duplicateModalState.song);
    }
    setDuplicateModalState({ isOpen: false, song: null });
  };

  const handleModalCancel = () => {
    setDuplicateModalState({ isOpen: false, song: null });
  };

  if (isLoading) {
    return <div className="text-center py-4">Loading...</div>;
  }

  if (error) {
    return <div className="text-destructive py-2">{error.message}</div>;
  }

  if (results.length === 0 && query) {
    return (
      <div className="text-center text-muted-foreground py-4">
        No official audio found.
      </div>
    );
  }

  if (results.length === 0) {
    return null;
  }

  return (
    <>
      <ul className="divide-y divide-border">
        {results.map((song) => (
          <SongResultItem
            key={song.videoId}
            song={song}
            isAdding={addingStates[song.videoId] || false}
            onAddToLibrary={handleAddToLibrary}
          />
        ))}
      </ul>

      {duplicateModalState.song && duplicateModalState.song.duplicateStatus && (
        <DuplicateConfirmationModal
          isOpen={duplicateModalState.isOpen}
          onClose={() => setDuplicateModalState({ isOpen: false, song: null })}
          youtubeSong={duplicateModalState.song}
          duplicateStatus={duplicateModalState.song.duplicateStatus}
          onConfirm={handleModalConfirm}
          onCancel={handleModalCancel}
          isAdding={addingStates[duplicateModalState.song.videoId] || false}
        />
      )}
    </>
  );
};
```

### 5. Enhanced Business Logic

#### 5.1 Enhanced Song Creation Hook
**File**: `frontend/src/hooks/useSongCreation.ts` (modify existing)

```typescript
import { useState } from 'react';
import { YoutubeMusicSearchResultWithDuplicates } from '@/types/YoutubeMusic';
import { useSongs } from './api/useSongs';

export const useSongCreation = () => {
  const [currentSong, setCurrentSong] = useState<YoutubeMusicSearchResultWithDuplicates | null>(null);
  const [duplicateOverride, setDuplicateOverride] = useState<boolean>(false);
  
  const { useCreateSong } = useSongs();
  const createSongMutation = useCreateSong();

  const createSong = async (song: YoutubeMusicSearchResultWithDuplicates, overrideDuplicates = false) => {
    setCurrentSong(song);
    setDuplicateOverride(overrideDuplicates);
    
    try {
      // Log duplicate override decision for analytics
      if (song.duplicateStatus?.hasDuplicates && overrideDuplicates) {
        console.log('User chose to override duplicate detection', {
          videoId: song.videoId,
          duplicateStatus: song.duplicateStatus.status,
          matchCount: song.duplicateStatus.potentialMatches.length,
        });
      }
      
      const result = await createSongMutation.mutateAsync({
        title: song.title,
        artist: song.artist,
        videoId: song.videoId,
        source: 'youtube-music',
        sourceUrl: `https://music.youtube.com/watch?v=${song.videoId}`,
        album: song.album,
        // Include duplicate override flag in metadata
        metadata: {
          duplicateOverride: overrideDuplicates,
          originalDuplicateStatus: song.duplicateStatus,
        },
      });
      
      return result;
    } catch (error) {
      console.error('Failed to create song:', error);
      throw error;
    } finally {
      setCurrentSong(null);
      setDuplicateOverride(false);
    }
  };

  return {
    createSong,
    currentSong,
    isAdding: createSongMutation.isPending,
    error: createSongMutation.error,
    duplicateOverride,
  };
};
```

## Implementation Phases

### Phase 1: Backend Foundation (Week 1)
1. ✅ Create `DuplicateDetectionService` with basic matching algorithms
2. ✅ Add database methods to `SongRepository` for duplicate queries
3. ✅ Implement `/api/youtube-music/check-duplicates` endpoint  
4. ✅ Enhance existing search endpoint with optional duplicate checking
5. ✅ Write comprehensive unit tests for duplicate detection logic
6. ✅ Add logging and error handling

### Phase 2: Frontend Types & API (Week 1)
1. ✅ Create duplicate-related TypeScript interfaces
2. ✅ Implement `useDuplicateDetection` hook with proper error handling
3. ✅ Enhance existing YouTube Music hooks to include duplicate checking
4. ✅ Create utility functions for duplicate status handling
5. ✅ Add comprehensive error boundaries

### Phase 3: UI Components (Week 2)
1. ✅ Build `DuplicateStatusIndicator` component with tooltips
2. ✅ Create `DuplicateConfirmationModal` with rich comparison UI
3. ✅ Update `SongResultItem` with duplicate indicators and button states
4. ✅ Enhance `SearchResults` with modal state management
5. ✅ Add loading states and skeleton components

### Phase 4: Integration & Polish (Week 2)
1. ✅ Wire up all components in the YouTube Music Search flow
2. ✅ Add user preferences for duplicate behavior (future: settings panel)
3. ✅ Implement analytics/logging for duplicate detection effectiveness
4. ✅ Add keyboard navigation and accessibility features
5. ✅ Optimize performance with memoization and lazy loading

### Phase 5: Testing & Refinement (Week 3)
1. ✅ End-to-end testing of duplicate detection workflow
2. ✅ Performance optimization for search with duplicate checking
3. ✅ UX refinements based on testing feedback
4. ✅ Error handling and edge case coverage
5. ✅ Documentation updates and code review

## Key UX Flow

1. **User searches** → YouTube Music results load with real-time duplicate checking
2. **Inline indicators** → Visual badges show duplicate status immediately:
   - 🔴 **"Exact Match"** - Identical song (button disabled)
   - 🟡 **"Similar"** - Potential duplicates (button shows "Add Anyway")
   - 🟢 **"New"** - No duplicates found (normal "Add to Library")
3. **Click interaction**:
   - **No duplicates**: Direct add to library
   - **Potential duplicates**: Show confirmation modal with comparison
   - **Exact duplicates**: Button disabled with "Already in Library" text
4. **Modal interaction** → Side-by-side comparison with confidence scores and match reasons
5. **User decision** → "Add Anyway" or "Cancel" with decision logged for analytics

## Technical Considerations

### Performance Optimizations
- **Async duplicate checking**: Don't block search results display
- **Debounced search**: Avoid excessive API calls during typing
- **Result caching**: Cache duplicate status for recently searched songs
- **Progressive enhancement**: Search works even if duplicate checking fails
- **Batch API calls**: Check multiple songs in single request

### Matching Algorithm Strategy
1. **Exact videoId match** (confidence: 1.0) → Same YouTube video
2. **High title/artist similarity** (confidence: 0.8-0.95) → Likely same song
3. **Moderate similarity + duration match** (confidence: 0.6-0.8) → Possible duplicate  
4. **Low similarity** (confidence: < 0.6) → Different song

### Error Handling & Resilience
- **Graceful degradation**: If duplicate checking fails, allow normal add flow
- **Retry mechanism**: Retry failed duplicate checks with exponential backoff
- **User feedback**: Clear error messages if duplicate detection is unavailable
- **Fallback UI**: Show search results even if duplicate API is down
- **Analytics**: Track duplicate detection failures for monitoring

### Security & Performance
- **Rate limiting**: Prevent abuse of duplicate checking API
- **Input validation**: Sanitize all search inputs and parameters
- **SQL injection protection**: Use parameterized queries for database access
- **Memory management**: Limit batch sizes and cache sizes
- **Database indexing**: Optimize queries for title/artist/videoId lookups

## Future Enhancements

### Advanced Features
- **Smart learning**: Learn from user override decisions to improve matching
- **Bulk duplicate detection**: Check entire library for existing duplicates
- **User preferences**: Configurable duplicate sensitivity levels
- **Duplicate resolution**: Tools to merge/deduplicate existing library songs
- **Preview comparison**: Audio preview of duplicate candidates

### Analytics & Insights
- **Duplicate prevention metrics**: Track how many duplicates were prevented
- **User behavior analysis**: Understand when users override duplicate warnings
- **Match algorithm effectiveness**: Monitor false positives/negatives
- **Library health insights**: Show users duplicate statistics and cleanup suggestions

This implementation provides a comprehensive solution that balances duplicate prevention with user control, following the project's architecture patterns and code quality standards.