#!/usr/bin/env python3
"""
Audio Separation Engine Benchmarking Script

This script benchmarks three experimental vocal separation engines:
1. Demucs Standard (Baseline)
2. Roformer Karaoke-First (Single-pass)
3. Hybrid Sequential (Gold Standard)

Metrics collected:
- Processing time (total duration)
- Peak VRAM usage
- Output file sizes
- Success/failure status

Usage:
    python scripts/benchmark_separation.py <path_to_audio_file>

Example:
    python scripts/benchmark_separation.py /path/to/test.mp3
"""

import argparse
import json
import logging
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
from app.services.separation_engines import (
    separate_with_demucs,
    separate_with_hybrid,
    separate_with_roformer,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class VRAMMonitor:
    """Monitor VRAM usage during processing"""

    def __init__(self, interval=0.5):
        self.interval = interval
        self.peak_vram_mb = 0
        self.current_vram_mb = 0
        self.monitoring = False
        self.thread = None
        self.has_gpu = torch.cuda.is_available()

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            if self.has_gpu:
                try:
                    torch.cuda.synchronize()
                    allocated = torch.cuda.memory_allocated() / (1024**2)  # MB
                    reserved = torch.cuda.memory_reserved() / (1024**2)  # MB
                    self.current_vram_mb = max(allocated, reserved)
                    self.peak_vram_mb = max(self.peak_vram_mb, self.current_vram_mb)
                except Exception as e:
                    logger.warning(f"VRAM monitoring error: {e}")
            time.sleep(self.interval)

    def start(self):
        """Start VRAM monitoring"""
        if not self.has_gpu:
            logger.warning("No GPU available - VRAM monitoring disabled")
            return

        self.monitoring = True
        self.peak_vram_mb = 0
        self.current_vram_mb = 0

        # Reset CUDA memory stats
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.empty_cache()

        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("VRAM monitoring started")

    def stop(self):
        """Stop VRAM monitoring and return peak usage"""
        if not self.has_gpu:
            return 0

        self.monitoring = False
        if self.thread:
            self.thread.join(timeout=2.0)

        # Get final reading from PyTorch
        torch.cuda.synchronize()
        pytorch_peak = torch.cuda.max_memory_allocated() / (1024**2)
        final_peak = max(self.peak_vram_mb, pytorch_peak)

        logger.info(f"VRAM monitoring stopped. Peak usage: {final_peak:.1f} MB")
        return final_peak


def get_file_size_mb(file_path: Path) -> float:
    """Get file size in MB"""
    if file_path.exists():
        return file_path.stat().st_size / (1024**2)
    return 0.0


def benchmark_engine(
    engine_name: str,
    engine_func,
    input_path: Path,
    output_dir: Path,
    stop_event: threading.Event,
) -> dict:
    """
    Benchmark a single separation engine

    Args:
        engine_name: Name of the engine (for logging)
        engine_func: The separation function to call
        input_path: Path to the input audio file
        output_dir: Directory for output files
        stop_event: Threading event for cancellation

    Returns:
        Dictionary with benchmark results
    """
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Benchmarking: {engine_name}")
    logger.info(f"{'=' * 60}\n")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Status callback for progress updates
    def status_callback(msg: str):
        logger.info(f"[{engine_name}] {msg}")

    # Setup VRAM monitoring
    vram_monitor = VRAMMonitor(interval=0.5)
    vram_monitor.start()

    # Run the engine
    start_time = time.time()

    try:
        success, detected_bpm = engine_func(
            input_path=input_path,
            song_dir=output_dir,
            status_callback=status_callback,
            stop_event=stop_event,
        )
        end_time = time.time()

        # Stop VRAM monitoring
        peak_vram = vram_monitor.stop()

        # Calculate metrics
        duration = end_time - start_time

        # Get output file sizes
        vocals_path = output_dir / "vocals.mp3"
        instrumental_path = output_dir / "instrumental.mp3"

        vocals_size_mb = get_file_size_mb(vocals_path)
        instrumental_size_mb = get_file_size_mb(instrumental_path)

        result = {
            "engine": engine_name,
            "success": success,
            "duration_seconds": round(duration, 2),
            "duration_formatted": f"{int(duration // 60)}m {int(duration % 60)}s",
            "peak_vram_mb": round(peak_vram, 1),
            "detected_bpm": detected_bpm,
            "vocals_size_mb": round(vocals_size_mb, 2),
            "instrumental_size_mb": round(instrumental_size_mb, 2),
            "total_output_size_mb": round(vocals_size_mb + instrumental_size_mb, 2),
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"\n{engine_name} Results:")
        logger.info(f"  Success: {success}")
        logger.info(f"  Duration: {result['duration_formatted']}")
        logger.info(f"  Peak VRAM: {peak_vram:.1f} MB")
        logger.info(f"  Output size: {result['total_output_size_mb']:.2f} MB")
        if detected_bpm:
            logger.info(f"  Detected BPM: {detected_bpm}")

        return result

    except Exception as e:
        end_time = time.time()
        peak_vram = vram_monitor.stop()
        duration = end_time - start_time

        logger.error(f"{engine_name} failed: {e}", exc_info=True)

        return {
            "engine": engine_name,
            "success": False,
            "error": str(e),
            "duration_seconds": round(duration, 2),
            "duration_formatted": f"{int(duration // 60)}m {int(duration % 60)}s",
            "peak_vram_mb": round(peak_vram, 1),
            "timestamp": datetime.now().isoformat(),
        }


def run_benchmark(input_path: Path, output_base_dir: Path):
    """
    Run all benchmark experiments

    Args:
        input_path: Path to the input audio file
        output_base_dir: Base directory for all output files
    """
    logger.info(f"\n{'#' * 60}")
    logger.info(f"Audio Separation Engine Benchmark")
    logger.info(f"{'#' * 60}")
    logger.info(f"Input file: {input_path}")
    logger.info(f"Output directory: {output_base_dir}")
    logger.info(f"GPU available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    logger.info(f"{'#' * 60}\n")

    # Validate input file
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)

    if not input_path.suffix.lower() in [".mp3", ".wav", ".m4a", ".flac"]:
        logger.warning(f"Input file has unusual extension: {input_path.suffix}")

    # Create base output directory
    output_base_dir.mkdir(parents=True, exist_ok=True)

    # Define experiments
    experiments = [
        {
            "name": "1_Demucs_Standard",
            "function": separate_with_demucs,
            "description": "Baseline: Standard Demucs 4-stem separation",
        },
        {
            "name": "2_Roformer_ViperX",
            "function": separate_with_roformer,
            "description": "Karaoke-First: Single-pass Roformer with ViperX model",
        },
        {
            "name": "3_Hybrid_Sequential",
            "function": separate_with_hybrid,
            "description": "Gold Standard: Demucs + audio-separator refinement",
        },
    ]

    # Run benchmarks
    results = []
    stop_event = threading.Event()

    for exp in experiments:
        engine_output_dir = output_base_dir / exp["name"]

        # Clean output directory if it exists
        if engine_output_dir.exists():
            import shutil

            shutil.rmtree(engine_output_dir)

        result = benchmark_engine(
            engine_name=exp["name"],
            engine_func=exp["function"],
            input_path=input_path,
            output_dir=engine_output_dir,
            stop_event=stop_event,
        )
        result["description"] = exp["description"]
        results.append(result)

        # Small delay between experiments to let GPU cool down
        time.sleep(2)

    # Generate summary report
    logger.info(f"\n{'#' * 60}")
    logger.info("BENCHMARK SUMMARY")
    logger.info(f"{'#' * 60}\n")

    # Print comparison table
    logger.info(f"{'Engine':<25} {'Duration':<12} {'VRAM (MB)':<12} {'Success':<10}")
    logger.info("-" * 60)

    for result in results:
        logger.info(
            f"{result['engine']:<25} "
            f"{result['duration_formatted']:<12} "
            f"{result.get('peak_vram_mb', 0):<12.1f} "
            f"{'✓' if result['success'] else '✗':<10}"
        )

    # Save detailed results to JSON
    results_file = output_base_dir / "benchmark_results.json"
    with open(results_file, "w") as f:
        json.dump(
            {
                "input_file": str(input_path),
                "timestamp": datetime.now().isoformat(),
                "gpu_available": torch.cuda.is_available(),
                "gpu_name": (
                    torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
                ),
                "results": results,
            },
            f,
            indent=2,
        )

    logger.info(f"\nDetailed results saved to: {results_file}")
    logger.info(f"\nBenchmark complete! Check output directories for audio files:")
    for exp in experiments:
        logger.info(f"  - {output_base_dir / exp['name']}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Benchmark audio separation engines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to the input audio file to process",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for results (default: ./benchmark_results_<timestamp>)",
    )

    args = parser.parse_args()

    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"./benchmark_results_{timestamp}")

    # Run benchmark
    run_benchmark(input_path=args.input_file, output_base_dir=output_dir)


if __name__ == "__main__":
    main()
