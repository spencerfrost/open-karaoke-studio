"""
Command line interface for Whisper to LRC conversion.

This module provides the command line interface and argument parsing
for the whisper-to-lrc conversion tool.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .converter import WhisperToLRCConverter
from .models import ConverterConfig
from .quality import get_quality_summary


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Convert Faster Whisper JSON output to LRC format lyrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s vocals_whisper_results.json
  %(prog)s vocals_whisper_results.json --output vocals.lrc
  %(prog)s vocals_whisper_results.json --max-gap 3.0 --target-words 6
  %(prog)s vocals_whisper_results.json --confidence-threshold 0.5 --quiet
        """,
    )

    # Required arguments
    parser.add_argument(
        "input_file", help="Path to the Faster Whisper JSON output file"
    )

    # Optional arguments
    parser.add_argument(
        "-o",
        "--output",
        help="Output LRC file path (if not provided, prints to stdout)",
    )

    # Converter configuration
    parser.add_argument(
        "--max-gap",
        type=float,
        default=2.0,
        help="Maximum gap in seconds to allow within a line (default: 2.0)",
    )

    parser.add_argument(
        "--min-words", type=int, default=2, help="Minimum words per line (default: 2)"
    )

    parser.add_argument(
        "--max-words", type=int, default=8, help="Maximum words per line (default: 8)"
    )

    parser.add_argument(
        "--target-words", type=int, default=5, help="Target words per line (default: 5)"
    )

    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.3,
        help="Minimum confidence score for words (default: 0.3)",
    )

    # Output options
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress status messages (only show LRC output)",
    )

    parser.add_argument(
        "--show-quality", action="store_true", help="Show detailed quality assessment"
    )

    parser.add_argument(
        "--show-metadata", action="store_true", help="Show conversion metadata"
    )

    return parser


def validate_arguments(args: argparse.Namespace) -> bool:
    """
    Validate command line arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        True if arguments are valid
    """
    # Check input file exists
    if not Path(args.input_file).exists():
        print(f"❌ Error: Input file not found: {args.input_file}", file=sys.stderr)
        return False

    # Validate numeric ranges
    if args.max_gap < 0:
        print("❌ Error: max-gap must be non-negative", file=sys.stderr)
        return False

    if args.min_words < 1:
        print("❌ Error: min-words must be at least 1", file=sys.stderr)
        return False

    if args.max_words < args.min_words:
        print("❌ Error: max-words must be >= min-words", file=sys.stderr)
        return False

    if args.target_words < args.min_words or args.target_words > args.max_words:
        print(
            "❌ Error: target-words must be between min-words and max-words",
            file=sys.stderr,
        )
        return False

    if not (0 <= args.confidence_threshold <= 1):
        print("❌ Error: confidence-threshold must be between 0 and 1", file=sys.stderr)
        return False

    return True


def run_conversion(args: argparse.Namespace) -> int:
    """
    Run the conversion process with the given arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Load JSON data
        import json

        with open(args.input_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        # Create converter with configuration
        config = ConverterConfig(
            max_gap=args.max_gap,
            min_words_per_line=args.min_words,
            max_words_per_line=args.max_words,
            target_words_per_line=args.target_words,
            confidence_threshold=args.confidence_threshold,
        )
        converter = WhisperToLRCConverter(config)

        # Convert to LRC
        lrc_content, lyrics_data = converter.convert_json_to_lrc(json_data)

        # Save or print LRC content
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(lrc_content)
            if not args.quiet:
                print(f"✅ LRC file saved to: {args.output}")
        else:
            if not args.quiet:
                print("📝 LRC Content:")
                print("-" * 40)
            print(lrc_content)

        # Show status information
        if not args.quiet:
            print()
            print("🎵 Conversion completed successfully!")
            print(f"📊 Generated {len(lyrics_data.lines)} lyric lines")
            print(get_quality_summary(lyrics_data.quality))

        # Show detailed quality assessment
        if args.show_quality:
            print("\n🔍 Quality Assessment:")
            quality = lyrics_data.quality
            print(f"  Average confidence: {quality.avg_confidence:.3f}")
            print(
                f"  Low confidence words: {quality.low_confidence_words}/{quality.total_words}"
            )
            print(f"  Coverage percentage: {quality.coverage_percentage:.1%}")
            print(f"  Timing consistency: {quality.timing_consistency:.3f}")
            print(
                f"  Review recommended: {'Yes' if quality.recommended_review else 'No'}"
            )

        # Show metadata
        if args.show_metadata:
            print("\n📋 Metadata:")
            metadata = lyrics_data.metadata
            if metadata.get("detected_language"):
                print(
                    f"  Language: {metadata['detected_language']} ({metadata.get('language_probability', 0):.2f})"
                )
            if metadata.get("duration"):
                print(f"  Duration: {metadata['duration']:.1f} seconds")
            print(
                f"  Words: {metadata['original_word_count']} total, {metadata['filtered_word_count']} used"
            )
            print(f"  Confidence threshold: {metadata['confidence_threshold']}")

        return 0

    except Exception as e:
        print(f"❌ Error during conversion: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point for the CLI."""
    parser = create_argument_parser()
    args = parser.parse_args()

    if not validate_arguments(args):
        return 1

    return run_conversion(args)


if __name__ == "__main__":
    sys.exit(main())
