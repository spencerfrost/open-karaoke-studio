# Open Karaoke Studio: Lyric Timing Solutions

## Overview

Open Karaoke Studio now includes two complementary approaches to solve lyric timing issues in karaoke tracks. This document explains both solutions and when to use each.

## The Problem

When creating karaoke tracks:
1. You separate vocals from music using Demucs
2. You get synced lyrics from online sources
3. **The timing doesn't match** - lyrics might say "start singing at 25s" but vocals actually start at 23s
4. This makes karaoke difficult to follow

## Two Solution Approaches

### 1. Logic-First Lyric Alignment (Ready Now)
**Location**: `/backend/scripts/lyric_alignment/`

**What it does**: Uses audio analysis to detect timing misalignment and provides correction values.

**Best for**:
- Quick fixes to existing karaoke tracks
- Batch processing your entire library
- When you have good synced lyrics but wrong timing
- Quality control and validation

**How it works**:
- Analyzes isolated vocal tracks to find when vocals actually start
- Compares to when synced lyrics say they should start
- Calculates timing offset (e.g., "vocals start 2.67 seconds early")
- Provides specific correction values

**Example Output**:
```
Song: Got Nothing
Detected vocal start: 22.88s
Expected vocal start: 25.55s
Offset: -2.67s (vocals start early)
Recommendation: Shift all lyrics back by 2.67 seconds
```

### 2. AI-Generated Lyrics (Experimental)
**Location**: `/backend/scripts/ai_lyrics/`

**What it does**: Uses AI speech recognition to generate perfectly timed lyrics from audio.

**Best for**:
- Songs with no existing synced lyrics
- Songs with very poor quality lyrics
- Creating custom karaoke from any audio
- When you want AI-generated timing precision

**How it works**:
- Uses Whisper or similar ASR models
- Analyzes the audio directly to create word-level timestamps
- Generates lyrics with perfect timing alignment

**Status**: Experimental - requires additional development

## Project Structure

```
open-karaoke/
├── backend/scripts/
│   ├── lyric_alignment/          # Logic-first approach (ready)
│   │   ├── USER_GUIDE.md        # How to use the system
│   │   ├── onset_detection.py   # Finds vocal start timing
│   │   ├── batch_test.py        # Tests multiple songs
│   │   └── requirements.txt     # Dependencies
│   │
│   └── ai_lyrics/               # AI approach (experimental)
│       └── asr_experiments/     # Speech recognition tests
│
└── docs/
    └── vision_and_roadmap.md    # Technical details
```

## Quick Start

### For Logic-First Alignment:

1. **Install dependencies**:
   ```bash
   cd backend/scripts/lyric_alignment
   pip install -r requirements.txt
   ```

2. **Test a single song**:
   ```bash
   python onset_detection.py
   ```

3. **Test your entire library**:
   ```bash
   python batch_test.py
   ```

4. **Read the results** in `USER_GUIDE.md` for detailed explanations

### For AI Lyrics (Future):

This approach is still in development. It will provide:
- Automatic lyric generation from audio
- Perfect timing alignment
- Word-level precision
- Support for any language

## When to Use Which Approach

| Scenario | Recommended Approach | Why |
|----------|---------------------|-----|
| You have synced lyrics but timing is off | Logic-First Alignment | Quick fix with existing lyrics |
| Lyrics are completely wrong | AI-Generated Lyrics | Start fresh with AI |
| Need to process 100+ songs | Logic-First Alignment | Batch processing available |
| Working with non-English songs | AI-Generated Lyrics | Better language support |
| Want highest accuracy | AI-Generated Lyrics | Direct audio analysis |
| Need results right now | Logic-First Alignment | Ready to use today |

## Results and Impact

### Current Test Results (Logic-First):
- Successfully detected 2.67-second timing offset in test song
- 4 different detection methods provide confidence validation
- Ready for batch processing of entire music libraries

### Expected Benefits:
- **Faster karaoke setup**: Automatically detect and fix timing issues
- **Better user experience**: Lyrics that actually match the audio
- **Quality control**: Identify problematic tracks in your library
- **Scalability**: Process hundreds of songs automatically

## Next Steps

1. **Test the logic-first approach** on your music library
2. **Provide feedback** on accuracy and usefulness
3. **Decide on automation level** - manual fixes vs. automatic corrections
4. **Plan AI lyrics integration** based on your needs

## Getting Help

- **For usage questions**: Read `/backend/scripts/lyric_alignment/USER_GUIDE.md`
- **For technical details**: See `/docs/vision_and_roadmap.md`
- **For test results**: Check `/backend/scripts/lyric_alignment/ANALYSIS_RESULTS.md`

This system is designed to solve real problems in karaoke track preparation. The logic-first approach gives you immediate value, while the AI approach provides a path for even better results in the future.
