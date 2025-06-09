# Lyric Alignment User Guide

## What This Project Does

This project helps solve a common problem in karaoke: **synced lyrics don't match when vocals actually start in the audio**. For example, lyrics might say to start singing at 25 seconds, but the actual vocals don't begin until 23 seconds.

## The Problem We're Solving

When you download karaoke tracks and synced lyrics:
- The lyrics file has timestamps for when each line should be sung
- But the vocal track (after removing instrumentals) might have different timing
- This creates a mismatch that makes karaoke difficult to follow

## How Our Solution Works

We use audio analysis to:
1. **Detect when vocals actually start** in the isolated vocal track
2. **Compare this to when lyrics say they should start**
3. **Calculate the timing offset** between expected and actual
4. **Recommend adjustments** to fix the alignment

## Project Structure

```
backend/scripts/lyric_alignment/
├── README.md              # Technical documentation
├── USER_GUIDE.md         # This file - explains everything simply
├── ANALYSIS_RESULTS.md   # Detailed test results
├── onset_detection.py    # Finds when vocals start
├── duration_analysis.py  # Compares song lengths
├── batch_test.py        # Tests multiple songs at once
└── requirements.txt     # Required Python packages
```

## How to Use This System

### Step 1: Install Dependencies
```bash
cd /home/spencer/code/open-karaoke/backend/scripts/lyric_alignment
pip install -r requirements.txt
```

### Step 2: Test a Single Song
```bash
python onset_detection.py
```

This will:
- Analyze the "Got Nothing" test song
- Show when vocals actually start vs. when expected
- Display confidence levels for the detection

### Step 3: Test Multiple Songs
```bash
python batch_test.py
```

This will:
- Test all available songs in your library
- Create a report showing alignment issues across your collection
- Identify which songs need timing adjustments

## Understanding the Output

### Single Song Analysis Example

When you run `onset_detection.py`, you'll see output like this:

```
=== ONSET DETECTION RESULTS ===
Song: Got Nothing by Under the Influence of Giants

Method 1 - Energy-based: Vocals start at 22.50s (High confidence)
Method 2 - Spectral: Vocals start at 23.20s (Medium confidence)
Method 3 - Complex Domain: Vocals start at 22.88s (High confidence)
Method 4 - Vocal Frequency: Vocals start at 22.95s (High confidence)

CONSENSUS: Vocals likely start at 22.88s
Expected start (from lyrics): 25.55s
TIMING OFFSET: -2.67 seconds (vocals start 2.67s earlier than expected)

RECOMMENDATION: Lyrics should be shifted 2.67 seconds earlier
```

### What This Means:

- **Detected Start**: 22.88 seconds (when vocals actually begin)
- **Expected Start**: 25.55 seconds (when lyrics say they should begin)
- **Offset**: -2.67 seconds (vocals are 2.67 seconds early)
- **Fix**: Shift all lyric timestamps back by 2.67 seconds

### Confidence Levels:

- **High**: Very reliable detection (>80% confidence)
- **Medium**: Fairly reliable (60-80% confidence)
- **Low**: Less reliable (<60% confidence)

## Batch Testing Output

When you run `batch_test.py`, you'll get a report like:

```
=== BATCH ALIGNMENT ANALYSIS ===
Tested 25 songs from your library

SONGS WITH GOOD ALIGNMENT (offset < 1 second):
✓ Song A - Offset: 0.3s
✓ Song B - Offset: -0.8s

SONGS NEEDING ADJUSTMENT (offset > 1 second):
⚠ Got Nothing - Offset: -2.67s (vocals start early)
⚠ Song C - Offset: +3.2s (vocals start late)
⚠ Song D - Offset: -1.8s (vocals start early)

SUMMARY:
- 15 songs (60%) have good alignment
- 10 songs (40%) need timing adjustments
- Average offset: -1.2 seconds
```

## What You Can Do With These Results

### Option 1: Manual Adjustment
Use the offset values to manually adjust your lyrics files:
- If offset is -2.67s, subtract 2.67 from all timestamps
- If offset is +1.5s, add 1.5 to all timestamps

### Option 2: Automated Correction (Future Feature)
We can build a script that automatically applies these corrections to your lyrics files.

### Option 3: Quality Control
Use this to identify problematic tracks in your library that need attention.

## Technical Details (For Advanced Users)

### Detection Methods Used:
1. **Energy-based**: Looks for sudden increases in audio energy
2. **Spectral**: Analyzes frequency content changes
3. **Complex Domain**: Uses phase information for precise timing
4. **Vocal Frequency**: Focuses on human voice frequency ranges

### Why Multiple Methods?
Different songs have different characteristics:
- Soft intros might need energy-based detection
- Songs with instruments need spectral analysis
- Clean vocals work well with vocal frequency analysis
- Complex domain provides the most precision

### Consensus Algorithm:
We use all 4 methods and take a weighted average based on confidence levels to get the most accurate result.

## Troubleshooting

### "No vocal file found"
- Make sure your song has a `vocals.wav` file in its directory
- Check that Demucs has processed the song to separate vocals

### "Low confidence detection"
- The song might have a very gradual intro
- Try listening to the detected timestamp to verify manually
- Some songs may need manual timing adjustment

### "Large offset detected (>5 seconds)"
- This might indicate a problem with the source files
- Check that the vocal track and lyrics are from the same version of the song

## Next Steps

Based on your feedback, we can:
1. **Build an automated correction system** that applies the offsets to your lyrics files
2. **Create a web interface** to make this easier to use
3. **Add more detection methods** for difficult songs
4. **Integrate with your main karaoke app** for real-time alignment

## Questions?

This system is designed to help you understand and fix timing issues in your karaoke library. The key insight is that we can automatically detect these misalignments and provide specific correction values.

Would you like me to:
- Run the batch test on your entire library?
- Build the automated correction system?
- Create a simpler interface for this analysis?
- Explain any specific part in more detail?
