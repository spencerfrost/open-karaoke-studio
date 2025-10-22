import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import {
  getLyricsSizeValue,
  parseLyricsSize,
  toggleVolume,
  type LyricsSize
} from "@/utils/performanceControls";

/**
 * Hook for performance controls logic
 * Handles volume toggles and lyrics size conversions
 */
export const usePerformanceControlsLogic = () => {
  const {
    vocalVolume,
    instrumentalVolume,
    lyricsSize,
    setVocalVolume,
    setInstrumentalVolume,
    setLyricsSize,
  } = useKaraokePlayerStore();

  const toggleVocalsVolume = () => {
    const newVolume = toggleVolume(vocalVolume, 1); // Max volume is 1 (100%)
    setVocalVolume(newVolume);
  };

  const toggleInstrumentalVolume = () => {
    const newVolume = toggleVolume(instrumentalVolume, 1); // Max volume is 1 (100%)
    setInstrumentalVolume(newVolume);
  };

  const handleLyricsSizeChange = (value: number) => {
    const newSize = parseLyricsSize(value);
    setLyricsSize(newSize);
  };

  const getLyricsSizeNumericValue = (size: LyricsSize) => {
    return getLyricsSizeValue(size);
  };

  return {
    // State
    vocalVolume,
    instrumentalVolume,
    lyricsSize,

    // Actions
    toggleVocalsVolume,
    toggleInstrumentalVolume,
    handleLyricsSizeChange,
    getLyricsSizeNumericValue,

    // Setters (for direct access if needed)
    setVocalVolume,
    setInstrumentalVolume,
    setLyricsSize,
  };
};