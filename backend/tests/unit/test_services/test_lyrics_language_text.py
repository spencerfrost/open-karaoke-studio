"""Tests for reading a song's language from its lyrics text."""

import pytest

from app.services.lyrics_language import detect_lyrics_language

FRENCH = """[00:10.00]Qui dit étude dit travail
[00:13.00]Qui dit taf te dit les thunes
[00:16.00]Qui dit argent dit dépenses
[00:19.00]Qui dit crédit dit créance
[00:22.00]Qui dit dette te dit huissier
[00:25.00]Oui, dit assis dans la merde
[00:28.00]Qui dit amour dit les gosses
[00:31.00]Dit toujours et dit divorce
[00:34.00]Car les problèmes ne viennent pas seuls"""

# Muse's Hysteria, which Whisper heard as Danish from the singing alone.
ENGLISH = """[Verse 1]
[00:43.00]It's bugging me, grating me
[00:46.00]And twisting me around
[00:50.00]Yeah, I'm endlessly caving in
[00:54.00]And turning inside out
[Chorus]
[01:00.00]'Cause I want it now, I want it now
[01:07.00]Give me your heart and your soul
[01:11.00]And I'm breaking out, I'm breaking out
[01:17.00]Last chance to lose control
[01:48.00]And dreaming I'm alive"""


def test_lrc_lyrics_read_as_their_language():
    assert detect_lyrics_language(FRENCH) == {"language": "fr", "probability": 1.0}


def test_english_reads_as_english():
    detected = detect_lyrics_language(ENGLISH)
    assert detected is not None
    assert detected["language"] == "en"
    assert detected["probability"] >= 0.9


def test_the_same_text_gives_the_same_answer_every_time():
    assert len({str(detect_lyrics_language(ENGLISH)) for _ in range(5)}) == 1


@pytest.mark.parametrize(
    "lyrics",
    [
        None,
        "",
        # Three lines are too few: langdetect reads this patois as Afrikaans.
        "Skankin', groovin', hallelujah\nSkankin', groovin', help me Jah\nWe a go skank it",
        "[Chorus]\n[Verse 1]\n" + "[00:10.00]Oh oh oh\n" * 20,
    ],
)
def test_too_little_text_reads_as_nothing(lyrics):
    assert detect_lyrics_language(lyrics) is None
