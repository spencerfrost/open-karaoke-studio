"""
Data structures for BPM investigation results.
"""

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


@dataclass
class StrategyResult:
    """
    Container for results from a single BPM detection strategy.

    Attributes:
        strategy_name: Human-readable name of the strategy
        bpm_candidates: List of detected BPM values (sorted by confidence)
        execution_time: Time in seconds to execute the strategy
        processing_notes: List of notable observations during processing
        intermediate_files: Mapping of description to file path for generated artifacts
    """

    strategy_name: str
    bpm_candidates: List[float]
    execution_time: float
    processing_notes: List[str] = field(default_factory=list)
    intermediate_files: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class SongTestResult:
    """
    Container for all strategy results for a single song.

    Attributes:
        song_id: Database ID of the tested song
        title: Song title
        artist: Artist name
        current_bpm: Currently stored BPM value (baseline)
        audio_file_path: Path to audio file used for testing
        strategy_results: List of results from each tested strategy
    """

    song_id: str
    title: str
    artist: str
    current_bpm: Optional[float]
    audio_file_path: str
    strategy_results: List[StrategyResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "song_id": self.song_id,
            "title": self.title,
            "artist": self.artist,
            "current_bpm": self.current_bpm,
            "audio_file_path": self.audio_file_path,
            "strategy_results": [sr.to_dict() for sr in self.strategy_results],
        }
