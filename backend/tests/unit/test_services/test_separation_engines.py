from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pytest
import torch

from app.services.separation_engines import roformer_loader, three_track


def _config(**overrides):
    values = {
        "SEPARATION_USE_AUTOCAST": True,
        "SEPARATION_TORCH_COMPILE": True,
        "THREE_TRACK_DENOISE": True,
        "DEFAULT_MODEL": "htdemucs_ft",
        "DEFAULT_MP3_BITRATE": "320",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.fixture
def fake_separator_class(monkeypatch):
    separator_class = MagicMock(name="Separator")
    monkeypatch.setattr(roformer_loader, "Separator", separator_class)
    return separator_class


@pytest.mark.parametrize("use_autocast", [True, False])
@pytest.mark.parametrize("use_compile", [True, False])
def test_load_separator_passes_settings_from_config(
    monkeypatch, fake_separator_class, use_autocast, use_compile
):
    monkeypatch.setattr(
        roformer_loader,
        "get_config",
        lambda: _config(
            SEPARATION_USE_AUTOCAST=use_autocast, SEPARATION_TORCH_COMPILE=use_compile
        ),
    )

    separator = roformer_loader.load_separator("model.ckpt", "/tmp/out")

    kwargs = fake_separator_class.call_args.kwargs
    assert kwargs["output_dir"] == "/tmp/out"
    assert kwargs["output_format"] == "wav"
    assert kwargs["use_autocast"] is use_autocast
    assert kwargs["use_torch_compile"] is use_compile
    separator.load_model.assert_called_once_with(model_filename="model.ckpt")


def test_load_separator_keeps_one_pass_per_chunk(monkeypatch, fake_separator_class):
    """overlap=1 on audio-separator 0.47: one window per chunk, as before 0.47."""
    monkeypatch.setattr(roformer_loader, "get_config", _config)

    roformer_loader.load_separator("model.ckpt", "/tmp/out")

    assert fake_separator_class.call_args.kwargs["mdxc_params"]["overlap"] == 1


def _exit_during_load(error: Exception):
    """Mimic audio-separator: sys.exit(1) inside the except for a load error."""

    def load_model(model_filename):
        try:
            raise error
        except RuntimeError:
            raise SystemExit(1)

    return load_model


def test_load_separator_turns_oom_exit_into_oom_error(
    monkeypatch, fake_separator_class
):
    monkeypatch.setattr(roformer_loader, "get_config", _config)
    fake_separator_class.return_value.load_model.side_effect = _exit_during_load(
        torch.cuda.OutOfMemoryError("CUDA out of memory. Tried to allocate 20 MiB")
    )

    with pytest.raises(torch.cuda.OutOfMemoryError):
        roformer_loader.load_separator("model.ckpt", "/tmp/out")


def test_load_separator_turns_other_exit_into_runtime_error(
    monkeypatch, fake_separator_class
):
    monkeypatch.setattr(roformer_loader, "get_config", _config)
    fake_separator_class.return_value.load_model.side_effect = _exit_during_load(
        RuntimeError("Error(s) in loading state_dict")
    )

    with pytest.raises(RuntimeError, match="state_dict") as excinfo:
        roformer_loader.load_separator("model.ckpt", "/tmp/out")
    assert not isinstance(excinfo.value, torch.cuda.OutOfMemoryError)


class _FakeRoformer:
    """Writes empty stem files named the way audio-separator names them."""

    def __init__(self, model, output_dir):
        self.model = model
        self.output_dir = output_dir

    def separate(self, path):
        if self.model == three_track.DENOISE_MODEL:
            names = ["backing_(dry)_denoise.wav", "backing_(noise)_denoise.wav"]
        else:
            names = ["vocals_(Vocals)_karaoke.wav", "vocals_(Instrumental)_karaoke.wav"]
        for name in names:
            open(f"{self.output_dir}/{name}", "wb").close()
        return names


@pytest.fixture
def stub_pipeline(monkeypatch):
    """Stub Demucs, the Roformer loader and MP3 export; record which models load."""
    loaded = []

    def fake_load(model, output_dir, output_format="wav"):
        loaded.append(model)
        return _FakeRoformer(model, output_dir)

    demucs = MagicMock(samplerate=44100)
    stems = {name: torch.zeros(2, 10) for name in ("drums", "bass", "other", "vocals")}
    demucs.separate_audio_file.return_value = (torch.zeros(2, 10), stems)

    exported = {}

    def from_wav(path):
        segment = MagicMock()
        segment.export.side_effect = lambda out, **kw: exported.__setitem__(out, path)
        return segment

    monkeypatch.setattr(three_track, "load_separator", fake_load)
    monkeypatch.setattr(three_track, "DemucsSeparator", lambda **kw: demucs)
    monkeypatch.setattr(three_track, "select_device_and_log", lambda cb: "cpu")
    monkeypatch.setattr(three_track.AudioSegment, "from_wav", from_wav)
    return SimpleNamespace(loaded=loaded, exported=exported, demucs=demucs)


@pytest.mark.parametrize("denoise", [True, False])
def test_three_track_denoise_toggle(monkeypatch, tmp_path, stub_pipeline, denoise):
    monkeypatch.setattr(
        three_track, "get_config", lambda: _config(THREE_TRACK_DENOISE=denoise)
    )

    ok = three_track.separate_with_three_track(
        tmp_path / "original.mp3", tmp_path, status_callback=lambda m: None
    )

    assert ok
    assert (three_track.DENOISE_MODEL in stub_pipeline.loaded) is denoise
    backing_source = next(
        src for out, src in stub_pipeline.exported.items() if "backing" in out
    )
    assert ("(dry)" in backing_source) is denoise
    assert ("(Instrumental)" in backing_source) is not denoise


SOURCES = ["drums", "bass", "other", "vocals"]
ONE_HOT_BAG_WEIGHTS = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]


def _bag(weights):
    models = [SimpleNamespace(name=f"model{i}") for i in range(len(weights))]
    return SimpleNamespace(sources=SOURCES, weights=weights, models=models)


def test_vocals_specialist_replaces_one_hot_bag():
    bag = _bag(ONE_HOT_BAG_WEIGHTS)
    separator = SimpleNamespace(_model=bag)

    assert three_track._use_vocals_specialist(separator)
    assert separator._model is bag.models[3]


def test_vocals_specialist_keeps_averaging_bag():
    bag = _bag([[1.0] * 4, [1.0] * 4])
    separator = SimpleNamespace(_model=bag)

    assert not three_track._use_vocals_specialist(separator)
    assert separator._model is bag


def test_vocals_specialist_keeps_single_model():
    model = SimpleNamespace(sources=SOURCES)  # htdemucs: no bag weights
    separator = SimpleNamespace(_model=model)

    assert not three_track._use_vocals_specialist(separator)
    assert separator._model is model


def test_three_track_instrumental_is_mix_minus_vocals(
    monkeypatch, tmp_path, stub_pipeline
):
    monkeypatch.setattr(three_track, "get_config", _config)
    mix = torch.full((2, 10), 0.5)
    vocals = torch.full((2, 10), 0.2)
    stems = {name: torch.full((2, 10), 0.9) for name in SOURCES[:3]}
    stub_pipeline.demucs._model = _bag(ONE_HOT_BAG_WEIGHTS)
    stub_pipeline.demucs.separate_audio_file.return_value = (
        mix,
        {**stems, "vocals": vocals},
    )
    written = {}
    monkeypatch.setattr(
        three_track.sf,
        "write",
        lambda path, data, sr, subtype: written.__setitem__(Path(path).name, data),
    )

    assert three_track.separate_with_three_track(
        tmp_path / "original.mp3", tmp_path, status_callback=lambda m: None
    )
    assert np.allclose(written["demucs_instrumental.wav"], 0.3)


def test_three_track_exports_each_stem_from_its_wav(
    monkeypatch, tmp_path, stub_pipeline
):
    monkeypatch.setattr(three_track, "get_config", _config)

    assert three_track.separate_with_three_track(
        tmp_path / "original.mp3", tmp_path, status_callback=lambda m: None
    )
    sources = {
        Path(out).name: Path(src).name for out, src in stub_pipeline.exported.items()
    }
    assert sources == {
        "vocals.mp3": "vocals_(Vocals)_karaoke.wav",
        "backing_vocals.mp3": "backing_(dry)_denoise.wav",
        "instrumental.mp3": "demucs_instrumental.wav",
    }
    assert not (tmp_path / ".temp_three_track").exists()


def test_three_track_reports_vocals_once_written(monkeypatch, tmp_path, stub_pipeline):
    monkeypatch.setattr(three_track, "get_config", _config)
    reported = []

    def on_vocals_ready(path):
        reported.append((path, str(path) in stub_pipeline.exported))

    assert three_track.separate_with_three_track(
        tmp_path / "original.mp3",
        tmp_path,
        status_callback=lambda m: None,
        on_vocals_ready=on_vocals_ready,
    )
    assert reported == [(tmp_path / "vocals.mp3", True)]


def test_three_track_fails_when_an_export_fails(monkeypatch, tmp_path, stub_pipeline):
    monkeypatch.setattr(three_track, "get_config", _config)
    real_from_wav = three_track.AudioSegment.from_wav

    def from_wav(path):
        if "instrumental" in str(path):
            raise RuntimeError("ffmpeg failed")
        return real_from_wav(path)

    monkeypatch.setattr(three_track.AudioSegment, "from_wav", from_wav)

    assert not three_track.separate_with_three_track(
        tmp_path / "original.mp3", tmp_path, status_callback=lambda m: None
    )
    assert not (tmp_path / ".temp_three_track").exists()


def test_three_track_demucs_overlap(monkeypatch, tmp_path, stub_pipeline):
    monkeypatch.setattr(three_track, "get_config", _config)
    demucs_kwargs = {}

    def make_demucs(**kw):
        demucs_kwargs.update(kw)
        return stub_pipeline.demucs

    monkeypatch.setattr(three_track, "DemucsSeparator", make_demucs)

    assert three_track.separate_with_three_track(
        tmp_path / "original.mp3", tmp_path, status_callback=lambda m: None
    )
    assert demucs_kwargs["overlap"] == three_track.DEMUCS_OVERLAP == 0.1


@pytest.mark.parametrize(
    "device, enabled, autocast",
    [("cuda", True, True), ("cuda", False, False), ("cpu", True, False)],
)
def test_demucs_autocast_only_on_cuda_when_enabled(device, enabled, autocast):
    ctx = three_track._demucs_autocast(device, enabled)
    assert isinstance(ctx, torch.autocast) is autocast
