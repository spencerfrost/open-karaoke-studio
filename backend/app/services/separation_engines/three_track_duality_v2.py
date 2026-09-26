"""Three-track engine variant using InstVoc Duality V2 for vocal split."""

from pathlib import Path
from typing import Callable, Dict, Optional
import threading

from .three_track import separate_with_three_track

DUALITY_V2_MODEL = "melband_roformer_instvox_duality_v2.ckpt"
ENGINE_LABEL = "Three-Track (Demucs + Roformer InstVoc Duality V2 + De-Noise)"


def separate_with_three_track_duality_v2(
    input_path: Path,
    song_dir: Path,
    status_callback: Callable[[str], None],
    stop_event: Optional[threading.Event] = None,
    on_vocals_ready: Optional[Callable[[Path], None]] = None,
    timing_sink: Optional[Dict[str, float]] = None,
) -> bool:
    return separate_with_three_track(
        input_path=input_path,
        song_dir=song_dir,
        status_callback=status_callback,
        stop_event=stop_event,
        on_vocals_ready=on_vocals_ready,
        timing_sink=timing_sink,
        karaoke_model=DUALITY_V2_MODEL,
        engine_label=ENGINE_LABEL,
    )
