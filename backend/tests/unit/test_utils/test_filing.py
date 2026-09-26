"""Tests for A–Z filing of artist and show names."""

import pytest
from app.utils.filing import filing_letter, filing_name


@pytest.mark.parametrize(
    "name, letter",
    [
        ("The Beatles", "B"),
        ("the killers", "K"),
        ("A Perfect Circle", "P"),
        ("An Horse", "H"),
        ("ABBA", "A"),
        ("Theory of a Deadman", "T"),
        ("Anastacia", "A"),
        ("Édith Piaf", "E"),
        ("Øystein", "#"),
        ("3 Doors Down", "#"),
        ("*NSYNC", "#"),
        ("The", "T"),
        ("", "#"),
    ],
)
def test_filing_letter(name, letter):
    assert filing_letter(name) == letter


def test_filing_name_sorts_articles_and_accents_in_place():
    names = ["The Beatles", "Beck", "Björk", "Blondie", "A Ha", "Adele"]
    assert sorted(names, key=filing_name) == [
        "Adele",
        "The Beatles",
        "Beck",
        "Björk",
        "Blondie",
        "A Ha",
    ]
