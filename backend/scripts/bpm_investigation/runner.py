"""
Main runner for BPM investigation.

This module orchestrates the entire investigation process:
1. Setup output directories
2. Select diverse test songs from database
3. For each song:
   a. Run baseline strategy
   b. Run experimental strategies
   c. Save intermediate results
4. Generate comparative visualizations
5. Generate comprehensive report
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

import librosa

from .config import setup_output_directories
from .models import SongTestResult, StrategyResult
from .report import generate_report
from .song_selection import find_audio_file, select_test_songs
from .strategies import ALL_STRATEGIES
from .visualization import generate_visualizations

logger = logging.getLogger(__name__)


def run_all_strategies(
    audio_path: Path, output_dir: Path, song_id: str
) -> List[StrategyResult]:
    """
    Run all BPM detection strategies on a single audio file.

    Args:
        audio_path: Path to audio file
        output_dir: Directory for output files
        song_id: Identifier for this song

    Returns:
        List of StrategyResult objects
    """
    logger.info(f"Loading audio: {audio_path}")

    # Load audio (same preprocessing as production: 22050 Hz, 90 seconds)
    y, sr = librosa.load(str(audio_path), sr=22050, duration=90)

    logger.info(f"Audio loaded: duration={len(y)/sr:.1f}s, sr={sr}Hz")

    results = []

    for strategy_name, strategy_func in ALL_STRATEGIES:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {strategy_name}")
        logger.info(f"{'='*60}")

        try:
            result = strategy_func(y, sr, output_dir, song_id)
            results.append(result)

            logger.info(f"[OK] {strategy_name} complete:")
            logger.info(
                f"  Final BPM: {result.bpm_candidates[0] if result.bpm_candidates else 'N/A'}"
            )
            logger.info(f"  All Candidates: {[round(c, 1) for c in result.bpm_candidates[:5]]}")
            logger.info(f"  Execution time: {result.execution_time:.2f}s")

        except Exception as e:
            logger.error(f"[FAIL] {strategy_name} failed: {e}", exc_info=True)

    return results


def run_investigation() -> int:
    """
    Main execution flow for BPM accuracy investigation.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    logger.info("=" * 80)
    logger.info("BPM Detection Accuracy Investigation")
    logger.info("=" * 80)

    # Setup output directories
    output_dirs = setup_output_directories()
    logger.info(f"Results will be saved to: {output_dirs['root']}")

    # Select test songs
    test_songs = select_test_songs()
    if not test_songs:
        logger.error("No test songs selected. Exiting.")
        return 1

    logger.info(f"Testing {len(test_songs)} songs with multiple strategies")

    # Initialize results container
    all_results: List[SongTestResult] = []

    # Execute strategies for each test song
    for idx, song in enumerate(test_songs, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"Processing Song {idx}/{len(test_songs)}: {song.title} by {song.artist}")
        logger.info(f"Current BPM: {song.bpm}")
        logger.info(f"{'='*80}")

        # Find audio file
        audio_path = find_audio_file(song.id)
        if not audio_path:
            logger.warning(f"Skipping song {song.id} - no audio file found")
            continue

        # Create song-specific output directory
        song_output_dir = output_dirs["intermediate_audio"] / song.id
        song_plot_dir = output_dirs["plots"] / song.id
        song_output_dir.mkdir(parents=True, exist_ok=True)
        song_plot_dir.mkdir(parents=True, exist_ok=True)

        # Run all strategies
        strategy_results = run_all_strategies(audio_path, song_output_dir, song.id)

        # Collect results
        song_result = SongTestResult(
            song_id=song.id,
            title=song.title,
            artist=song.artist,
            current_bpm=song.bpm,
            audio_file_path=str(audio_path),
            strategy_results=strategy_results,
        )
        all_results.append(song_result)

        # Save intermediate JSON for this song
        song_json = output_dirs["raw_data"] / f"{song.id}_results.json"
        with open(song_json, "w") as f:
            json.dump(song_result.to_dict(), f, indent=2)
        logger.info(f"Song results saved to: {song_json}")

    # Generate visualizations
    generate_visualizations(all_results, output_dirs["plots"])

    # Generate comprehensive report
    generate_report(all_results, output_dirs["root"])

    # Save raw results as JSON
    results_file = output_dirs["raw_data"] / "all_results.json"
    with open(results_file, "w") as f:
        json.dump(
            {
                "timestamp": datetime.now().isoformat(),
                "test_songs_count": len(test_songs),
                "results": [r.to_dict() for r in all_results],
            },
            f,
            indent=2,
        )
    logger.info(f"Raw results saved to: {results_file}")

    logger.info("=" * 80)
    logger.info("Investigation complete!")
    logger.info(f"Results directory: {output_dirs['root']}")
    logger.info("=" * 80)

    return 0


def run_single_file_test(test_file: Path, output_dir: Path | None = None) -> int:
    """
    Run BPM detection strategies on a single audio file.

    Args:
        test_file: Path to the audio file to test
        output_dir: Optional output directory (defaults to bpm_test_output)

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if not test_file.exists():
        logger.error(f"Audio file not found: {test_file}")
        return 1

    output = output_dir or Path("bpm_test_output")
    output.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("BPM Strategy Test Mode - Single File")
    logger.info(f"Input: {test_file}")
    logger.info(f"Output: {output}")
    logger.info("=" * 80)

    # Generate a pseudo song_id from the filename
    song_id = test_file.stem

    # Run all strategies
    results = run_all_strategies(test_file, output, song_id)

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("RESULTS SUMMARY")
    logger.info("=" * 80)

    for result in results:
        top_bpm = result.bpm_candidates[0] if result.bpm_candidates else "N/A"
        logger.info(f"{result.strategy_name}: {top_bpm} BPM ({result.execution_time:.2f}s)")

    return 0
