# Lyric Alignment Analysis Results

## What We're Testing

We're trying to solve this problem: **The synced lyrics timing doesn't match when vocals actually start in the audio.**

### The Test Case: "Got Nothing" by Under the Influence of Giants

**File tested:** `/karaoke_library/cef0e5e2-e26f-4ee1-881b-368089a25efe/vocals.mp3`

---

## Current Situation (Before Alignment)

### What the Synced Lyrics Say:
```
[00:25.55] I got nothing but all that I need
[00:29.24] With oceans flowing, oceans flowing
[00:35.28] No, I got nothing but all that I need
```
**First lyric should start at:** `25.55 seconds`

### What Our Audio Analysis Found:
```
🎯 Recommended vocal start: 22.88s
🔍 Confidence: low
📈 Agreement: 4/4 methods
📊 Std deviation: 2.66s

🔬 Individual Method Results:
  energy_based   : 25.61s
  spectral       : 20.22s
  complex        : 20.25s
  vocal_frequency: 25.52s
```
**Actual vocals detected at:** `22.88 seconds`

---

## The Alignment Problem

| Item | Expected Time | Detected Time | Difference |
|------|---------------|---------------|------------|
| **First Vocals** | 25.55s | 22.88s | **-2.67s** |

### What This Means:
- The vocals actually start **2.67 seconds EARLIER** than the synced lyrics expect
- If we play synced lyrics as-is, the text will be **2.67 seconds LATE**
- We need to **shift the lyrics earlier by 2.67 seconds** to match the audio

---

## Why Is This Happening?

### Possible Reasons:
1. **Lead-in vocals** - There might be background vocals, "oh yeah", or vocal warm-up before the main lyrics
2. **Synced lyrics are imprecise** - The original timing might be slightly off
3. **Vocal separation artifacts** - The AI separation might have captured some instrumental sounds as "vocals"

### Analysis Quality:
- **✅ All 4 detection methods found vocals** (good sign)
- **⚠️ 2.66s variation between methods** (causes "low confidence")
- **📊 Range: 20.22s to 25.61s** (5.39s spread)

---

## What Should We Do?

### Option 1: Trust the Consensus (22.88s)
- **Shift all synced lyrics earlier by 2.67 seconds**
- First lyric would appear at: `25.55 - 2.67 = 22.88s`
- **Pro:** Matches when vocals actually start
- **Con:** Might be too early if the early vocals are just "ooh" sounds

### Option 2: Trust the Energy-Based Detection (25.61s)
- **Shift synced lyrics earlier by minimal amount: 0.06 seconds**
- Very close to original timing
- **Pro:** Minimal change, stays close to original
- **Con:** Might miss early vocal content

### Option 3: Use the Original Timing (25.55s)
- **No adjustment needed**
- **Pro:** Trusts the original synced lyrics
- **Con:** Might be late if vocals actually start earlier

---

## Recommendation

Based on this analysis, I recommend **Option 1** with some refinement:

1. **Use onset detection as a "reality check"**
2. **If detected start is within 3 seconds of synced lyrics start → make small adjustment**
3. **If detected start is very different → flag for manual review**

### For This Song:
- Detected: 22.88s, Expected: 25.55s
- Difference: 2.67s (within 3s threshold)
- **Recommended adjustment:** Shift lyrics earlier by 2.67s

---

## Next Steps

1. **Test this on more songs** to see if the pattern holds
2. **Create alignment rules** based on confidence and agreement
3. **Build a system** that can automatically detect and fix these alignment issues

---

## Technical Details

### Detection Methods Used:
1. **Energy-based:** Looks for sudden increases in audio energy
2. **Spectral:** Analyzes frequency changes that indicate sound onset
3. **Complex:** Uses advanced signal processing for onset detection
4. **Vocal-frequency:** Focuses on 200-4000Hz range where vocals typically appear

### Files Generated:
- `vocals_onset_analysis.json` - Detailed technical results
- This document - Human-readable summary
