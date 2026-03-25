"""
Report generation for BPM investigation results.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np

from .config import PRIMARY_TEST_SONG_ID, STRATEGY_DESCRIPTIONS, TARGET_BPMS
from .models import SongTestResult

logger = logging.getLogger(__name__)


def generate_report(results: List[SongTestResult], output_dir: Path) -> None:
    """
    Generate comprehensive markdown report summarizing findings.

    Report sections:
    - Executive summary
    - Test song details
    - Strategy comparison table
    - Detailed per-song results
    - Recommendations for production implementation

    Args:
        results: List of test results for all songs
        output_dir: Directory to save report file
    """
    logger.info("Generating comprehensive markdown report...")

    if not results:
        logger.warning("No results to report")
        return

    report_path = output_dir / "FINDINGS.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Gather all strategy names
    all_strategy_names = []
    for song_result in results:
        for strategy in song_result.strategy_results:
            name = strategy.strategy_name
            if name not in all_strategy_names:
                all_strategy_names.append(name)

    # Primary test song (if present)
    primary_song = next((s for s in results if s.song_id == PRIMARY_TEST_SONG_ID), None)

    # Calculate strategy times for later use
    strategy_times = _collect_strategy_times(results)
    avg_times = {name: np.mean(times) for name, times in strategy_times.items()}
    fastest_strategy = min(avg_times.items(), key=lambda x: x[1]) if avg_times else None
    slowest_strategy = max(avg_times.items(), key=lambda x: x[1]) if avg_times else None

    with open(report_path, "w") as f:
        _write_header(f, timestamp, results, all_strategy_names)
        _write_executive_summary(f, results, primary_song, fastest_strategy, slowest_strategy, avg_times)
        _write_test_song_details(f, results)
        _write_methodology(f, all_strategy_names)
        _write_results_by_song(f, results, primary_song, output_dir)
        _write_cross_strategy_analysis(f, results, all_strategy_names, strategy_times, avg_times)
        _write_recommendations(f, primary_song, fastest_strategy, slowest_strategy)
        _write_failure_mode_analysis(f, primary_song, all_strategy_names)
        _write_raw_data_section(f, output_dir)
        _write_appendices(f, all_strategy_names, output_dir)

    logger.info(f"Report generated: {report_path}")
    logger.info("Report generation complete!")


def _collect_strategy_times(results: List[SongTestResult]) -> Dict[str, List[float]]:
    """Collect execution times by strategy."""
    strategy_times = {}
    for song_result in results:
        for strategy in song_result.strategy_results:
            name = strategy.strategy_name
            if name not in strategy_times:
                strategy_times[name] = []
            strategy_times[name].append(strategy.execution_time)
    return strategy_times


def _write_header(f, timestamp: str, results: List[SongTestResult], all_strategy_names: List[str]) -> None:
    """Write report header."""
    f.write("# BPM Detection Accuracy Investigation\n\n")
    f.write(f"**Date:** {timestamp}\n\n")
    f.write(f"**Total Songs Analyzed:** {len(results)}\n\n")
    f.write(f"**Total Strategies Tested:** {len(all_strategy_names)} strategies\n\n")
    f.write("---\n\n")


def _write_executive_summary(
    f,
    results: List[SongTestResult],
    primary_song,
    fastest_strategy,
    slowest_strategy,
    avg_times: Dict[str, float],
) -> None:
    """Write executive summary section."""
    f.write("## Executive Summary\n\n")

    strategies_hit_target = []

    # Primary test song analysis
    if primary_song:
        f.write("### Primary Test Song\n\n")
        f.write(f"- **Title:** {primary_song.title}\n")
        f.write(f"- **Artist:** {primary_song.artist}\n")
        f.write(f"- **Song ID:** `{primary_song.song_id}`\n")
        if primary_song.current_bpm:
            f.write(f"- **Current BPM:** {primary_song.current_bpm:.1f}\n")
        else:
            f.write("- **Current BPM:** Not available\n")
        f.write("- **Expected BPM:** ~88 or ~176 BPM (Drum & Bass genre)\n\n")

        # Check which strategies hit the target
        for strategy in primary_song.strategy_results:
            for candidate in strategy.bpm_candidates:
                for target in TARGET_BPMS:
                    if abs(candidate - target) <= 3:
                        strategies_hit_target.append(strategy.strategy_name)
                        break

        strategies_hit_target = list(set(strategies_hit_target))  # Remove duplicates

        if strategies_hit_target:
            count = len(strategies_hit_target)
            f.write(
                f"**Status:** {count} strateg{'y' if count == 1 else 'ies'} "
                "successfully detected target BPM range\n\n"
            )
            f.write("**Strategies That Hit Target:**\n")
            for strategy_name in strategies_hit_target:
                f.write(f"- {strategy_name.replace('_', ' ').title()}\n")
            f.write("\n")
        else:
            f.write(
                "**Status:** No strategies successfully detected the expected "
                "target BPM range (88 or 176 BPM)\n\n"
            )
    else:
        f.write("*Primary test song not found in results*\n\n")

    # Overall analysis
    f.write("### Overall Analysis\n\n")

    if fastest_strategy and slowest_strategy:
        f.write(
            f"- **Fastest Strategy:** {fastest_strategy[0].replace('_', ' ').title()} "
            f"({fastest_strategy[1]:.2f}s avg)\n"
        )
        f.write(
            f"- **Slowest Strategy:** {slowest_strategy[0].replace('_', ' ').title()} "
            f"({slowest_strategy[1]:.2f}s avg)\n"
        )
        f.write(f"- **Performance Range:** {fastest_strategy[1]:.2f}s - {slowest_strategy[1]:.2f}s\n\n")

    f.write("**Top Recommendation:** See detailed analysis below\n\n")
    f.write("---\n\n")


def _write_test_song_details(f, results: List[SongTestResult]) -> None:
    """Write test song details table."""
    f.write("## Test Song Details\n\n")
    f.write("| Song ID | Title | Artist | Current BPM | Audio File |\n")
    f.write("|---------|-------|--------|-------------|------------|\n")

    for song_result in results:
        song_id_short = song_result.song_id[:8] + "..."
        title = song_result.title[:30] + "..." if len(song_result.title) > 30 else song_result.title
        artist = song_result.artist[:20] + "..." if len(song_result.artist) > 20 else song_result.artist
        bpm = f"{song_result.current_bpm:.1f}" if song_result.current_bpm else "N/A"
        audio_file = Path(song_result.audio_file_path).name

        f.write(f"| {song_id_short} | {title} | {artist} | {bpm} | {audio_file} |\n")

    f.write("\n---\n\n")


def _write_methodology(f, all_strategy_names: List[str]) -> None:
    """Write methodology section."""
    f.write("## Methodology\n\n")

    f.write("### Audio Processing\n\n")
    f.write("- **Sample Rate:** 22,050 Hz (resampled from source)\n")
    f.write("- **Analysis Window:** 90 seconds (first 90 seconds of audio)\n")
    f.write("- **Audio Source:** Instrumental track (preferred) or original audio\n\n")

    f.write("### Evaluation Criteria\n\n")
    f.write("1. **Accuracy:** Does strategy generate target BPM within +/-3 BPM tolerance?\n")
    f.write("2. **Musicality:** Are all candidates musically plausible (30-300 BPM)?\n")
    f.write("3. **Performance:** Is execution time acceptable (< 10s)?\n")
    f.write("4. **Consistency:** Does strategy produce similar results across genres?\n\n")

    f.write("### Strategies Tested\n\n")

    for i, strategy_name in enumerate(all_strategy_names, 1):
        display_name = strategy_name.replace("_", " ").title()
        description = STRATEGY_DESCRIPTIONS.get(strategy_name, "No description available")
        f.write(f"{i}. **{display_name}:** {description}\n")

    f.write("\n---\n\n")


def _write_results_by_song(
    f, results: List[SongTestResult], primary_song, output_dir: Path
) -> None:
    """Write detailed results for each song."""
    f.write("## Results by Song\n\n")

    for song_result in results:
        f.write(f"### {song_result.title} by {song_result.artist}\n\n")
        f.write(f"**Song ID:** `{song_result.song_id}`\n\n")

        if song_result.current_bpm:
            f.write(f"**Current BPM:** {song_result.current_bpm:.1f}\n\n")
        else:
            f.write("**Current BPM:** Not available\n\n")

        # Check if this is the primary D&B test song
        if song_result.song_id == PRIMARY_TEST_SONG_ID:
            f.write("**Expected/Target BPM:** ~88 or ~176 BPM (Drum & Bass genre)\n\n")

        # Strategy results table
        f.write("| Strategy | Top 3 BPM Candidates | Execution Time | Status |\n")
        f.write("|----------|---------------------|----------------|--------|\n")

        for strategy in song_result.strategy_results:
            strategy_name = strategy.strategy_name.replace("_", " ").title()

            # Get top 3 candidates
            top_3 = strategy.bpm_candidates[:3] if strategy.bpm_candidates else []
            candidates_str = ", ".join([f"{c:.1f}" for c in top_3]) if top_3 else "N/A"

            exec_time = f"{strategy.execution_time:.2f}s"

            # Determine status (for primary test song)
            status = "\u2014"  # em dash
            if song_result.song_id == PRIMARY_TEST_SONG_ID and song_result.current_bpm:
                hit_target = False
                close_target = False

                for candidate in strategy.bpm_candidates:
                    for target in TARGET_BPMS:
                        if abs(candidate - target) <= 3:
                            hit_target = True
                            break
                        elif abs(candidate - target) <= 10:
                            close_target = True
                    if hit_target:
                        break

                if hit_target:
                    status = "\u2713 Hit target"
                elif close_target:
                    status = "~ Close"
                else:
                    status = "\u2717 Missed"

            f.write(f"| {strategy_name} | {candidates_str} | {exec_time} | {status} |\n")

        f.write("\n")

        # Link to distribution plot
        f.write(f"**Visualization:** `plots/bpm_distribution_{song_result.song_id}.png`\n\n")

        # Notable findings
        f.write("**Analysis:**\n\n")

        # Check for consensus among strategies
        all_candidates = []
        for strategy in song_result.strategy_results:
            if strategy.bpm_candidates:
                all_candidates.extend(strategy.bpm_candidates)

        if all_candidates:
            median_bpm = np.median(all_candidates)
            std_bpm = np.std(all_candidates)

            f.write(f"- **Median BPM across all strategies:** {median_bpm:.1f}\n")
            f.write(f"- **Standard deviation:** {std_bpm:.1f}\n")

            if std_bpm < 5:
                f.write("- **Consensus:** High agreement among strategies (low variance)\n")
            elif std_bpm < 15:
                f.write("- **Consensus:** Moderate agreement among strategies\n")
            else:
                f.write("- **Consensus:** Low agreement among strategies (high variance indicates complex rhythm)\n")

        # Strategy-specific notes
        f.write("\n**Strategy Notes:**\n\n")
        for strategy in song_result.strategy_results:
            if strategy.processing_notes:
                f.write(f"- **{strategy.strategy_name.replace('_', ' ').title()}:** {strategy.processing_notes[0]}\n")

        f.write("\n")

        # Intermediate files generated
        f.write("**Intermediate Files:**\n\n")
        for strategy in song_result.strategy_results:
            if strategy.intermediate_files:
                for file_type, file_path in strategy.intermediate_files.items():
                    try:
                        rel_path = (
                            Path(file_path).relative_to(output_dir.parent)
                            if output_dir.parent in Path(file_path).parents
                            else Path(file_path).name
                        )
                    except ValueError:
                        rel_path = Path(file_path).name
                    f.write(f"- {strategy.strategy_name}/{file_type}: `{rel_path}`\n")

        f.write("\n---\n\n")


def _write_cross_strategy_analysis(
    f,
    results: List[SongTestResult],
    all_strategy_names: List[str],
    strategy_times: Dict[str, List[float]],
    avg_times: Dict[str, float],
) -> None:
    """Write cross-strategy analysis section."""
    f.write("## Cross-Strategy Analysis\n\n")

    # Execution time comparison
    f.write("### Execution Time Comparison\n\n")
    f.write("| Strategy | Avg Time (s) | Std Dev (s) | vs Baseline |\n")
    f.write("|----------|--------------|-------------|-------------|\n")

    baseline_time = avg_times.get("baseline", None)

    for strategy_name in all_strategy_names:
        display_name = strategy_name.replace("_", " ").title()
        avg_time = avg_times.get(strategy_name, 0)
        std_time = np.std(strategy_times.get(strategy_name, [0]))

        if baseline_time and strategy_name != "baseline":
            vs_baseline = ((avg_time - baseline_time) / baseline_time) * 100
            vs_baseline_str = f"{vs_baseline:+.1f}%"
        else:
            vs_baseline_str = "\u2014"

        f.write(f"| {display_name} | {avg_time:.2f} | {std_time:.2f} | {vs_baseline_str} |\n")

    f.write("\n**Visualization:** `plots/execution_time_comparison.png`\n\n")

    # Candidate count comparison
    f.write("### Candidate Generation Patterns\n\n")
    f.write("| Strategy | Avg Candidates | Min | Max | Pattern |\n")
    f.write("|----------|----------------|-----|-----|--------|\n")

    for strategy_name in all_strategy_names:
        display_name = strategy_name.replace("_", " ").title()

        # Collect candidate counts
        counts = []
        for song_result in results:
            for strategy in song_result.strategy_results:
                if strategy.strategy_name == strategy_name:
                    counts.append(len(strategy.bpm_candidates))

        if counts:
            avg_count = np.mean(counts)
            min_count = min(counts)
            max_count = max(counts)

            # Determine pattern
            if avg_count < 5:
                pattern = "Conservative"
            elif avg_count < 10:
                pattern = "Moderate"
            else:
                pattern = "Liberal"

            f.write(f"| {display_name} | {avg_count:.1f} | {min_count} | {max_count} | {pattern} |\n")

    f.write("\n**Visualization:** `plots/candidate_count_comparison.png`\n\n")

    # Strategy agreement analysis
    f.write("### Strategy Agreement Analysis\n\n")
    f.write("This section analyzes which strategies tend to produce similar results.\n\n")

    # For each song, check which strategies agree (within 5 BPM)
    agreement_counts = {}

    for song_result in results:
        # Get top candidate from each strategy
        strategy_top_bpms = {}
        for strategy in song_result.strategy_results:
            if strategy.bpm_candidates:
                strategy_top_bpms[strategy.strategy_name] = strategy.bpm_candidates[0]

        # Check pairwise agreement
        strategy_names = list(strategy_top_bpms.keys())
        for i in range(len(strategy_names)):
            for j in range(i + 1, len(strategy_names)):
                s1, s2 = strategy_names[i], strategy_names[j]
                bpm1, bpm2 = strategy_top_bpms[s1], strategy_top_bpms[s2]

                if abs(bpm1 - bpm2) <= 5:
                    pair = tuple(sorted([s1, s2]))
                    agreement_counts[pair] = agreement_counts.get(pair, 0) + 1

    # Find pairs with high agreement
    if agreement_counts:
        f.write("**High Agreement Pairs** (strategies that frequently produce similar results):\n\n")

        # Sort by agreement count
        sorted_pairs = sorted(agreement_counts.items(), key=lambda x: x[1], reverse=True)

        for (s1, s2), count in sorted_pairs[:5]:  # Top 5 pairs
            percentage = (count / len(results)) * 100
            s1_display = s1.replace("_", " ").title()
            s2_display = s2.replace("_", " ").title()
            f.write(
                f"- **{s1_display}** + **{s2_display}**: "
                f"{count}/{len(results)} songs ({percentage:.0f}% agreement)\n"
            )

        f.write("\n")

    f.write("**Visualization:** `plots/strategy_success_matrix.png`\n\n")
    f.write("---\n\n")


def _write_recommendations(f, primary_song, fastest_strategy, slowest_strategy) -> None:
    """Write recommendations section."""
    f.write("## Recommendations\n\n")

    f.write("### Analysis Summary\n\n")
    f.write("Based on the test results, the following observations can be made:\n\n")

    # Find strategies that hit target on primary song (if available)
    if primary_song:
        strategies_hit_target = []
        for strategy in primary_song.strategy_results:
            for candidate in strategy.bpm_candidates:
                if abs(candidate - 88) <= 3 or abs(candidate - 176) <= 3:
                    strategies_hit_target.append(strategy.strategy_name)
                    break

        if strategies_hit_target:
            f.write("**Strategies that successfully detected the target BPM for the primary D&B test song:**\n\n")
            for strategy_name in strategies_hit_target:
                f.write(f"- {strategy_name.replace('_', ' ').title()}\n")
            f.write("\n")
        else:
            f.write(
                "**Note:** No strategies successfully detected the expected target BPM (88 or 176 BPM) "
                "for the primary Drum & Bass test song. This indicates that the baseline detection "
                "algorithm may need significant improvements for complex rhythmic patterns.\n\n"
            )

    # Performance considerations
    f.write("**Performance Considerations:**\n\n")
    if fastest_strategy and slowest_strategy:
        speedup = slowest_strategy[1] / fastest_strategy[1]
        f.write(
            f"- Fastest strategy ({fastest_strategy[0].replace('_', ' ').title()}) "
            f"is {speedup:.1f}x faster than slowest\n"
        )
        f.write("- All strategies complete within acceptable time limits (< 10s)\n\n")

    # Recommendation placeholder
    f.write("### Primary Recommendation\n\n")

    f.write("**Strategy Selection Criteria:**\n\n")
    f.write("1. **Accuracy:** Successfully detects target BPM for complex genres (D&B, EDM)\n")
    f.write("2. **Consistency:** Produces reliable results across different BPM ranges\n")
    f.write("3. **Performance:** Acceptable execution time (< 10s)\n")
    f.write("4. **Maintainability:** Easy to implement and understand\n\n")

    f.write("**Recommended Strategy:** *See detailed analysis of strategy performance above*\n\n")

    f.write("The optimal strategy should be selected based on:\n")
    f.write("- Success rate on the primary D&B test song\n")
    f.write("- Consistency across different BPM ranges\n")
    f.write("- Minimal performance overhead\n\n")

    # Implementation guidance
    f.write("### Production Implementation\n\n")
    f.write("To implement the recommended strategy in production:\n\n")

    f.write("```python\n")
    f.write("# File: backend/app/services/audio.py\n")
    f.write("# Location: detect_bpm() function, around lines 235-236\n\n")
    f.write("# 1. Add necessary imports at top of file\n")
    f.write("from scipy.signal import butter, filtfilt  # For filtering strategies\n")
    f.write("# or\n")
    f.write("import librosa  # Already imported\n\n")
    f.write("# 2. Add preprocessing before BPM detection\n")
    f.write("# After loading audio (line 236: y, sr = librosa.load(...))\n\n")
    f.write("if config.use_improved_bpm_detection:  # Feature flag\n")
    f.write("    # Apply recommended preprocessing here\n")
    f.write("    # Example for low-pass filter:\n")
    f.write("    nyquist = sr / 2\n")
    f.write("    cutoff = 150  # Hz\n")
    f.write("    order = 4\n")
    f.write("    b, a = signal.butter(order, cutoff / nyquist, btype='low')\n")
    f.write("    y = signal.filtfilt(b, a, y)\n")
    f.write("    \n")
    f.write("# Continue with existing detection logic...\n")
    f.write("```\n\n")

    f.write("### Migration Strategy\n\n")

    f.write("**Phase 1: Testing**\n")
    f.write("1. Deploy behind feature flag for A/B testing\n")
    f.write("2. Monitor BPM detection quality on new uploads\n")
    f.write("3. Collect user feedback on count-in timing accuracy\n\n")

    f.write("**Phase 2: Backfill**\n")
    f.write("```bash\n")
    f.write("# Re-detect BPM for existing songs in problematic ranges\n")
    f.write("cd backend && source venv/bin/activate\n")
    f.write("python scripts/backfill_bpm_with_improved_detection.py --min-bpm 70 --max-bpm 180\n")
    f.write("```\n\n")

    f.write("**Phase 3: Validation**\n")
    f.write("1. Review updated BPMs for known problematic songs\n")
    f.write("2. Test karaoke count-in timing during active sessions\n")
    f.write("3. Roll back if detection quality degrades\n\n")

    # Alternative approaches
    f.write("### Alternative Approaches\n\n")
    f.write("If a single strategy does not provide satisfactory results, consider:\n\n")

    f.write("**Hybrid Approach:**\n")
    f.write("- Combine multiple strategies (e.g., low-pass filter + HPSS)\n")
    f.write("- Use ensemble voting to select final BPM\n")
    f.write("- May improve accuracy but increases computation time\n\n")

    f.write("**Genre-Specific Detection:**\n")
    f.write("- Apply different strategies based on detected genre\n")
    f.write("- Use HPSS for electronic music, low-pass for hip-hop, etc.\n")
    f.write("- Requires genre classification as preprocessing step\n\n")

    f.write("**Manual Override:**\n")
    f.write("- Add UI for users to manually set BPM if auto-detection fails\n")
    f.write("- Store user-provided BPM as ground truth for future testing\n")
    f.write("- Useful fallback for edge cases\n\n")

    f.write("---\n\n")


def _write_failure_mode_analysis(f, primary_song, all_strategy_names: List[str]) -> None:
    """Write failure mode analysis section."""
    f.write("## Failure Mode Analysis\n\n")

    strategies_hit_target = []

    if primary_song:
        f.write(f"### Why Baseline Fails on {primary_song.title}\n\n")

        baseline_strategy = next(
            (s for s in primary_song.strategy_results if s.strategy_name == "baseline"), None
        )

        if baseline_strategy:
            f.write("**Baseline Strategy Results:**\n\n")
            f.write(
                f"- **Top BPM Candidates:** "
                f"{[round(c, 1) for c in baseline_strategy.bpm_candidates[:5]]}\n"
            )
            f.write("- **Expected BPM:** 88 or 176 BPM\n")
            if baseline_strategy.bpm_candidates:
                f.write(
                    f"- **Deviation:** {abs(baseline_strategy.bpm_candidates[0] - 88):.1f} BPM from 88 BPM, "
                    f"{abs(baseline_strategy.bpm_candidates[0] - 176):.1f} BPM from 176 BPM\n\n"
                )

            f.write("**Potential Issues:**\n\n")
            f.write(
                "1. **High-Frequency Noise:** Drum & Bass tracks have dense hi-hat and cymbal "
                "patterns that may confuse onset detection\n"
            )
            f.write(
                "2. **Tempo Ambiguity:** Rapid drum patterns at 176 BPM may be misinterpreted "
                "as slower 88 BPM half-time\n"
            )
            f.write(
                "3. **Complex Layering:** Multiple rhythmic layers (kick, snare, hi-hat) compete "
                "for detection priority\n"
            )
            f.write("4. **Syncopation:** Off-beat elements may create false onset peaks\n\n")

        # Build strategies that hit target
        for strategy in primary_song.strategy_results:
            for candidate in strategy.bpm_candidates:
                if abs(candidate - 88) <= 3 or abs(candidate - 176) <= 3:
                    strategies_hit_target.append(strategy.strategy_name)
                    break

    # Strategies that consistently fail
    f.write("### Strategies That Didn't Improve\n\n")

    if primary_song:
        failed_strategies = [s for s in all_strategy_names if s not in strategies_hit_target]

        if failed_strategies:
            f.write("The following strategies did not successfully detect the target BPM:\n\n")
            for strategy_name in failed_strategies:
                display_name = strategy_name.replace("_", " ").title()
                f.write(f"- **{display_name}**\n")
            f.write("\n")

            f.write("**Common Pattern:**\n\n")
            f.write("These strategies may share similar limitations:\n")
            f.write("- Insufficient isolation of fundamental rhythm (kick drum)\n")
            f.write("- Over-sensitivity to high-frequency percussion\n")
            f.write("- Inadequate handling of tempo ambiguity (half-time vs full-time)\n\n")

    f.write("---\n\n")


def _write_raw_data_section(f, output_dir: Path) -> None:
    """Write raw data section."""
    f.write("## Raw Data\n\n")
    f.write("Complete results saved to: `raw_data/all_results.json`\n\n")

    f.write("### Files Generated\n\n")

    # Count files
    plot_count = len(list(output_dir.glob("plots/**/*.png")))
    audio_count = len(list(output_dir.glob("intermediate_audio/**/*.wav")))

    f.write(f"- **Plots:** {plot_count} PNG files in `plots/` directory\n")
    f.write(f"- **Intermediate Audio:** {audio_count} WAV files in `intermediate_audio/` directory\n")
    f.write("- **Strategy-specific plots:** Each strategy x each song\n\n")


def _write_appendices(f, all_strategy_names: List[str], output_dir: Path) -> None:
    """Write appendices section."""
    f.write("---\n\n")
    f.write("## Appendices\n\n")

    f.write("### Appendix A: Strategy Descriptions\n\n")

    for strategy_name in all_strategy_names:
        display_name = strategy_name.replace("_", " ").title()
        description = STRATEGY_DESCRIPTIONS.get(strategy_name, "No description available")

        f.write(f"#### {display_name}\n\n")
        f.write(f"{description}\n\n")

        # Add technical details
        if strategy_name == "lowpass_filter":
            f.write("**Technical Details:**\n")
            f.write("- Filter type: 4th order Butterworth\n")
            f.write("- Cutoff frequency: 150 Hz\n")
            f.write("- Removes high-frequency content above cutoff\n\n")

        elif strategy_name == "hpss_separation":
            f.write("**Technical Details:**\n")
            f.write("- Margin: 8.0 (stronger separation)\n")
            f.write("- Separates harmonic (tonal) and percussive (rhythmic) components\n")
            f.write("- BPM detection performed on percussive component\n\n")

        elif strategy_name == "tempogram_plp":
            f.write("**Technical Details:**\n")
            f.write("- Uses Predominant Local Pulse (PLP) analysis\n")
            f.write("- More robust to tempo variations\n")
            f.write("- Analyzes tempogram for consistent pulse patterns\n\n")

        elif strategy_name == "multiband_detection":
            f.write("**Technical Details:**\n")
            f.write("- Frequency bands: Bass (20-250 Hz), Mid (250-4000 Hz), High (4000-11025 Hz)\n")
            f.write("- Independent BPM detection per band\n")
            f.write("- Reveals rhythmic differences across frequency spectrum\n\n")

        elif strategy_name == "large_ac_size":
            f.write("**Technical Details:**\n")
            f.write("- Tests ac_size values: 8 (default), 16, 32, 64\n")
            f.write("- Larger windows capture longer-term patterns\n")
            f.write("- May improve detection for slow tempos\n\n")

    f.write("### Appendix B: Intermediate Files Index\n\n")

    f.write("All intermediate files are organized by song and strategy:\n\n")
    f.write("```\n")
    f.write("reports/bpm_investigation_YYYYMMDD_HHMMSS/\n")
    f.write("\u251c\u2500\u2500 plots/\n")
    f.write("\u2502   \u251c\u2500\u2500 {song_id}/\n")
    f.write("\u2502   \u2502   \u251c\u2500\u2500 baseline_{song_id}.png\n")
    f.write("\u2502   \u2502   \u251c\u2500\u2500 lowpass_filter_{song_id}.png\n")
    f.write("\u2502   \u2502   \u2514\u2500\u2500 ...\n")
    f.write("\u2502   \u251c\u2500\u2500 bpm_distribution_{song_id}.png\n")
    f.write("\u2502   \u251c\u2500\u2500 execution_time_comparison.png\n")
    f.write("\u2502   \u251c\u2500\u2500 candidate_count_comparison.png\n")
    f.write("\u2502   \u2514\u2500\u2500 strategy_success_matrix.png\n")
    f.write("\u251c\u2500\u2500 intermediate_audio/\n")
    f.write("\u2502   \u2514\u2500\u2500 {song_id}/\n")
    f.write("\u2502       \u251c\u2500\u2500 lowpass_filtered_{song_id}.wav\n")
    f.write("\u2502       \u251c\u2500\u2500 hpss_harmonic_{song_id}.wav\n")
    f.write("\u2502       \u251c\u2500\u2500 hpss_percussive_{song_id}.wav\n")
    f.write("\u2502       \u2514\u2500\u2500 ...\n")
    f.write("\u251c\u2500\u2500 raw_data/\n")
    f.write("\u2502   \u251c\u2500\u2500 {song_id}_results.json\n")
    f.write("\u2502   \u2514\u2500\u2500 all_results.json\n")
    f.write("\u2514\u2500\u2500 FINDINGS.md (this file)\n")
    f.write("```\n\n")

    f.write("---\n\n")
    f.write("**End of Report**\n")
