#!/usr/bin/env python3
"""
Align synced lyrics with vocal timing using ASR.
This script takes both an audio file AND synced lyrics to find the optimal alignment.
"""

import sys
import json
import re
from pathlib import Path
from faster_whisper import WhisperModel

def parse_synced_lyrics(lyrics_content):
    """
    Parse synced lyrics to extract the first few words/phrases.
    Supports LRC format: [mm:ss.xx]text
    
    Returns:
        list: First few phrases with their expected timestamps
    """
    lines = lyrics_content.strip().split('\n')
    synced_phrases = []
    
    for line in lines:
        # Match LRC format: [mm:ss.xx] or [mm:ss] 
        match = re.match(r'\[(\d{1,2}):(\d{2})(?:\.(\d{2}))?\]\s*(.*)', line.strip())
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            centiseconds = int(match.group(3)) if match.group(3) else 0
            text = match.group(4).strip()
            
            if text:  # Skip empty lines
                timestamp = minutes * 60 + seconds + centiseconds / 100
                synced_phrases.append({
                    "timestamp": timestamp,
                    "text": text,
                    "words": text.lower().split()
                })
    
    return synced_phrases

def align_lyrics_with_audio(audio_path, synced_lyrics_content=None, search_window=30.0):
    """
    Align synced lyrics with the actual vocal timing in an audio track.
    
    Args:
        audio_path: Path to the audio file
        synced_lyrics_content: String content of synced lyrics (LRC format)
        search_window: How many seconds to search for the first phrase
    
    Returns:
        dict: Results including alignment offset and analysis
    """
    
    print(f"🎵 Aligning lyrics with vocals in: {audio_path}")
    print("=" * 50)
    
    # Parse synced lyrics
    if synced_lyrics_content:
        synced_phrases = parse_synced_lyrics(synced_lyrics_content)
        if not synced_phrases:
            print("❌ No synced lyrics found in provided content")
            return None
        
        first_phrase = synced_phrases[0]
        target_words = first_phrase["words"][:5]  # First 5 words
        expected_time = first_phrase["timestamp"]
        
        print(f"🎯 Looking for: '{' '.join(target_words)}'")
        print(f"📅 Expected at: {expected_time:.2f}s according to synced lyrics")
    else:
        print("⚠️  No synced lyrics provided - will analyze all vocals")
        target_words = None
        expected_time = 0.0
    
    # Initialize ASR model
    print("🤖 Loading Whisper model...")
    model = WhisperModel("small", device="cpu", compute_type="int8")
    
    # Transcribe with word timestamps
    print("🎤 Transcribing vocals...")
    segments, info = model.transcribe(
        audio_path, 
        beam_size=5,
        word_timestamps=True,
        language="en"
    )
    
    # Extract all words with timestamps
    all_words = []
    for segment in segments:
        if hasattr(segment, 'words') and segment.words:
            for word in segment.words:
                all_words.append({
                    "word": word.word.strip().lower(),
                    "start": word.start,
                    "end": word.end,
                    "probability": word.probability
                })
    
    results = {
        "audio_file": str(audio_path),
        "duration": info.duration,
        "language": info.language,
        "synced_lyrics": {
            "provided": synced_lyrics_content is not None,
            "first_phrase": first_phrase if synced_lyrics_content else None,
            "target_words": target_words,
            "expected_time": expected_time
        },
        "detected_words": all_words[:20],  # First 20 words
        "alignment": {
            "found_match": False,
            "actual_time": None,
            "offset_needed": None,
            "confidence": None
        }
    }
    
    # If we have target words, try to find them in the audio
    if target_words:
        print(f"\n🔍 Searching for target phrase in first {search_window}s...")
        
        best_match = find_phrase_in_audio(target_words, all_words, search_window)
        
        if best_match:
            actual_time = best_match["start_time"]
            offset = actual_time - expected_time
            
            results["alignment"].update({
                "found_match": True,
                "actual_time": actual_time,
                "offset_needed": offset,
                "confidence": best_match["confidence"],
                "matched_words": best_match["matched_words"]
            })
            
            print(f"✅ Found phrase at: {actual_time:.2f}s")
            print(f"📊 Offset needed: {offset:+.2f}s")
            if offset > 0:
                print(f"   → Vocals start {offset:.2f}s LATER than expected")
            elif offset < 0:
                print(f"   → Vocals start {abs(offset):.2f}s EARLIER than expected")
            else:
                print(f"   → Perfect alignment!")
        else:
            print("❌ Could not find target phrase in audio")
    
    # Show first few detected words for reference
    print(f"\n📝 First words detected in audio:")
    for i, word in enumerate(all_words[:10]):
        print(f"  {i+1:2d}. '{word['word']}' at {word['start']:.2f}s")
    
    return results

def find_phrase_in_audio(target_words, audio_words, search_window):
    """
    Find the best match for target words in the audio transcript.
    
    Returns:
        dict: Match info with start_time, confidence, and matched_words
    """
    target_text = ' '.join(target_words).lower()
    best_match = None
    best_score = 0
    
    # Search through audio words within the time window
    for i in range(len(audio_words)):
        word = audio_words[i]
        
        # Only search within the specified time window
        if word["start"] > search_window:
            break
        
        # Try matching sequences of different lengths
        for length in range(1, min(len(target_words) + 1, len(audio_words) - i + 1)):
            audio_sequence = audio_words[i:i+length]
            audio_text = ' '.join([w["word"] for w in audio_sequence])
            
            # Calculate similarity score
            score = calculate_text_similarity(target_text, audio_text)
            
            if score > best_score and score > 0.6:  # Minimum 60% similarity
                avg_confidence = sum(w["probability"] for w in audio_sequence) / len(audio_sequence)
                best_score = score
                best_match = {
                    "start_time": audio_sequence[0]["start"],
                    "end_time": audio_sequence[-1]["end"],
                    "confidence": score * avg_confidence,
                    "matched_words": audio_text,
                    "target_words": target_text
                }
    
    return best_match

def calculate_text_similarity(text1, text2):
    """Simple text similarity based on word overlap."""
    words1 = set(text1.split())
    words2 = set(text2.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)

def main():
    if len(sys.argv) < 2:
        print("Usage: python align_lyrics_with_audio.py <audio_file> [lyrics_file]")
        print()
        print("Examples:")
        print("  python align_lyrics_with_audio.py vocals.mp3 synced_lyrics.lrc")
        print("  python align_lyrics_with_audio.py vocals.mp3")
        print()
        print("If no lyrics file is provided, will analyze the audio alone.")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    lyrics_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not Path(audio_path).exists():
        print(f"❌ Error: Audio file not found: {audio_path}")
        sys.exit(1)
    
    # Load synced lyrics if provided
    synced_lyrics_content = None
    if lyrics_path:
        if not Path(lyrics_path).exists():
            print(f"❌ Error: Lyrics file not found: {lyrics_path}")
            sys.exit(1)
        
        with open(lyrics_path, 'r', encoding='utf-8') as f:
            synced_lyrics_content = f.read()
    
    try:
        results = align_lyrics_with_audio(audio_path, synced_lyrics_content)
        
        if results:
            # Save results
            output_file = Path(audio_path).stem + "_alignment_results.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\n💾 Results saved to: {output_file}")
            
            if results["alignment"]["found_match"]:
                offset = results["alignment"]["offset_needed"]
                print(f"\n🎯 ALIGNMENT SUMMARY")
                print(f"Recommended offset: {offset:+.2f} seconds")
            else:
                print(f"\n⚠️  Could not determine alignment automatically")
        
    except Exception as e:
        print(f"❌ Error processing alignment: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
