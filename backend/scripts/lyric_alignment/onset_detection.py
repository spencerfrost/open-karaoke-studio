#!/usr/bin/env python3
"""
Audio onset detection for finding the start of vocals.
Uses librosa for lightweight, fast onset detection without heavy AI models.
"""

import sys
import json
from pathlib import Path
import numpy as np
import librosa

def detect_vocal_onsets(audio_path, min_onset_strength=0.1, search_window=30.0):
    """
    Detect vocal onsets using audio analysis.

    Args:
        audio_path: Path to audio file
        min_onset_strength: Minimum strength for an onset to be considered significant
        search_window: Only analyze first N seconds for efficiency

    Returns:
        dict: Onset detection results
    """

    print(f"🎵 Loading audio: {audio_path}")

    # Load audio (limit to search window for efficiency)
    y, sr = librosa.load(audio_path, duration=search_window)
    total_duration = librosa.get_duration(y=y, sr=sr)

    print(f"📊 Analyzing first {total_duration:.1f} seconds...")

    # Multiple onset detection methods
    results = {
        "audio_file": str(audio_path),
        "analyzed_duration": total_duration,
        "sample_rate": sr,
        "onset_methods": {}
    }

    # Method 1: Energy-based onset detection
    print("🔍 Method 1: Energy-based onset detection...")
    rms_energy = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    rms_times = librosa.frames_to_time(range(len(rms_energy)), sr=sr, hop_length=512)

    # Find first significant energy increase
    avg_energy = np.mean(rms_energy[:int(sr/512)])  # First second average
    energy_threshold = avg_energy + (np.std(rms_energy) * 2)  # 2 std devs above mean

    significant_energy_frames = rms_energy > energy_threshold
    first_energy_onset = None
    if np.any(significant_energy_frames):
        first_energy_idx = np.where(significant_energy_frames)[0][0]
        first_energy_onset = float(rms_times[first_energy_idx])

    results["onset_methods"]["energy_based"] = {
        "first_onset": first_energy_onset,
        "threshold_used": float(energy_threshold),
        "avg_energy": float(avg_energy)
    }

    # Method 2: Spectral onset detection
    print("🔍 Method 2: Spectral onset detection...")
    onset_envelope = librosa.onset.onset_strength(y=y, sr=sr)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_envelope,
        sr=sr,
        units='time',
        delta=min_onset_strength,
        wait=1.0  # Minimum 1 second between onsets
    )

    first_spectral_onset = float(onset_frames[0]) if len(onset_frames) > 0 else None

    results["onset_methods"]["spectral"] = {
        "first_onset": first_spectral_onset,
        "all_onsets": [float(t) for t in onset_frames[:10]],  # First 10 onsets
        "total_onsets": len(onset_frames)
    }

    # Method 3: Complex domain onset detection (good for vocals)
    print("🔍 Method 3: Complex domain onset detection...")
    complex_onset_envelope = librosa.onset.onset_strength(
        y=y, sr=sr, aggregate=np.median
    )
    complex_onset_frames = librosa.onset.onset_detect(
        onset_envelope=complex_onset_envelope,
        sr=sr,
        units='time',
        delta=min_onset_strength * 0.8,  # Slightly more sensitive
        wait=0.5
    )

    first_complex_onset = float(complex_onset_frames[0]) if len(complex_onset_frames) > 0 else None

    results["onset_methods"]["complex"] = {
        "first_onset": first_complex_onset,
        "all_onsets": [float(t) for t in complex_onset_frames[:10]],
        "total_onsets": len(complex_onset_frames)
    }

    # Method 4: High-frequency content analysis (vocal-specific)
    print("🔍 Method 4: High-frequency content analysis...")

    # Focus on frequencies where vocals typically appear (200-4000 Hz)
    stft = librosa.stft(y)
    freqs = librosa.fft_frequencies(sr=sr)
    vocal_freq_mask = (freqs >= 200) & (freqs <= 4000)

    vocal_energy = np.mean(np.abs(stft[vocal_freq_mask, :]), axis=0)
    vocal_times = librosa.frames_to_time(range(len(vocal_energy)), sr=sr)

    # Find first significant vocal frequency content
    vocal_threshold = np.mean(vocal_energy[:int(sr/2048)]) + (np.std(vocal_energy) * 1.5)
    significant_vocal_frames = vocal_energy > vocal_threshold

    first_vocal_onset = None
    if np.any(significant_vocal_frames):
        first_vocal_idx = np.where(significant_vocal_frames)[0][0]
        first_vocal_onset = float(vocal_times[first_vocal_idx])

    results["onset_methods"]["vocal_frequency"] = {
        "first_onset": first_vocal_onset,
        "threshold_used": float(vocal_threshold),
        "avg_vocal_energy": float(np.mean(vocal_energy))
    }

    # Calculate consensus recommendation
    all_onsets = [
        first_energy_onset,
        first_spectral_onset,
        first_complex_onset,
        first_vocal_onset
    ]

    # Filter out None values
    valid_onsets = [t for t in all_onsets if t is not None]

    if valid_onsets:
        # Use median of valid onsets as consensus
        consensus_onset = float(np.median(valid_onsets))
        onset_std = float(np.std(valid_onsets))
        confidence = "high" if onset_std < 0.5 else "medium" if onset_std < 1.0 else "low"
    else:
        consensus_onset = None
        onset_std = None
        confidence = "none"

    results["consensus"] = {
        "recommended_onset": consensus_onset,
        "confidence": confidence,
        "onset_std_dev": onset_std,
        "methods_agreed": len(valid_onsets),
        "individual_onsets": {
            "energy": first_energy_onset,
            "spectral": first_spectral_onset,
            "complex": first_complex_onset,
            "vocal_freq": first_vocal_onset
        }
    }

    return results

def print_onset_analysis(results):
    """Print formatted onset analysis results."""

    print(f"\n📊 ONSET DETECTION RESULTS")
    print("=" * 40)

    consensus = results["consensus"]

    print(f"🎯 Recommended vocal start: ", end="")
    if consensus["recommended_onset"] is not None:
        print(f"{consensus['recommended_onset']:.2f}s")
        print(f"🔍 Confidence: {consensus['confidence']}")
        print(f"📈 Agreement: {consensus['methods_agreed']}/4 methods")
        if consensus["onset_std_dev"] is not None:
            print(f"📊 Std deviation: {consensus['onset_std_dev']:.2f}s")
    else:
        print("❌ No clear onset detected")

    print(f"\n🔬 Individual Method Results:")
    methods = results["onset_methods"]
    for method_name, method_data in methods.items():
        onset_time = method_data["first_onset"]
        if onset_time is not None:
            print(f"  {method_name:15s}: {onset_time:.2f}s")
        else:
            print(f"  {method_name:15s}: No onset detected")

def main():
    if len(sys.argv) < 2:
        print("Usage: python onset_detection.py <audio_file> [options]")
        print()
        print("Options:")
        print("  --sensitivity N    Onset sensitivity (0.01-1.0, default: 0.1)")
        print("  --window N         Analysis window in seconds (default: 30)")
        print()
        print("Examples:")
        print("  python onset_detection.py vocals.mp3")
        print("  python onset_detection.py vocals.mp3 --sensitivity 0.05 --window 15")
        sys.exit(1)

    audio_path = sys.argv[1]

    # Parse options
    sensitivity = 0.1
    window = 30.0

    if "--sensitivity" in sys.argv:
        idx = sys.argv.index("--sensitivity")
        if idx + 1 < len(sys.argv):
            sensitivity = float(sys.argv[idx + 1])

    if "--window" in sys.argv:
        idx = sys.argv.index("--window")
        if idx + 1 < len(sys.argv):
            window = float(sys.argv[idx + 1])

    if not Path(audio_path).exists():
        print(f"❌ Error: Audio file not found: {audio_path}")
        sys.exit(1)

    print(f"🎤 Onset Detection Analysis")
    print("=" * 40)
    print(f"File: {Path(audio_path).name}")
    print(f"Sensitivity: {sensitivity}")
    print(f"Analysis window: {window}s")

    try:
        results = detect_vocal_onsets(audio_path, sensitivity, window)
        print_onset_analysis(results)

        # Save results
        output_file = Path(audio_path).stem + "_onset_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n💾 Analysis saved to: {output_file}")

        if results["consensus"]["recommended_onset"] is not None:
            onset_time = results["consensus"]["recommended_onset"]
            print(f"\n✅ Detected vocal start at {onset_time:.2f}s")
        else:
            print(f"\n⚠️  Could not reliably detect vocal start")
            print("💡 Try adjusting sensitivity or check if audio contains clear vocals")

    except Exception as e:
        print(f"❌ Error during onset detection: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
