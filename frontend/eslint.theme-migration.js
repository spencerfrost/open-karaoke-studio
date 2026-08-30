/*
 * Files that still contain raw palette classes (orange-peel, lemon-chiffon,
 * russet, rust, dark-cyan) because Stage 3 of the theme-token migration has
 * not converted them yet. See docs/plans/2026-07-19-theme-token-migration.md.
 *
 * This list may only ever shrink. When it is empty, delete this file and the
 * override block that consumes it in eslint.config.js — at that point the
 * raw palette utilities can be removed from @theme in index.css and the
 * classes stop compiling entirely.
 */
export const STAGE_3_PENDING = [
  'src/components/session/SessionInfoDisplay.tsx',
  'src/features/library/components/AlphabeticalIndexBar.tsx',
  'src/features/library/components/AlphabeticalNavigation.tsx',
  'src/features/library/components/ArtistAccordion.tsx',
  'src/features/library/components/ArtistResultsSection.tsx',
  'src/features/library/components/ArtistSection.tsx',
  'src/features/library/components/ArtistSongTable.tsx',
  'src/features/library/components/BrowseArtistCard.tsx',
  'src/features/library/components/LibrarySearchInput.tsx',
  'src/features/library/components/RecentlyAddedSongs/RecentlyAddedSongs.tsx',
  'src/features/library/components/RecentlyAddedSongs/SectionHeader.tsx',
  'src/features/library/components/RecentlySang/RecentlySang.tsx',
  'src/features/library/components/SongResultsGrid.tsx',
  'src/features/library/components/SongResultsSection.tsx',
  'src/features/lyrics/components/CountInDisplay.tsx',
  'src/features/lyrics/components/KaraokeLyricsRenderer.tsx',
  'src/features/lyrics/components/LyricsSizeControl.tsx',
  'src/features/performance/components/ConnectedPerformanceControls.tsx',
  'src/features/performance/components/KnobControl.tsx',
  'src/features/performance/components/PerformanceControlsPanel.tsx',
  'src/features/performance/components/VolumeChannel.tsx',
  'src/features/player/components/KaraokePlayer.tsx',
  'src/features/player/components/subcomponents/AudioVisualizer.tsx',
  'src/features/player/components/subcomponents/ChordCarousel.tsx',
  'src/features/player/components/subcomponents/ProgressBar.tsx',
  'src/features/player/components/subcomponents/QueueEnded.tsx',
  'src/features/player/components/subcomponents/settings-menu/LyricsEditView.tsx',
  'src/features/player/components/subcomponents/settings-menu/LyricsTimingView.tsx',
  'src/features/player/components/subcomponents/settings-menu/LyricsView.tsx',
  'src/features/player/components/subcomponents/settings-menu/MainView.tsx',
  'src/features/player/components/subcomponents/settings-menu/SpeedView.tsx',
  'src/features/player/components/subcomponents/settings-menu/VolumeView.tsx',
  'src/features/queue/components/KaraokeQueueItem.tsx',
  'src/features/session/components/SessionEndModal.tsx',
  'src/features/session/components/SessionRecoveryLoading.tsx',
  'src/features/session/components/WebsocketStatus.tsx',
  'src/pages/Settings.tsx',
]
