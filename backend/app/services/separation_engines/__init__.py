"""
Experimental vocal separation engines for benchmarking.

This package provides multiple separation engine implementations:
- demucs_standard: Baseline Demucs-only separation
- audio_sep_roformer: Single-pass Roformer with ViperX model
- hybrid_sequential: Sequential Demucs → audio-separator refinement
- clean_backing: Multi-pass with de-noised backing vocals
- three_track: Three independent tracks (lead vocals, backing vocals, instrumental)
"""

from .demucs_standard import separate_with_demucs
from .audio_sep_roformer import separate_with_roformer
from .hybrid_sequential import separate_with_hybrid
from .clean_backing import separate_with_clean_backing
from .three_track import separate_with_three_track

__all__ = [
    "separate_with_demucs",
    "separate_with_roformer",
    "separate_with_hybrid",
    "separate_with_clean_backing",
    "separate_with_three_track",
]
