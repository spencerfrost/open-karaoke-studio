"""Lyrics alignment hears the lead and backing vocals together."""

import numpy as np
import pytest
import soundfile as sf

from app.services.audio import load_sung_vocals

SR = 22050  # load_vocals' rate, so nothing is resampled


def write(path, samples):
    sf.write(str(path), np.asarray(samples, dtype=np.float32), SR)
    return path


def test_lead_alone_without_a_backing_track(tmp_path):
    lead = write(tmp_path / "vocals.wav", [0.25] * 100)
    y, sr = load_sung_vocals(lead)
    assert sr == SR
    assert y == pytest.approx(np.full(100, 0.25), abs=1e-3)


def test_backing_is_summed_in_and_padded_to_the_longer(tmp_path, monkeypatch):
    lead = write(tmp_path / "vocals.wav", [0.25] * 100)
    write(tmp_path / "backing.wav", [0.5] * 150)
    monkeypatch.setattr("app.services.audio.BACKING_VOCALS_FILENAME", "backing.wav")
    y, _ = load_sung_vocals(lead)
    assert len(y) == 150
    assert y[:100] == pytest.approx(np.full(100, 0.75), abs=1e-3)
    assert y[100:] == pytest.approx(np.full(50, 0.5), abs=1e-3)


def test_a_clipping_sum_is_scaled_down(tmp_path, monkeypatch):
    lead = write(tmp_path / "vocals.wav", [0.8] * 100)
    write(tmp_path / "backing.wav", [0.8] * 100)
    monkeypatch.setattr("app.services.audio.BACKING_VOCALS_FILENAME", "backing.wav")
    y, _ = load_sung_vocals(lead)
    assert float(np.max(np.abs(y))) == pytest.approx(1.0, abs=1e-3)
