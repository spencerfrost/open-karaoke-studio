from types import SimpleNamespace
from unittest.mock import Mock

from app.services import gpu_idle_cleanup


def test_end_gpu_activity_schedules_idle_cleanup(monkeypatch):
    scheduled = {}

    class FakeTimer:
        def __init__(self, interval, function, args=None, kwargs=None):
            scheduled["interval"] = interval
            scheduled["function"] = function
            scheduled["args"] = args or ()
            scheduled["kwargs"] = kwargs or {}
            scheduled["started"] = False
            self.daemon = False

        def start(self):
            scheduled["started"] = True

        def cancel(self):
            scheduled["cancelled"] = True

    monkeypatch.setenv("GPU_IDLE_CLEANUP_SECONDS", "123")
    monkeypatch.setattr(gpu_idle_cleanup.torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(gpu_idle_cleanup.threading, "Timer", FakeTimer)
    monkeypatch.setattr(gpu_idle_cleanup.time, "monotonic", lambda: 1000.0)

    gpu_idle_cleanup._active_gpu_users = 0
    gpu_idle_cleanup._last_gpu_activity_monotonic = 0.0
    gpu_idle_cleanup._cleanup_generation = 0
    gpu_idle_cleanup._cleanup_timer = None

    gpu_idle_cleanup.begin_gpu_activity("test")
    gpu_idle_cleanup.end_gpu_activity("test")

    assert scheduled["interval"] == 123
    assert scheduled["function"] == gpu_idle_cleanup._run_idle_cleanup_if_still_idle
    assert scheduled["args"] == (1, 123)
    assert scheduled["started"] is True


def test_idle_cleanup_releases_cached_cuda_memory(monkeypatch):
    empty_cache = Mock()
    ipc_collect = Mock()
    collect = Mock()

    monkeypatch.setattr(gpu_idle_cleanup.torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(gpu_idle_cleanup.torch.cuda, "memory_reserved", Mock(side_effect=[512 * 1024 * 1024, 128 * 1024 * 1024]))
    monkeypatch.setattr(gpu_idle_cleanup.torch.cuda, "memory_allocated", Mock(side_effect=[256 * 1024 * 1024, 64 * 1024 * 1024]))
    monkeypatch.setattr(gpu_idle_cleanup.torch.cuda, "empty_cache", empty_cache)
    monkeypatch.setattr(gpu_idle_cleanup.torch.cuda, "ipc_collect", ipc_collect)
    monkeypatch.setattr(gpu_idle_cleanup.gc, "collect", collect)
    monkeypatch.setattr(gpu_idle_cleanup.time, "monotonic", lambda: 2000.0)

    gpu_idle_cleanup._active_gpu_users = 0
    gpu_idle_cleanup._last_gpu_activity_monotonic = 1000.0
    gpu_idle_cleanup._cleanup_generation = 7
    gpu_idle_cleanup._cleanup_timer = SimpleNamespace(cancel=lambda: None)

    gpu_idle_cleanup._run_idle_cleanup_if_still_idle(expected_generation=7, timeout_seconds=30)

    collect.assert_called_once()
    empty_cache.assert_called_once()
    ipc_collect.assert_called_once()