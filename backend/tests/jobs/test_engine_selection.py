import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import threading
from app.jobs.jobs import select_and_run_separation_engine


@patch("app.jobs.jobs.separate_with_roformer")
def test_select_roformer_engine(mock_roformer):
    mock_roformer.return_value = (True, 120.0)

    success, bpm = select_and_run_separation_engine(
        engine_type="roformer",
        input_path=Path("/fake/path.mp3"),
        song_dir=Path("/fake/dir"),
        status_callback=Mock(),
        stop_event=threading.Event(),
    )

    assert success is True
    assert bpm == 120.0
    mock_roformer.assert_called_once()


@patch("app.jobs.jobs.separate_with_hybrid")
def test_select_hybrid_engine(mock_hybrid):
    mock_hybrid.return_value = (True, None)

    success, bpm = select_and_run_separation_engine(
        engine_type="hybrid",
        input_path=Path("/fake/path.mp3"),
        song_dir=Path("/fake/dir"),
        status_callback=Mock(),
        stop_event=threading.Event(),
    )

    assert success is True
    assert bpm is None
    mock_hybrid.assert_called_once()


@patch("app.jobs.jobs.separate_with_demucs")
def test_default_to_demucs_for_unknown_engine(mock_demucs):
    mock_demucs.return_value = (True, 140.5)

    success, bpm = select_and_run_separation_engine(
        engine_type="unknown_engine",
        input_path=Path("/fake/path.mp3"),
        song_dir=Path("/fake/dir"),
        status_callback=Mock(),
        stop_event=threading.Event(),
    )

    assert success is True
    mock_demucs.assert_called_once()


@patch("app.jobs.jobs.separate_with_clean_backing")
def test_select_clean_backing_engine(mock_clean):
    mock_clean.return_value = (False, None)

    success, bpm = select_and_run_separation_engine(
        engine_type="clean_backing",
        input_path=Path("/fake/path.mp3"),
        song_dir=Path("/fake/dir"),
        status_callback=Mock(),
        stop_event=threading.Event(),
    )

    assert success is False
    mock_clean.assert_called_once()


@patch("app.jobs.jobs.separate_with_demucs")
def test_default_to_demucs_for_demucs_engine_type(mock_demucs):
    mock_demucs.return_value = (True, 130.0)

    success, bpm = select_and_run_separation_engine(
        engine_type="demucs",
        input_path=Path("/fake/path.mp3"),
        song_dir=Path("/fake/dir"),
        status_callback=Mock(),
        stop_event=threading.Event(),
    )

    assert success is True
    assert bpm == 130.0
    mock_demucs.assert_called_once()


@patch("app.jobs.jobs.separate_with_roformer")
def test_passes_all_arguments_correctly(mock_roformer):
    mock_roformer.return_value = (True, 125.0)
    mock_callback = Mock()
    mock_stop_event = threading.Event()
    input_path = Path("/input/audio.mp3")
    song_dir = Path("/output/song123")

    select_and_run_separation_engine(
        engine_type="roformer",
        input_path=input_path,
        song_dir=song_dir,
        status_callback=mock_callback,
        stop_event=mock_stop_event,
    )

    # Verify all arguments were passed correctly
    mock_roformer.assert_called_once_with(
        input_path=input_path,
        song_dir=song_dir,
        status_callback=mock_callback,
        stop_event=mock_stop_event,
    )
