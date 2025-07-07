#!/usr/bin/env python3
"""
Quick test script to find a sample vocals file and run ASR on it.
This will automatically pick a vocals.mp3 from your karaoke library.
"""

import random
import sys
from pathlib import Path


def find_sample_vocals():
    """Find a sample vocals.mp3 file from the karaoke library."""

    # Look for the karaoke library
    possible_paths = [
        Path("/home/spencer/code/open-karaoke-studio/karaoke_library"),
        Path("../../../karaoke_library"),
        Path("../../karaoke_library"),
        Path("./karaoke_library"),
    ]

    library_path = None
    for path in possible_paths:
        if path.exists() and path.is_dir():
            library_path = path.resolve()
            break

    if not library_path:
        print("❌ Could not find karaoke_library directory")
        return None

    print(f"🔍 Searching for vocals in: {library_path}")

    # Find all vocals.mp3 files
    vocals_files = list(library_path.glob("*/vocals.mp3"))

    if not vocals_files:
        print("❌ No vocals.mp3 files found in karaoke library")
        return None

    print(f"📁 Found {len(vocals_files)} vocal tracks")

    # Pick a random one
    sample_file = random.choice(vocals_files)
    print(f"🎵 Selected: {sample_file}")

    return sample_file


def main():
    print("🎤 ASR Quick Test - Finding Sample Vocals")
    print("=" * 50)

    vocals_file = find_sample_vocals()
    if not vocals_file:
        print("\n💡 Manual usage:")
        print("python test_faster_whisper.py /path/to/vocals.mp3")
        print("python test_vocal_start.py /path/to/vocals.mp3")
        return 1

    print(f"\n🚀 Running ASR test on: {vocals_file.name}")
    print("=" * 50)

    # Import and run the vocal start detection
    try:
        from test_vocal_start import detect_vocal_start

        results = detect_vocal_start(str(vocals_file))

        print("\n" + "=" * 50)
        print("🎯 QUICK TEST RESULTS")
        print("=" * 50)

        recommended_time = results["analysis"]["recommended_start_time"]
        first_word = (
            results["analysis"]["first_meaningful_word"]
            or results["analysis"]["first_word"]
        )

        print(f"File: {vocals_file.name}")
        print(f"Recommended vocal start: {recommended_time:.2f} seconds")
        if first_word:
            print(f"First word: '{first_word}'")

        print(f"\n✅ Success! Check the generated JSON files for detailed results.")

    except ImportError:
        print("❌ Could not import test modules. Make sure to run setup.py first!")
        return 1
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
