#!/usr/bin/env python3
"""
Compare all ASR models side-by-side.
This script runs all available ASR models on the same audio file and compares results.
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import torch


def get_device_info():
    """Get device information for consistent reporting"""
    if torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        print(f"🚀 CUDA detected: {gpu_name}")
        return device, gpu_name
    else:
        print("💻 Using CPU (CUDA not available)")
        return "cpu", "CPU"


def run_faster_whisper(audio_path: str) -> Optional[Dict[str, Any]]:
    """Run Faster Whisper test"""
    try:
        from test_faster_whisper import test_faster_whisper

        print("🚀 Testing Faster Whisper...")
        result = test_faster_whisper(audio_path)  # Fixed: only one argument
        result["model_name"] = "faster-whisper"
        return result
    except Exception as e:
        print(f"❌ Faster Whisper failed: {e}")
        return None


def run_whisper(audio_path: str) -> Optional[Dict[str, Any]]:
    """Run Original Whisper test"""
    try:
        from test_whisper import test_whisper

        print("🚀 Testing Original Whisper...")
        result = test_whisper(audio_path, "base")
        result["model_name"] = "whisper"
        return result
    except Exception as e:
        print(f"❌ Original Whisper failed: {e}")
        return None


def run_insanely_fast_whisper(audio_path: str) -> Optional[Dict[str, Any]]:
    """Run Insanely Fast Whisper test"""
    try:
        from test_insanely_fast_whisper import test_insanely_fast_whisper

        print("🚀 Testing Insanely Fast Whisper...")
        result = test_insanely_fast_whisper(audio_path)  # Simplified call
        result["model_name"] = "insanely-fast-whisper"
        return result
    except Exception as e:
        print(f"❌ Insanely Fast Whisper failed: {e}")
        return None


def run_all_models(audio_path: str) -> Dict[str, Any]:
    """Run all available ASR models on the same audio file"""
    print(f"🎤 Comparing ASR models on: {audio_path}")
    print("=" * 60)

    results = {}

    # Test Faster Whisper
    result = run_faster_whisper(audio_path)
    if result:
        results["faster_whisper"] = result
    print()

    # Test Original Whisper
    result = run_whisper(audio_path)
    if result:
        results["whisper"] = result
    print()

    # Test Insanely Fast Whisper
    result = run_insanely_fast_whisper(audio_path)
    if result:
        results["insanely_fast_whisper"] = result
    print()

    return results


def analyze_results(results: Dict[str, Any]) -> pd.DataFrame:
    """Analyze and compare results from different models"""
    comparison_data = []

    for model_name, result in results.items():
        if result is None:
            continue

        # Calculate metrics
        processing_time = result.get("processing_time", 0)
        total_words = len(result.get("words", []))
        total_segments = len(result.get("segments", []))
        avg_words_per_segment = total_words / max(total_segments, 1)

        # Get first word timing
        first_word_time = None
        if result.get("words"):
            first_word_time = result["words"][0].get("start", None)

        # Get text length
        text_length = len(result.get("text", ""))

        comparison_data.append(
            {
                "Model": model_name.replace("_", " ").title(),
                "Processing Time (s)": round(processing_time, 2),
                "Total Words": total_words,
                "Total Segments": total_segments,
                "Avg Words/Segment": round(avg_words_per_segment, 1),
                "First Word (s)": (
                    round(first_word_time, 2) if first_word_time else "N/A"
                ),
                "Text Length": text_length,
                "Language": result.get("detected_language", "unknown"),
            }
        )

    return pd.DataFrame(comparison_data)


def compare_transcriptions(results: Dict[str, Any]) -> None:
    """Compare the actual transcription text between models"""
    print("📝 TRANSCRIPTION COMPARISON")
    print("=" * 60)

    for model_name, result in results.items():
        if result:
            text = result.get("text", "")
            print(f"\n{model_name.replace('_', ' ').title()}:")
            print(f"'{text}'")


def analyze_timing_precision(results: Dict[str, Any]) -> None:
    """Analyze timing precision across models"""
    print("\n⏱️  TIMING ANALYSIS")
    print("=" * 60)

    for model_name, result in results.items():
        if result and result.get("words"):
            words = result["words"]

            # Calculate timing stats
            word_durations = []
            gaps_between_words = []

            for i, word in enumerate(words):
                duration = word.get("end", 0) - word.get("start", 0)
                word_durations.append(duration)

                if i > 0:
                    gap = word.get("start", 0) - words[i - 1].get("end", 0)
                    gaps_between_words.append(gap)

            if word_durations:
                avg_duration = sum(word_durations) / len(word_durations)
                avg_gap = (
                    sum(gaps_between_words) / len(gaps_between_words)
                    if gaps_between_words
                    else 0
                )

                print(f"\n{model_name.replace('_', ' ').title()}:")
                print(f"  Average word duration: {avg_duration:.3f}s")
                print(f"  Average gap between words: {avg_gap:.3f}s")
                print(
                    f"  Total audio span: {words[-1].get('end', 0) - words[0].get('start', 0):.2f}s"
                )


def save_detailed_comparison(results: Dict[str, Any], output_path: str):
    """Save detailed comparison results"""
    comparison = {
        "summary": {
            "total_models_tested": len([r for r in results.values() if r is not None]),
            "successful_models": list(results.keys()),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "detailed_results": results,
        "word_level_comparison": {},
    }

    # Create word-level comparison
    for model_name, result in results.items():
        if result and "words" in result:
            comparison["word_level_comparison"][model_name] = result["words"]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)


def main():
    if len(sys.argv) < 2:
        print("Usage: python compare_models.py <audio_file>")
        print("Example: python compare_models.py /path/to/vocals.mp3")
        sys.exit(1)

    audio_file = sys.argv[1]

    if not Path(audio_file).exists():
        print(f"❌ Error: Audio file '{audio_file}' not found")
        sys.exit(1)

    # Run all models
    results = run_all_models(audio_file)

    if not results:
        print("❌ No models produced results. Check your installation.")
        sys.exit(1)

    # Analyze results
    print("📊 PERFORMANCE COMPARISON")
    print("=" * 60)
    df = analyze_results(results)
    print(df.to_string(index=False))

    # Compare transcriptions
    compare_transcriptions(results)

    # Analyze timing precision
    analyze_timing_precision(results)

    # Save results
    output_file = "model_comparison_results.json"
    save_detailed_comparison(results, output_file)

    # Save summary CSV
    csv_file = "model_comparison_summary.csv"
    df.to_csv(csv_file, index=False)

    print(f"\n💾 Detailed results saved to: {output_file}")
    print(f"💾 Summary saved to: {csv_file}")
    print("\n✅ Model comparison completed!")

    # Recommendations
    print("\n💡 RECOMMENDATIONS")
    print("=" * 60)
    if len(results) > 1:
        fastest_model = min(
            results.items(),
            key=lambda x: (
                x[1].get("processing_time", float("inf")) if x[1] else float("inf")
            ),
        )
        most_words_model = max(
            results.items(), key=lambda x: len(x[1].get("words", [])) if x[1] else 0
        )

        print(
            f"🏃 Fastest model: {fastest_model[0]} ({fastest_model[1].get('processing_time', 0):.2f}s)"
        )
        print(
            f"🎯 Most detailed transcription: {most_words_model[0]} ({len(most_words_model[1].get('words', []))} words)"
        )
    else:
        print("Run with multiple working models for recommendations.")


if __name__ == "__main__":
    main()
