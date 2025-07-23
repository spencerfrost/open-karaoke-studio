#!/usr/bin/env python3
"""
CLI script for Whisper to LRC conversion.

This script provides a command-line interface for the whisper-to-lrc
conversion functionality.
"""

import sys
from pathlib import Path

# Add the parent directory to Python path so we can import the package
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.ai_lyrics.whisper_to_lrc.cli import main

if __name__ == "__main__":
    sys.exit(main())
