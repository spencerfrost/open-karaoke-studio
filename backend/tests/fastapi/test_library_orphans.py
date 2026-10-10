"""Tests for deleting library folders that no song points to."""

import shutil
import tempfile
from pathlib import Path

import pytest

from app.config import get_config


@pytest.fixture
def library():
    library_dir = get_config().LIBRARY_DIR
    created = []

    def make(name, files=()):
        folder = library_dir / name
        folder.mkdir()
        for file_name in files:
            (folder / file_name).touch()
        created.append(folder)
        return folder

    yield make
    for folder in created:
        shutil.rmtree(folder, ignore_errors=True)


def test_tests_use_a_throwaway_library():
    assert get_config().LIBRARY_DIR.is_relative_to(Path(tempfile.gettempdir()))


def test_deletes_an_orphan_folder(client, library):
    folder = library("orphan-song", files=["original.mp3"])

    resp = client.delete("/api/songs/orphan/orphan-song")

    assert resp.status_code == 200
    assert not folder.exists()


@pytest.mark.parametrize("name", ["covers", "artists"])
def test_refuses_to_delete_an_artwork_folder(client, library, name):
    folder = library(name, files=["1234.jpg"])

    resp = client.delete(f"/api/songs/orphan/{name}")

    assert resp.status_code == 400
    assert folder.exists()


def test_bulk_delete_skips_artwork_folders(client, library):
    covers = library("covers", files=["1234.jpg"])
    orphan = library("orphan-song")

    resp = client.request(
        "DELETE",
        "/api/songs/orphan-bulk",
        json={"dir_names": ["covers", "orphan-song"]},
    )

    assert resp.json() == {"deleted": 1, "skipped": 1}
    assert covers.exists()
    assert not orphan.exists()
