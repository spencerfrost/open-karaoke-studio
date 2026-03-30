# Lyrics Analysis: Section Breaks & Song Structure

Detecting where section breaks belong in synced lyrics and inserting them — so karaoke display has proper verse/chorus separation instead of a wall of text.

---

## The Problem

Synced lyrics from external APIs (LRCLIB, Musixmatch, etc.) arrive as a continuous stream of timestamped lines with no structural separation. A typical song looks like this:

```
[00:15.30] I walked along the avenue
[00:18.45] Thinking about the things we do
[00:21.60] The world was spinning all around
[00:24.80] My feet could barely touch the ground
[00:28.00] And then the chorus hits me hard
[00:31.20] I'm singing underneath the stars
```

There's no indication of where one section ends and another begins. Verses run into choruses, choruses into bridges — all one unbroken block. For karaoke, this makes it harder to follow along. Singers lose their place. There's no visual breathing room.

What it *should* look like:

```
[00:15.30] I walked along the avenue
[00:18.45] Thinking about the things we do
[00:21.60] The world was spinning all around
[00:24.80] My feet could barely touch the ground
[00:26.50]
[00:28.00] And then the chorus hits me hard
[00:31.20] I'm singing underneath the stars
```

That empty timestamped line (`[00:26.50]`) is a section break. Its timestamp marks when the vocalist stops singing at the end of the previous section — not when the next section starts. This is the format some well-formatted LRC files already use, and it's what we want to produce for every song.

A few songs in the library already have these breaks (placed manually or by better sources). Most don't. Out of 906 synced lyrics in the database, the vast majority are unbroken streams.

---

## The Approach

No single analysis method can reliably detect section breaks on its own. A timing gap between two lyrics lines *might* be a section break — or it might just be a slow melody. Silence in the vocals *might* indicate a break — or the singer could be holding a note with no words. A repeated block of text *probably* indicates a chorus — but it could be a pre-chorus or hook.

When multiple methods agree, though, confidence goes up fast. A timing gap + vocal silence + the start of a repeated text block = almost certainly a section break.

The idea is straightforward: run several independent analysis methods, each of which produces candidates for where section breaks might be along with a confidence score, then combine those scores. Where the combined confidence is high, insert a break. Where it's low, leave it alone. Where it's ambiguous, flag it for human review.

This is a well-established pattern in music information retrieval (MIR). It's how tools like MSAF detect song structure — run multiple boundary detectors, fuse the results, and the consensus is more reliable than any single detector.

---

## Analysis Methods

### Analyzing the Lyrics Text

**Repeated line groups.** Choruses repeat. If the same sequence of 3–4 lines appears two or three times in a song, those are almost certainly choruses. The boundaries before and after each occurrence of that repeated block are strong section break candidates. Longer repeated sequences and more repetitions = higher confidence. A repeated 2-line group that appears twice is suggestive; a repeated 4-line group that appears three times is near-certain.

The main limitation: repetition alone can't distinguish a chorus from a pre-chorus or a hook. It tells you *that* something repeats, not *what* it is structurally. But for the purpose of section break detection, that distinction doesn't matter yet — we just need to know where the boundary is.

**Existing section markers.** Some LRC files already contain empty timestamped lines or blank lines at section boundaries. Some lyrics sources include annotations like `(Chorus x2)` or `(Verse)`. When these exist, they're high-confidence signals — someone (or some system) already marked the structure. The challenge is that they're inconsistent across sources and often missing entirely.

**Section annotations from lyrics APIs.** Services like Genius sometimes include section labels — `[Verse 1]`, `[Chorus]`, `[Bridge]` — in their plain-text lyrics. These aren't part of the synced LRC format, but if we can match the text between a Genius annotation and our synced lyrics, we get section labels for free. Coverage is spotty, but when available, it's a strong signal.

### Analyzing LRC Timestamps

**Timing gaps between lines.** The simplest and most readily available signal. If two consecutive lyrics lines are 3+ seconds apart, there's probably a section break between them. But the threshold can't be absolute — a slow ballad at 60 BPM has naturally longer gaps between lines than an uptempo pop song at 130 BPM. The gap needs to be evaluated relative to the song's *median* gap. A gap that's 3x the median is much more meaningful than a gap that happens to be 3 seconds.

Timing gaps are a strong starting signal but produce false positives. A singer might pause mid-verse for dramatic effect, or a long instrumental fill might separate two lines within the same section. Timing gaps need corroboration from other methods.

**Timestamp pattern regularity.** Within a section, lines tend to arrive at a somewhat consistent cadence. Verses have a rhythm to their line spacing; choruses have their own. A disruption in that pattern — where the regular cadence breaks — can signal a section transition. This is a weaker signal than raw gap size but adds corroboration when it aligns with other methods.

### Analyzing the Isolated Vocals

We already have Demucs-separated vocal tracks for every song. This is a powerful asset — analyzing `vocals.mp3` directly tells us when someone is actually singing, without interference from instruments.

**Voice Activity Detection (VAD) / silence detection.** The most direct signal for section breaks. If nobody is singing, it's a break. VAD models (like Silero or WebRTC VAD) are specifically trained to distinguish speech/singing from silence and background noise. Applied to the isolated vocals track, they produce a timeline of "voice present" vs. "voice absent" segments. Stretches of vocal absence that last more than about a second are strong section break candidates.

This is arguably the highest-confidence single signal, because it answers the most fundamental question directly: is the vocalist singing or not? Its main limitation is that some section transitions happen without a clean silence — the singer might sustain a note into the transition, or background vocals might continue while lead vocals pause.

**Vocal energy analysis (RMS).** Similar to VAD but more granular. Instead of a binary voice/no-voice decision, RMS energy gives a continuous measurement of how loud the vocals are over time. Energy valleys — where the vocal volume drops significantly — mark section boundaries. This catches cases where there isn't true silence but there is a clear dip.

Energy analysis also helps characterize sections: choruses typically have higher vocal energy than verses. A transition from low-energy singing to high-energy singing (or vice versa) often coincides with a section change.

**Vocal onset re-entry detection.** Our codebase already has a 4-method onset consensus system that detects when vocals first begin in a song. The same approach — running multiple onset detection methods and taking the consensus — can be extended to detect *all* points where vocals re-enter after a gap, not just the first one. Each re-entry point is the start of a new section (or at least the end of a break).

### Analyzing the Instrumental / Full Audio

**Energy profile changes.** The overall energy of a song shifts at section boundaries. Choruses are typically louder and denser than verses. Bridges often have a distinct energy signature — a drop followed by a build. Analyzing the energy contour of the full mix (or the instrumental track) reveals these structural transitions. Where the energy profile shifts significantly, there's likely a section boundary.

**Harmonic self-similarity.** This is a more sophisticated technique from MIR. The idea: compute the harmonic content (chroma features — a 12-dimensional representation of which pitch classes are present) at every moment in the song, then compare every moment to every other moment. This produces a self-similarity matrix. Within a section, the harmonic content tends to be self-similar (same chord progression repeating). At section boundaries, the harmonic content changes — producing "novelty peaks" that mark transitions.

This is powerful because it detects structure at a musical level, not just a sonic one. Two sections might have similar energy and vocal presence but completely different chord progressions — harmonic analysis catches that.

**Drum/percussion pattern changes.** Using harmonic-percussive source separation (HPSS), the percussive component can be isolated from the full mix. Changes in drum patterns often mark section boundaries — a fill leading into a chorus, a stripped-down verse with minimal percussion, a bridge with a completely different groove. This is a supplementary signal, not a primary one, but it adds corroboration.

### Using ML Models

**Song structure segmentation models.** Models like allin1 (all-in-one) are trained specifically to segment songs into labeled sections — intro, verse, chorus, bridge, outro — with confidence scores for each. They analyze the full audio and output a complete structural map. This is the most direct approach to the problem: ask a model that was trained on thousands of labeled songs to tell you where the sections are.

The trade-off is cost. These models require significant computation (GPU preferred) and large model weights (~500MB+). But the output is exactly what we want — labeled section boundaries with confidence.

**Whisper / whisperX forced alignment.** Speech-to-text models like Whisper, especially with forced alignment extensions like whisperX, produce word-level timestamps — the exact start and end time of each word. This is valuable for two reasons:

1. It tells us precisely when each word ends, which is critical for placing the section break timestamp. If the last word of a verse is "ground" and Whisper says it ends at 24.6 seconds, that's our starting point for the break timestamp.

2. Gaps in Whisper's output (stretches where it detects no speech) corroborate vocal silence detection.

### Placing the Break Timestamp

Detecting *where* a section break belongs (between which lines) is only half the problem. We also need to determine *when* — the timestamp for the empty LRC line.

The timestamp should mark when the vocalist actually stops producing sound at the end of a section. This is where Whisper and vocal audio analysis complement each other:

- **Whisper** tells us *which word* is last in the section and gives an approximate end time for that word. But Whisper is trained on speech, not singing. A held note — someone singing "youuuuuu" for three seconds — might get a word-end timestamp that cuts off well before the vocalist actually stops. Whisper sees the phoneme as "done" even though sound continues.

- **Vocal energy / VAD** on the isolated vocals tells us *when the sound actually stops*, regardless of what the word was. It captures held notes, vibrato tails, and fading vocals that Whisper misses.

The break timestamp should be the point where vocal sound actually ceases — informed by both Whisper's word boundary and the audio's energy envelope. In practice: start from Whisper's end-of-word timestamp, then extend forward until vocal energy drops below a threshold. That's when the vocalist is truly done with the section.

---

## How Methods Reinforce Each Other

The value of combining methods isn't just additive — certain combinations are qualitatively more reliable than any individual signal:

**Timing gap + vocal silence + text repetition boundary = near-certain section break.** If there's a 3-second gap in the LRC timestamps, AND the vocals are silent during that gap, AND the text after the gap is the start of a repeated block (chorus), that's as confident as it gets. Each signal independently suggests a break; together, they're conclusive.

**Timing gap alone, no vocal silence = probably not a break.** A gap in the timestamps but continuous singing through it? The timestamps might just reflect a slow part of the melody, or the LRC source might have imprecise timing. Without corroboration from the audio, a timing gap is merely suggestive.

**Vocal silence + energy drop, but no timing gap = suspicious timestamps.** If the vocalist clearly stops singing for 2+ seconds but the LRC timestamps show no gap, something is wrong with the timestamps — they might be shifted or inaccurate. This is worth flagging for review rather than blindly inserting a break.

**ML structure model agrees with text + timing signals = high confidence with structural labels.** When an ML model says "chorus starts here" and the text repetition analysis also identified that block as a repeated section, we can confidently label the section, not just mark the break.

**Contradictory signals = flag for human review.** When methods disagree — one says break, another says no — the combined confidence drops. Rather than guessing, the system flags the song for manual review. Over time, patterns in human corrections can inform weight adjustments.

---

## Song Structure as a Byproduct

Section break detection and song structure labeling are the same problem at different levels of detail. Once you can reliably detect where breaks belong, you're most of the way to labeling what's on either side of them.

The progression is natural:

1. **Detect breaks** — "there's a section boundary between lines 8 and 9"
2. **Group sections** — "lines 1–8 are one section, lines 9–16 are another"
3. **Identify repeated sections** — "lines 9–16 have the same text as lines 25–32, so they're the same section type"
4. **Label sections** — "the repeated section is probably the chorus; the non-repeated section before it is probably verse 1"

Steps 1 and 2 fall out directly from break detection. Step 3 comes from text repetition analysis (which we're already doing for break detection). Step 4 is where energy analysis, harmonic features, and ML models add the most value — but even basic heuristics get surprisingly far (first section = intro or verse, first repeated section = chorus, short unique section after chorus = bridge).

Structure labeling isn't a separate system — it's the next layer on top of break detection, using the same signals.

---

## What We Already Have

The codebase has several building blocks that apply directly:

- **Vocal separation** — Demucs already produces isolated vocal and instrumental tracks for every processed song. This is the key upstream asset that makes vocal analysis possible without building anything new.
- **Onset detection** — A 4-method consensus system (energy, spectral, complex domain, vocal frequency band) with confidence scoring based on agreement. Currently finds the first vocal onset; the same approach extends to finding all vocal re-entries.
- **Vocal energy analysis** — RMS energy computation, pitch tracking, and loudness measurement are all in production services.
- **Instrumental gap detection** — The frontend already detects timing gaps ≥ 2 seconds in LRC files for triggering count-in displays. The same logic applies to section break detection.
- **Lyrics versioning** — The lyrics system supports multiple versions per song with an active/inactive flag. Analysis-produced lyrics can be saved as a new version while preserving the original — making all changes reversible.

---

## Open Questions

1. **Should analysis run automatically on song import, or on-demand?** The cheap text/timing analysis could run automatically. Audio analysis is heavier — maybe triggered from the admin panel or as a batch job.

2. **How should results surface in the admin panel?** A dedicated "Lyrics Review" tab? Inline indicators on song cards showing which songs have low-confidence or missing section breaks?

3. **Auto-apply or require approval?** High-confidence breaks could be applied automatically (saved as a new lyrics version, original preserved). But should even high-confidence results require a human to approve them first?

4. **What about songs that already have section breaks?** Some LRC files arrive with breaks that may be in the wrong places. Should the system validate existing breaks, or only add breaks to songs that have none?
