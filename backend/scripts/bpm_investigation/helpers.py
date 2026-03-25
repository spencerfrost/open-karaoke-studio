"""
Helper functions for BPM detection and processing.
"""

from typing import List

from tqdm import tqdm


def filter_harmonic_duplicates(tempos: List[float]) -> List[float]:
    """
    Filter out harmonic multiples/divisors (2x, 1/2, 3/2, 2/3, 4/3, 3/4).
    Groups tempos that are harmonically related and keeps representative values.

    Args:
        tempos: List of tempo estimates

    Returns:
        List of filtered tempos with harmonics removed
    """
    if not tempos:
        return []

    # Common harmonic ratios to check
    harmonic_ratios = [0.5, 2.0, 0.667, 1.5, 0.75, 1.333]
    tolerance = 0.05  # 5% tolerance for matching

    clusters: List[List[float]] = []
    for tempo in tempos:
        # Find if this tempo belongs to existing cluster
        matched = False
        for cluster in clusters:
            for existing_tempo in cluster:
                # Check if harmonically related
                ratio = tempo / existing_tempo
                if (
                    any(abs(ratio - hr) < tolerance for hr in harmonic_ratios)
                    or abs(ratio - 1.0) < tolerance
                ):
                    cluster.append(tempo)
                    matched = True
                    break
            if matched:
                break

        if not matched:
            clusters.append([tempo])

    # Return the tempo from each cluster (prefer values in 80-180 range)
    filtered = []
    for cluster in clusters:
        # Prefer tempos in typical range
        in_range = [t for t in cluster if 80 <= t <= 180]
        if in_range:
            filtered.append(sum(in_range) / len(in_range))
        else:
            filtered.append(sum(cluster) / len(cluster))

    return filtered


def select_best_tempo(tempos: List[float]) -> float:
    """
    Select the most likely tempo from filtered estimates using median.

    Args:
        tempos: List of tempo estimates

    Returns:
        The selected BPM value
    """
    if not tempos:
        return 120.0  # Fallback

    # Use median for robustness against outliers
    tempos_sorted = sorted(tempos)
    n = len(tempos_sorted)
    if n % 2 == 0:
        return (tempos_sorted[n // 2 - 1] + tempos_sorted[n // 2]) / 2
    else:
        return tempos_sorted[n // 2]


def create_progress_bar(total: int, desc: str, position: int = 0) -> tqdm:
    """
    Create a configured tqdm progress bar for nested progress tracking.

    Args:
        total: Total number of items to track
        desc: Description text for the progress bar
        position: Vertical position for nested bars (0 = top)

    Returns:
        Configured tqdm progress bar instance
    """
    return tqdm(
        total=total,
        desc=desc,
        position=position,
        leave=True,
        ncols=100,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
    )
