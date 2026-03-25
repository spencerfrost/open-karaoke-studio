#!/usr/bin/env python3
"""
BPM Detection Accuracy Investigation Script

This script tests 8 experimental signal processing strategies against the current baseline
implementation to identify the most accurate BPM detection approach for complex tracks,
particularly Drum & Bass music.

Usage:
    cd backend && source venv/bin/activate
    python scripts/bpm_accuracy_investigation.py

    # Test a single audio file
    python scripts/bpm_accuracy_investigation.py --test-file /path/to/audio.mp3
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to sys.path to allow imports from app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bpm_investigation import run_investigation, run_single_file_test, setup_logging


def main() -> int:
    """Main entry point for BPM investigation."""
    # Setup logging
    setup_logging()

    parser = argparse.ArgumentParser(
        description="BPM Detection Accuracy Investigation - Test experimental strategies"
    )
    parser.add_argument(
        "--test-file",
        type=Path,
        help="Test a single audio file instead of running full investigation",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory (only used with --test-file)",
    )

    args = parser.parse_args()

    # Test mode: single file
    if args.test_file:
        return run_single_file_test(args.test_file, args.output)

    # Full investigation mode
    return run_investigation()


if __name__ == "__main__":
    sys.exit(main())
