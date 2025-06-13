# Open Karaoke Studio: Vision and Roadmap

## 1. Aligning Synced Lyrics with Vocal Start
- **Goal:** Precisely align the start of synced lyrics with the true start of vocals in each song's isolated vocal track (vocals.mp3).
- **Motivation:** Sometimes, vocal tracks contain non-word intros (e.g., "ooo", "ahhh") or even non-vocal sounds (e.g., guitar, whale calls) that are picked up by AI separation. The true start of the main vocal is not always at the very beginning of the track.
- **Approach Ideas:**
  - Analyze the vocal track to detect the first significant vocal onset (ideally, the first word sung).
  - Use this to align or shift the synced lyrics, or crop the vocal track for better alignment.
  - Compare the duration of the synced lyrics with the audio to estimate a window for onset detection (e.g., check within a 3-6 second window).

## 2. Technical Approaches for Vocal Start Detection
- **Onset Detection:**
  - Use Python audio analysis libraries (e.g., `librosa`, `madmom`) to detect onsets in the vocal track.
  - Focus on energy spikes or spectral changes that indicate the start of singing.
- **Speech-to-Text with Timestamps:**
  - Use models like OpenAI Whisper, Vosk, or other ASR (Automatic Speech Recognition) tools to transcribe the vocal track and obtain word-level timestamps.
  - This could distinguish between non-word sounds and actual lyrics, enabling more precise alignment.
  - If models provide word timing, this could power advanced features like bouncing ball karaoke.

## 3. Database Schema Evolution
- **Current State:** Lyrics and their metadata (plain, synced, duration, etc.) are likely stored directly on the song record.
- **Proposed Change:**
  - Move lyrics to a dedicated table, linked to songs.
  - Store additional metadata: type (plain/synced), duration, alignment info, etc.
  - This enables more flexible data management and future features.

## 4. Long-Term Vision
- **AI-Generated Karaoke Features:**
  - Explore STT (Speech-to-Text) models that can generate synced lyrics from vocal tracks.
  - Use aligned vocal tracks and synced lyrics as training data for models that can generate synced lyrics from new vocal tracks.
  - Explore bouncing ball karaoke by generating word-level or syllable-level timing.
  - Potentially train custom models for even more precise lyric alignment and karaoke effects.
- **Other AI Features:**
  - Pitch shifting, key transposition, and more advanced audio processing.

## 5. Next Steps
- **Document and Prioritize:**
  - Maintain this document as a living roadmap for feature ideas and technical directions.
- **Prototype:**
  - Start with a Python script to detect vocal onsets in isolated vocal tracks.
  - Evaluate speech-to-text models for word-level timing.
- **Database:**
  - Plan and implement a migration to move lyrics into a dedicated table.

---

*This document captures the current vision and technical roadmap for Open Karaoke Studio, based on recent brainstorming and architectural progress. It should be updated as new ideas and technical solutions emerge.*
