import { useKaraokePlayerStore } from "@/stores/useKaraokePlayerStore";
import { useShallow } from "zustand/react/shallow";
import {
  getLyricsSizeValue,
  parseLyricsSize,
  toggleVolume,
  type LyricsSize,
} from "@/utils/performanceControls";

/**
 * Hook for performance controls logic
 * Handles volume toggles and lyrics size conversions
 */
export const usePerformanceControlsLogic = () => {
  const {
    vocalVolume,
    backingVocalVolume,
    instrumentalVolume,
    headphonesVolume,
    headphonesAvailable,
    lyricsSize,
    setVocalVolume,
    setBackingVocalVolume,
    setInstrumentalVolume,
    setHeadphonesVolume,
    setLyricsSize,
  } = useKaraokePlayerStore(
    useShallow((s) => ({
      vocalVolume: s.vocalVolume,
      backingVocalVolume: s.backingVocalVolume,
      instrumentalVolume: s.instrumentalVolume,
      headphonesVolume: s.headphonesVolume,
      headphonesAvailable: s.headphonesAvailable,
      lyricsSize: s.lyricsSize,
      setVocalVolume: s.setVocalVolume,
      setBackingVocalVolume: s.setBackingVocalVolume,
      setInstrumentalVolume: s.setInstrumentalVolume,
      setHeadphonesVolume: s.setHeadphonesVolume,
      setLyricsSize: s.setLyricsSize,
    })),
  );

  const toggleVocalsVolume = () => {
    const newVolume = toggleVolume(vocalVolume, 1); // Max volume is 1 (100%)
    setVocalVolume(newVolume);
  };

  const toggleBackingVocalsVolume = () => {
    const newVolume = toggleVolume(backingVocalVolume, 1);
    setBackingVocalVolume(newVolume);
  };

  const toggleInstrumentalVolume = () => {
    const newVolume = toggleVolume(instrumentalVolume, 1); // Max volume is 1 (100%)
    setInstrumentalVolume(newVolume);
  };

  const toggleHeadphonesVolume = () => {
    setHeadphonesVolume(toggleVolume(headphonesVolume, 1));
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
    backingVocalVolume,
    instrumentalVolume,
    headphonesVolume,
    headphonesAvailable,
    lyricsSize,

    // Actions
    toggleVocalsVolume,
    toggleBackingVocalsVolume,
    toggleInstrumentalVolume,
    toggleHeadphonesVolume,
    handleLyricsSizeChange,
    getLyricsSizeNumericValue,

    // Setters (for direct access if needed)
    setVocalVolume,
    setBackingVocalVolume,
    setInstrumentalVolume,
    setHeadphonesVolume,
    setLyricsSize,
  };
};
