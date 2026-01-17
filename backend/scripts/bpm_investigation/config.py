"""
Configuration and setup for BPM investigation.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

import matplotlib

# Configure matplotlib backend for non-interactive plotting
matplotlib.use("Agg")


def setup_logging() -> logging.Logger:
    """
    Configure logging for the investigation script.

    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    return logging.getLogger(__name__)


def setup_output_directories(base_dir: Path | None = None) -> Dict[str, Path]:
    """
    Create timestamped output directory structure for investigation results.

    Args:
        base_dir: Optional base directory. Defaults to backend/reports/

    Returns:
        Dictionary mapping directory names to Path objects:
        - 'root': Main timestamped directory
        - 'plots': Directory for visualizations
        - 'intermediate_audio': Directory for intermediate audio files
        - 'raw_data': Directory for raw JSON data
    """
    logger = logging.getLogger(__name__)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent.parent / "reports"

    root_dir = base_dir / f"bpm_investigation_{timestamp}"

    directories = {
        "root": root_dir,
        "plots": root_dir / "plots",
        "intermediate_audio": root_dir / "intermediate_audio",
        "raw_data": root_dir / "raw_data",
    }

    for dir_name, dir_path in directories.items():
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")

    return directories


# Strategy descriptions for documentation
STRATEGY_DESCRIPTIONS = {
    "baseline": (
        "Current production implementation (multi-pass tempo detection "
        "with onset-based candidates and harmonic filtering)"
    ),
    "lowpass_filter": (
        "Aggressive Butterworth low-pass filter at 150Hz to isolate "
        "kick/sub-bass frequencies"
    ),
    "hpss_separation": (
        "Harmonic-Percussive Source Separation (HPSS) with margin=8.0 "
        "for clean beat detection"
    ),
    "tempogram_plp": (
        "Tempogram analysis with Predominant Local Pulse (PLP) for "
        "tempo variation handling"
    ),
    "log_amplitude": (
        "Log-amplitude scaling (dB conversion) of onset envelope to "
        "balance loud/quiet events"
    ),
    "delta_onset": "First derivative of onset envelope to emphasize sudden drum hits",
    "multiband_detection": (
        "Frequency band separation (bass/mid/high) with independent "
        "BPM detection per band"
    ),
    "large_ac_size": (
        "Large autocorrelation window sizes (8, 16, 32, 64) to capture "
        "long-term patterns"
    ),
    "median_aggregation": (
        "Median aggregation across frequency bands instead of traditional "
        "sum (robust to outliers)"
    ),
}

# Primary test song ID (Drum & Bass track for testing)
PRIMARY_TEST_SONG_ID = "328a2091-db5e-4dfe-b516-6cbcadde8678"

# Expected BPM values for D&B genre
TARGET_BPMS = [88, 176]
