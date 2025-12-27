"""
Experimental vocal separation engines for benchmarking.

This package provides multiple separation engine implementations:
- demucs_standard: Baseline Demucs-only separation
- audio_sep_roformer: Single-pass Roformer with ViperX model
- hybrid_sequential: Sequential Demucs → audio-separator refinement
"""

from .demucs_standard import separate_with_demucs
from .audio_sep_roformer import separate_with_roformer
from .hybrid_sequential import separate_with_hybrid

__all__ = [
    "separate_with_demucs",
    "separate_with_roformer",
    "separate_with_hybrid",
]
