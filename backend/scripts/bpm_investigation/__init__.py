"""
BPM Detection Accuracy Investigation Package.

This package tests 8 experimental signal processing strategies against the current baseline
implementation to identify the most accurate BPM detection approach for complex tracks,
particularly Drum & Bass music.

Usage:
    cd backend && source venv/bin/activate
    python scripts/bpm_accuracy_investigation.py
"""

from .config import (
    PRIMARY_TEST_SONG_ID,
    STRATEGY_DESCRIPTIONS,
    TARGET_BPMS,
    setup_logging,
    setup_output_directories,
)
from .helpers import create_progress_bar, filter_harmonic_duplicates, select_best_tempo
from .models import SongTestResult, StrategyResult
from .report import generate_report
from .runner import run_all_strategies, run_investigation, run_single_file_test
from .song_selection import find_audio_file, select_test_songs
from .visualization import generate_visualizations

__all__ = [
    # Config
    "setup_logging",
    "setup_output_directories",
    "PRIMARY_TEST_SONG_ID",
    "TARGET_BPMS",
    "STRATEGY_DESCRIPTIONS",
    # Models
    "StrategyResult",
    "SongTestResult",
    # Helpers
    "filter_harmonic_duplicates",
    "select_best_tempo",
    "create_progress_bar",
    # Song selection
    "find_audio_file",
    "select_test_songs",
    # Visualization
    "generate_visualizations",
    # Report
    "generate_report",
    # Runner
    "run_all_strategies",
    "run_investigation",
    "run_single_file_test",
]
