"""
Visualization generation for BPM investigation results.
"""

import logging
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import numpy as np

from .models import SongTestResult

logger = logging.getLogger(__name__)


def generate_visualizations(results: List[SongTestResult], output_dir: Path) -> None:
    """
    Generate comparative visualizations of strategy performance.

    Creates the following visualizations:
    - BPM distribution comparison across strategies (per song)
    - Execution time comparison (bar chart)
    - Candidate count comparison (bar chart)
    - Strategy success matrix (optional, if target BPM known)

    Args:
        results: List of test results for all songs
        output_dir: Directory to save plot files
    """
    logger.info("Generating comparative visualizations...")

    if not results:
        logger.warning("No results to visualize")
        return

    # Create plots directory if needed
    plots_dir = output_dir
    plots_dir.mkdir(parents=True, exist_ok=True)

    # Generate each visualization type
    _generate_bpm_distribution_plots(results, plots_dir)
    _generate_execution_time_plot(results, plots_dir)
    _generate_candidate_count_plot(results, plots_dir)
    _generate_success_matrix(results, plots_dir)

    logger.info("Visualization generation complete!")


def _generate_bpm_distribution_plots(results: List[SongTestResult], plots_dir: Path) -> None:
    """Generate BPM distribution plots for each song."""
    logger.info("  Creating BPM distribution plots for each song...")

    for song_result in results:
        song_id = song_result.song_id
        song_title = song_result.title
        song_artist = song_result.artist
        current_bpm = song_result.current_bpm

        # Prepare data: strategy names and their BPM candidates
        strategy_names = []
        strategy_bpms = []

        for strategy in song_result.strategy_results:
            if strategy.bpm_candidates:
                strategy_names.append(strategy.strategy_name.replace("_", " ").title())
                strategy_bpms.append(strategy.bpm_candidates)

        if not strategy_names:
            logger.warning(f"    No BPM candidates for song {song_id}, skipping distribution plot")
            continue

        # Create violin plot
        fig, ax = plt.subplots(figsize=(14, 8), dpi=300)

        # Create positions for each strategy
        positions = list(range(1, len(strategy_names) + 1))

        # Create violin plot
        parts = ax.violinplot(strategy_bpms, positions=positions, showmeans=True, showmedians=True)

        # Customize violin plot colors
        for pc in parts["bodies"]:
            pc.set_facecolor("skyblue")
            pc.set_alpha(0.6)

        # Add scatter points for individual candidates
        for i, (pos, bpms) in enumerate(zip(positions, strategy_bpms)):
            # Jitter x positions slightly for visibility
            x_jitter = np.random.normal(pos, 0.04, size=len(bpms))
            ax.scatter(x_jitter, bpms, alpha=0.4, s=30, color="darkblue")

        # Add horizontal line for current/target BPM
        if current_bpm:
            ax.axhline(
                y=current_bpm,
                color="red",
                linestyle="--",
                linewidth=2,
                label=f"Current BPM: {current_bpm:.1f}",
                alpha=0.7,
            )

        # Styling
        ax.set_xticks(positions)
        ax.set_xticklabels(strategy_names, rotation=45, ha="right")
        ax.set_ylabel("BPM Candidates", fontsize=12)
        ax.set_title(
            f"BPM Distribution by Strategy\n{song_title} by {song_artist}",
            fontsize=14,
            fontweight="bold",
        )
        ax.grid(True, alpha=0.3, axis="y")
        ax.legend(loc="upper right")

        # Add y-axis limits with some padding
        all_bpms = [bpm for bpms in strategy_bpms for bpm in bpms]
        if all_bpms:
            y_min = max(30, min(all_bpms) - 20)
            y_max = min(300, max(all_bpms) + 20)
            ax.set_ylim(y_min, y_max)

        plt.tight_layout()
        plot_path = plots_dir / f"bpm_distribution_{song_id}.png"
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        logger.info(f"    Saved: {plot_path.name}")


def _generate_execution_time_plot(results: List[SongTestResult], plots_dir: Path) -> None:
    """Generate execution time comparison plot."""
    logger.info("  Creating execution time comparison plot...")

    # Collect execution times by strategy
    strategy_times = {}

    for song_result in results:
        for strategy in song_result.strategy_results:
            strategy_name = strategy.strategy_name.replace("_", " ").title()
            if strategy_name not in strategy_times:
                strategy_times[strategy_name] = []
            strategy_times[strategy_name].append(strategy.execution_time)

    if not strategy_times:
        return

    # Calculate mean and std for each strategy
    strategy_names = list(strategy_times.keys())
    means = [np.mean(strategy_times[name]) for name in strategy_names]
    stds = [np.std(strategy_times[name]) for name in strategy_names]

    # Create bar chart
    fig, ax = plt.subplots(figsize=(12, 7), dpi=300)

    x_pos = np.arange(len(strategy_names))
    bars = ax.bar(
        x_pos,
        means,
        yerr=stds,
        capsize=5,
        alpha=0.7,
        color="steelblue",
        edgecolor="darkblue",
        linewidth=1.5,
    )

    # Add value labels on bars
    for i, (bar, mean, std) in enumerate(zip(bars, means, stds)):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + std + 0.1,
            f"{mean:.2f}s",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    ax.set_xticks(x_pos)
    ax.set_xticklabels(strategy_names, rotation=45, ha="right")
    ax.set_ylabel("Execution Time (seconds)", fontsize=12)
    ax.set_title("Average Execution Time by Strategy (with Std Dev)", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plot_path = plots_dir / "execution_time_comparison.png"
    plt.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"    Saved: {plot_path.name}")


def _generate_candidate_count_plot(results: List[SongTestResult], plots_dir: Path) -> None:
    """Generate candidate count comparison plot."""
    logger.info("  Creating candidate count comparison plot...")

    # Collect candidate counts by strategy
    strategy_counts = {}

    for song_result in results:
        for strategy in song_result.strategy_results:
            strategy_name = strategy.strategy_name.replace("_", " ").title()
            if strategy_name not in strategy_counts:
                strategy_counts[strategy_name] = []
            strategy_counts[strategy_name].append(len(strategy.bpm_candidates))

    if not strategy_counts:
        return

    # Calculate mean and std for each strategy
    strategy_names = list(strategy_counts.keys())
    means = [np.mean(strategy_counts[name]) for name in strategy_names]
    stds = [np.std(strategy_counts[name]) for name in strategy_names]

    # Create bar chart
    fig, ax = plt.subplots(figsize=(12, 7), dpi=300)

    x_pos = np.arange(len(strategy_names))
    bars = ax.bar(
        x_pos,
        means,
        yerr=stds,
        capsize=5,
        alpha=0.7,
        color="coral",
        edgecolor="darkred",
        linewidth=1.5,
    )

    # Add value labels on bars
    for i, (bar, mean, std) in enumerate(zip(bars, means, stds)):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + std + 0.1,
            f"{mean:.1f}",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    ax.set_xticks(x_pos)
    ax.set_xticklabels(strategy_names, rotation=45, ha="right")
    ax.set_ylabel("Number of BPM Candidates", fontsize=12)
    ax.set_title("Average BPM Candidates Generated by Strategy", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plot_path = plots_dir / "candidate_count_comparison.png"
    plt.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"    Saved: {plot_path.name}")


def _generate_success_matrix(results: List[SongTestResult], plots_dir: Path) -> None:
    """Generate strategy success matrix."""
    logger.info("  Creating strategy success matrix...")

    # Check if any songs have target BPMs
    songs_with_target = [s for s in results if s.current_bpm is not None]

    if not songs_with_target:
        logger.info("    Skipping success matrix (no target BPMs available)")
        return

    # Build matrix: rows = songs, cols = strategies
    all_strategy_names = []
    for song_result in songs_with_target:
        for strategy in song_result.strategy_results:
            name = strategy.strategy_name.replace("_", " ").title()
            if name not in all_strategy_names:
                all_strategy_names.append(name)

    n_songs = len(songs_with_target)
    n_strategies = len(all_strategy_names)

    # Create success matrix
    # 2 = hit target (within +/-3 BPM), 1 = close (within +/-10 BPM), 0 = missed
    success_matrix = np.zeros((n_songs, n_strategies))

    for i, song_result in enumerate(songs_with_target):
        target_bpm = song_result.current_bpm

        for strategy in song_result.strategy_results:
            strategy_name = strategy.strategy_name.replace("_", " ").title()
            j = all_strategy_names.index(strategy_name)

            # Check if any candidate hits the target
            best_match = float("inf")
            if strategy.bpm_candidates:
                for candidate in strategy.bpm_candidates:
                    diff = abs(candidate - target_bpm)
                    if diff < best_match:
                        best_match = diff

                if best_match <= 3:
                    success_matrix[i, j] = 2  # Hit
                elif best_match <= 10:
                    success_matrix[i, j] = 1  # Close
                else:
                    success_matrix[i, j] = 0  # Miss

    # Create heatmap
    fig, ax = plt.subplots(figsize=(14, max(6, n_songs * 0.6)), dpi=300)

    # Custom colormap: red (miss) -> yellow (close) -> green (hit)
    cmap = plt.cm.colors.ListedColormap(["#d32f2f", "#fbc02d", "#388e3c"])
    bounds = [-0.5, 0.5, 1.5, 2.5]
    norm = plt.cm.colors.BoundaryNorm(bounds, cmap.N)

    im = ax.imshow(success_matrix, cmap=cmap, norm=norm, aspect="auto")

    # Set ticks and labels
    ax.set_xticks(np.arange(n_strategies))
    ax.set_yticks(np.arange(n_songs))
    ax.set_xticklabels(all_strategy_names, rotation=45, ha="right")
    ax.set_yticklabels(
        [f"{s.title[:30]}..." if len(s.title) > 30 else s.title for s in songs_with_target]
    )

    # Add text annotations
    for i in range(n_songs):
        for j in range(n_strategies):
            value = success_matrix[i, j]
            text_color = "white" if value in [0, 2] else "black"
            if value == 2:
                text = "\u2713"  # checkmark
            elif value == 1:
                text = "~"
            else:
                text = "\u2717"  # X mark
            ax.text(j, i, text, ha="center", va="center", color=text_color, fontsize=12, fontweight="bold")

    ax.set_title(
        "Strategy Success Matrix (Target BPM Match)\n"
        "\u2713 = Hit (\u00b13 BPM)  ~ = Close (\u00b110 BPM)  \u2717 = Miss",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xlabel("Strategy", fontsize=12)
    ax.set_ylabel("Song", fontsize=12)

    # Create colorbar
    cbar = plt.colorbar(im, ax=ax, ticks=[0, 1, 2])
    cbar.ax.set_yticklabels(["Miss", "Close", "Hit"])

    plt.tight_layout()
    plot_path = plots_dir / "strategy_success_matrix.png"
    plt.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close()

    logger.info(f"    Saved: {plot_path.name}")
