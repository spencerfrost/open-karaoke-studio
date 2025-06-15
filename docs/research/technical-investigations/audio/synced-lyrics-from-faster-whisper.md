# Issue: Generate Synced Lyrics from Faster Whisper Transcription

## Overview

Create a script that converts Faster Whisper transcription output (with word-level timestamps) into ai-generated synced lyrics that match the format currently used in the Open Karaoke Studio database.

## Background

Based on our ASR model comparison, **Faster Whisper** proved to be the most accurate and efficient model for generating word-level timestamps from vocal tracks. We need to bridge the gap between its output format and the LRC-format synced lyrics currently stored in our database.

## Current State Analysis

### Existing Synced Lyrics Format (LRC)

From database analysis, current synced lyrics use the standard LRC format:

```lrc
[00:13.20] Baby on the way
[00:17.00] I was melting like ice
[00:23.53] On the back of my spine
[00:29.86] Where we goin' tonight
[00:38.47] You know I saw that eye
[00:42.60] In the corner of the light
```

**Format characteristics:**
- Timestamps in `[mm:ss.xx]` format
- Line-based lyrics (not word-level)
- Clean, readable text without word-level timing
- Stored in `generated_lyrics` column as TEXT

### Faster Whisper Output Format

From our test results, Faster Whisper provides:

```json
{
  "segments": [
    {
      "start": 32.34,
      "end": 45.7,
      "text": " credit business fortune teller picnic it's nothing wrong with a little california magic",
      "words": [
        {
          "word": "credit",
          "start": 32.34,
          "end": 33.74,
          "probability": 0.00962066650390625
        },
        {
          "word": "business",
          "start": 33.74,
          "end": 35.14,
          "probability": 0.2705078125
        }
      ]
    }
  ],
  "words": [
    // All words with individual timestamps
  ]
}
```

**Format characteristics:**
- Timestamps in decimal seconds (e.g., 32.34)
- Both segment-level and word-level data
- Confidence scores for each word
- Raw text that may need cleaning

## Requirements

### Core Functionality

1. **Convert Faster Whisper JSON to LRC format**
   - Parse segments and combine words into lyrical lines
   - Convert decimal seconds to `[mm:ss.xx]` format
   - Handle text cleaning and formatting

2. **Intelligent line breaking**
   - Group words into meaningful lines (not just by segments)
   - Consider pause detection between words
   - Respect natural sentence/phrase boundaries
   - Target 3-8 words per line for karaoke readability

3. **Quality filtering**
   - Filter out low-confidence words (probability < 0.3)
   - Handle gaps in transcription gracefully
   - Provide quality metrics for the generated lyrics

4. **Integration with existing database**
   - Update `synced_lyrics` column in songs table
   - Preserve existing lyrics as backup
   - Add metadata about AI-generated status

### Advanced Features (Future)

1. **Word-level timing support**
   - Generate enhanced LRC format with word-level timing
   - Support bouncing ball karaoke effects
   - Store word-level data separately for advanced features

2. **Manual editing interface**
   - Allow users to correct AI-generated lyrics
   - Provide timing adjustment tools
   - Validate against original audio

## Technical Implementation Plan

### Phase 1: Core Conversion Script

**Location:** `/backend/scripts/ai_lyrics/whisper_to_lrc.py`

**Key Functions:**

1. **`parse_whisper_output(json_data) -> LyricsData`**
   - Parse Faster Whisper JSON output
   - Extract segments and words with timing
   - Calculate confidence metrics

2. **`group_words_into_lines(words, max_gap=2.0) -> List[LyricLine]`**
   - Analyze gaps between words to detect natural breaks
   - Group words into lines of appropriate length
   - Consider punctuation and natural speech patterns

3. **`convert_to_lrc(lyric_lines) -> str`**
   - Convert timing from decimal seconds to LRC format
   - Format text appropriately
   - Generate standard LRC output

4. **`quality_assessment(words) -> QualityMetrics`**
   - Calculate average confidence score
   - Identify potential problem areas
   - Provide recommendations for manual review

### Phase 2: Database Integration

**Location:** `/backend/scripts/ai_lyrics/generate_synced_lyrics.py`

**Key Functions:**

1. **`process_song(song_id) -> bool`**
   - Load vocals file for song
   - Run Faster Whisper transcription
   - Convert to LRC format
   - Update database with results

2. **`batch_process(song_filter=None) -> BatchResults`**
   - Process multiple songs
   - Handle errors gracefully
   - Provide progress reporting
   - Generate summary statistics

### Phase 3: API Integration

**Location:** `/backend/app/api/lyrics.py`

**New Endpoints:**

1. **`POST /api/songs/{song_id}/generate-lyrics`**
   - Trigger AI lyrics generation for specific song
   - Return real-time progress updates
   - Handle async processing via Celery

2. **`GET /api/songs/{song_id}/lyrics/quality`**
   - Return quality metrics for AI-generated lyrics
   - Compare with existing lyrics if available

## Implementation Details

### Line Breaking Algorithm

```python
def group_words_into_lines(words, max_gap=2.0, target_words_per_line=5):
    lines = []
    current_line = []
    
    for i, word in enumerate(words):
        current_line.append(word)
        
        # Check for natural break points
        if should_break_line(word, words[i+1:], current_line):
            lines.append(create_line(current_line))
            current_line = []
    
    return lines

def should_break_line(current_word, next_words, current_line):
    # Break if gap is too large (silence)
    if next_words and (next_words[0]['start'] - current_word['end']) > max_gap:
        return True
    
    # Break if line is getting too long
    if len(current_line) >= 8:
        return True
    
    # Break at punctuation
    if current_word['word'].endswith(('.', '!', '?')):
        return True
    
    # Break at natural phrase boundaries
    if current_word['word'].endswith(',') and len(current_line) >= 3:
        return True
    
    return False
```

### Time Format Conversion

```python
def seconds_to_lrc_format(seconds):
    """Convert decimal seconds to LRC timestamp format [mm:ss.xx]"""
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    return f"[{minutes:02d}:{remaining_seconds:05.2f}]"
```

### Quality Assessment

```python
def assess_quality(words, segments):
    return {
        'avg_confidence': sum(w['probability'] for w in words) / len(words),
        'low_confidence_words': len([w for w in words if w['probability'] < 0.3]),
        'total_words': len(words),
        'coverage_percentage': calculate_coverage(segments),
        'timing_consistency': check_timing_gaps(words),
        'recommended_review': determine_review_needed(words, segments)
    }
```

## Database Schema Updates

### New Columns (Optional)

```sql
ALTER TABLE songs ADD COLUMN lyrics_source VARCHAR(50);  -- 'manual', 'ai_generated', 'lrclib'
ALTER TABLE songs ADD COLUMN lyrics_confidence FLOAT;   -- Average confidence score
ALTER TABLE songs ADD COLUMN lyrics_generated_at TIMESTAMP;
ALTER TABLE songs ADD COLUMN word_level_timing TEXT;    -- JSON for future word-level features
```

## Success Criteria

### Quality Metrics

1. **Accuracy**: Generated lyrics should match vocal content ≥85% accuracy
2. **Timing**: Line timestamps should align with vocal phrasing within ±0.5 seconds
3. **Readability**: Lines should be appropriately grouped for karaoke display
4. **Coverage**: At least 90% of vocal content should be captured

### Performance Targets

1. **Processing Speed**: ≤10 seconds for average 4-minute song
2. **Resource Usage**: ≤2GB RAM, ≤50% CPU during processing
3. **Reliability**: ≤5% failure rate across diverse vocal tracks

## Testing Strategy

### Test Cases

1. **Clear vocals with minimal background noise**
2. **Vocals with significant instrumental bleed**
3. **Multiple singers or harmonies**
4. **Non-English content (for robustness)**
5. **Very short songs (≤1 minute)**
6. **Very long songs (≥8 minutes)**

### Validation Process

1. **Compare against existing synced lyrics** from LRCLIB
2. **Manual review of generated content** for accuracy
3. **Timing validation** using karaoke playback
4. **User acceptance testing** with real karaoke use

## Example Output Comparison

### Input (Faster Whisper)
```json
"words": [
  {"word": "You", "start": 14.44, "end": 15.84, "probability": 0.09},
  {"word": "credit", "start": 32.34, "end": 33.74, "probability": 0.01},
  {"word": "business", "start": 33.74, "end": 35.14, "probability": 0.27},
  {"word": "fortune", "start": 35.14, "end": 37.2, "probability": 0.81}
]
```

### Output (LRC Format)
```lrc
[00:14.44] You
[00:32.34] Credit business fortune teller
[00:38.10] It's nothing wrong with a little California magic
```

## Risk Mitigation

### Potential Issues

1. **Poor transcription quality** → Implement confidence thresholds and manual review
2. **Incorrect line breaks** → Allow manual editing and adjustment
3. **Timing drift** → Validate against audio analysis
4. **Memory/performance issues** → Implement processing queues and limits

### Fallback Strategies

1. **Segment-only mode** if word-level timestamps fail
2. **Manual correction interface** for user refinement
3. **Hybrid approach** combining AI with existing lyrics sources

## Future Enhancements

1. **Real-time lyrics generation** during upload process
2. **Interactive timing adjustment** tools
3. **Multi-language support** with automatic detection
4. **Advanced features** like word-level highlighting for karaoke
5. **Training on karaoke-specific data** for better results

## Related Documentation

- [AI Lyrics Generation Guide](../ai_lyrics_generation.md)
- [ASR Experiments Results](../backend/scripts/ai_lyrics/asr_experiments/README.md)
- [Lyric Timing Solutions](../LYRIC_TIMING_SOLUTIONS.md)
- [Database Schema](../backend/app/db/models/song.py)

---

**Priority**: High  
**Estimated Effort**: 2-3 weeks for Phase 1-2  
**Dependencies**: Faster Whisper integration, existing lyrics infrastructure  
**Assignee**: TBD
