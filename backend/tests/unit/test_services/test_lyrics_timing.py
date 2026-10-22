import io
import json
import logging
from pathlib import Path

import pytest
from pythonjsonlogger.json import JsonFormatter

from app.config.base import BaseConfig
from app.config.logging import LoggingConfig
from app.services import lyrics_timing
from app.services.lyrics_timing import log_lyrics_event


@pytest.fixture
def log_config(tmp_path):
    (tmp_path / "backend").mkdir()
    config = BaseConfig()
    config.BASE_DIR = tmp_path
    return LoggingConfig(config).setup_logging(environment="production")


@pytest.fixture
def captured_events(log_config):
    """Capture lyrics events with the same JSON format as lyrics_timing.jsonl."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter(log_config["formatters"]["json"]["format"]))
    logger = lyrics_timing.logger
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        yield lambda: [json.loads(line) for line in stream.getvalue().splitlines()]
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


def test_lyrics_events_are_routed_to_the_lyrics_timing_file(log_config):
    route = log_config["loggers"][lyrics_timing.logger.name]
    handler = log_config["handlers"][route["handlers"][0]]

    assert route["handlers"] == ["file_lyrics_timing"]
    assert route["propagate"] is False
    assert handler["filename"].endswith("lyrics_timing.jsonl")


def test_lyrics_event_fields_reach_the_json_line(captured_events):
    log_lyrics_event(
        "song-1",
        "lyrics_alignment_finished",
        score=0.82,
        vocals_path=Path("/library/song-1/vocals.mp3"),
        sources=("db", "lrclib:1"),
    )

    [event] = captured_events()
    assert event["message"] == "lyrics_alignment_finished"
    assert event["song_id"] == "song-1"
    assert event["event"] == "lyrics_alignment_finished"
    assert event["score"] == 0.82
    assert event["vocals_path"] == "/library/song-1/vocals.mp3"
    assert event["sources"] == ["db", "lrclib:1"]


def test_lyrics_event_fields_named_like_log_record_attributes_do_not_raise(
    captured_events,
):
    log_lyrics_event(
        "song-1", "lyrics_remote_fetch_failed", name="lrclib", filename="x.lrc"
    )

    [event] = captured_events()
    assert event["field_name"] == "lrclib"
    assert event["field_filename"] == "x.lrc"
