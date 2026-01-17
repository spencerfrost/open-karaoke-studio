"""
BPM detection strategies package.

Each strategy implements a different approach to detecting BPM from audio.
"""

from .baseline import baseline_current_implementation
from .delta_onset import experiment_delta_onset
from .hpss_separation import experiment_hpss_separation
from .large_ac_size import experiment_large_ac_size
from .log_amplitude import experiment_log_amplitude
from .lowpass_filter import experiment_lowpass_filter
from .median_aggregation import experiment_median_aggregation
from .multiband_detection import experiment_multiband_detection
from .tempogram_plp import experiment_tempogram_plp

# All available strategies in order of execution
ALL_STRATEGIES = [
    ("Baseline (Current)", baseline_current_implementation),
    ("Strategy 1: Low-Pass Filter", experiment_lowpass_filter),
    ("Strategy 2: HPSS Separation", experiment_hpss_separation),
    ("Strategy 3: Tempogram PLP", experiment_tempogram_plp),
    ("Strategy 4: Log-Amplitude", experiment_log_amplitude),
    ("Strategy 5: Delta-Onset", experiment_delta_onset),
    ("Strategy 6: Multi-Band Detection", experiment_multiband_detection),
    ("Strategy 7: Large AC Size", experiment_large_ac_size),
    ("Strategy 8: Median Aggregation", experiment_median_aggregation),
]

__all__ = [
    "ALL_STRATEGIES",
    "baseline_current_implementation",
    "experiment_lowpass_filter",
    "experiment_hpss_separation",
    "experiment_tempogram_plp",
    "experiment_log_amplitude",
    "experiment_delta_onset",
    "experiment_multiband_detection",
    "experiment_large_ac_size",
    "experiment_median_aggregation",
]
