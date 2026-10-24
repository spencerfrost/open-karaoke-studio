"""Tests for the job owner tag (session ownership without the join code)."""

from app.db.models.job import Job, JobStatus
from app.utils.owner_tag import session_owner_tag


def test_owner_tag_is_stable_per_session():
    assert session_owner_tag("ABCD") == session_owner_tag("ABCD")


def test_owner_tag_differs_between_sessions():
    assert session_owner_tag("ABCD") != session_owner_tag("WXYZ")


def test_owner_tag_does_not_contain_the_code():
    tag = session_owner_tag("ABCD")
    assert tag is not None
    assert "ABCD" not in tag.upper()
    assert len(tag) == 16


def test_owner_tag_is_none_without_session():
    assert session_owner_tag(None) is None
    assert session_owner_tag("") is None


def test_owner_tag_depends_on_server_secret(monkeypatch):
    from app.config.base import BaseConfig

    before = session_owner_tag("ABCD")
    monkeypatch.setattr(BaseConfig, "SECRET_KEY", "another-secret")
    assert session_owner_tag("ABCD") != before


def test_job_to_dict_sends_owner_tag_not_session_or_user():
    job = Job(
        id="job-1",
        filename="x.mp3",
        status=JobStatus.PENDING,
        song_id="song-1",
        session_id="ABCD",
        user_id=7,
    )
    data = job.to_dict()

    assert "session_id" not in data
    assert "user_id" not in data
    assert data["owner_tag"] == session_owner_tag("ABCD")
    assert "ABCD" not in str(list(data.values()))


def test_job_to_dict_owner_tag_none_without_session():
    job = Job(id="job-2", filename="x.mp3", status=JobStatus.PENDING)
    assert job.to_dict()["owner_tag"] is None
