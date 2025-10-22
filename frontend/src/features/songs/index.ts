/**
 * Songs feature exports
 * Clean API for song management functionality
 */

// Component exports
export { AddSongDialog } from './components/AddSongDialog';
export { DeleteSongDialog } from './components/DeleteSongDialog';
export { JoinSessionDialog } from './components/JoinSessionDialog';
export { default as MetadataEditor } from './components/MetadataEditor';
export { MetadataEditorTab } from './components/MetadataEditorTab';
export { MetadataSearchTab } from './components/MetadataSearchTab';
export { YoutubeMusicResultCard } from './components/YoutubeMusicResultCard';
export { YouTubeResultCard } from './components/YoutubeVideoResultCard';

// Hook exports
export { useSongActions } from './hooks/useSongActions';
export { useSongCreation } from './hooks/useSongCreation';
export { useAddSongDialog } from './hooks/useAddSongDialog';
export { useSongDialogs } from './hooks/useSongDialogs';