import copy

from app.services.word_timing_repair import repair_words, sound_of


def word(text, start, end, line=0, score=0.9):
    return {
        "word": text,
        "start": start,
        "end": end,
        "score": score,
        "line_index": line,
    }


def spans(words):
    return [(w["start"], w["end"]) for w in words]


class TestSoundOf:
    def test_lead_and_backing_together(self):
        singing_map = {"lead": [[0, 2], [5, 6]], "backing": [[1, 3]]}
        assert sound_of(singing_map) == [(0, 3), (5, 6)]

    def test_missing_stems(self):
        assert sound_of({"lead": None, "backing": None}) == []


class TestCut:
    def test_held_last_word_ends_where_the_singing_stops(self):
        # The Package: "mine" timed 2:47–3:06, sung until 2:48.5.
        singing_map = {"lead": [[160, 168.5], [190, 200]], "backing": []}
        words = [word("all", 165, 166), word("mine", 167, 186)]
        repaired, changes = repair_words(words, singing_map)
        assert spans(repaired) == [(165, 166), (167, 168.5)]
        assert [(c.index, c.kind) for c in changes] == [(1, "cut")]
        assert changes[0].before == (167, 186)

    def test_held_mid_line_word(self):
        singing_map = {"lead": [[10, 12], [20, 25]], "backing": []}
        words = [word("I", 10, 10.5), word("can", 10.6, 19.8), word("feel", 20, 21)]
        repaired, changes = repair_words(words, singing_map)
        assert spans(repaired)[1] == (10.6, 12)
        assert [c.kind for c in changes] == ["cut"]

    def test_backing_singing_keeps_the_word(self):
        singing_map = {"lead": [[0, 2]], "backing": [[1.5, 6]]}
        repaired, changes = repair_words([word("ooh", 0, 6)], singing_map)
        assert spans(repaired) == [(0, 6)]
        assert changes == []

    def test_short_silence_inside_a_word_is_a_breath(self):
        singing_map = {"lead": [[0, 2], [3.5, 6]], "backing": []}
        repaired, changes = repair_words([word("long", 0, 6)], singing_map)
        assert spans(repaired) == [(0, 6)]
        assert changes == []

    def test_sound_after_the_silence_is_cut_too(self):
        # A word stretched across a whole break and into the next phrase.
        singing_map = {"lead": [[0, 2], [10, 14]], "backing": []}
        repaired, _ = repair_words([word("on", 1, 12)], singing_map)
        assert spans(repaired) == [(1, 2)]


class TestStartMoved:
    def test_word_starting_in_a_break_starts_with_the_singing(self):
        singing_map = {"lead": [[0, 5], [20, 25]], "backing": []}
        words = [word("door", 12, 21, line=1)]
        repaired, changes = repair_words(words, singing_map)
        assert spans(repaired) == [(20, 21)]
        assert [c.kind for c in changes] == ["start_moved"]

    def test_moved_start_then_cut(self):
        singing_map = {"lead": [[20, 22]], "backing": []}
        repaired, _ = repair_words([word("so", 15, 30)], singing_map)
        assert spans(repaired) == [(20, 22)]


class TestMoved:
    def test_word_alone_in_a_break_moves_to_where_singing_resumes(self):
        singing_map = {"lead": [[0, 5], [20, 25]], "backing": []}
        words = [word("one", 4, 4.8), word("door", 12, 12.5), word("two", 21, 22)]
        repaired, changes = repair_words(words, singing_map)
        assert spans(repaired) == [(4, 4.8), (20, 20.5), (21, 22)]
        assert [(c.index, c.kind) for c in changes] == [(1, "moved")]

    def test_moved_word_stops_at_the_next_word(self):
        singing_map = {"lead": [[0, 5], [20, 25]], "backing": []}
        words = [word("door", 12, 14), word("two", 20.5, 22)]
        repaired, _ = repair_words(words, singing_map)
        assert spans(repaired) == [(20, 20.5), (20.5, 22)]

    def test_words_sharing_a_silence_stay(self):
        # The map may have missed quiet singing: don't pile them up.
        singing_map = {"lead": [[0, 5], [20, 25]], "backing": []}
        words = [
            word("the", 12, 12.2),
            word("love", 12.3, 12.6),
            word("club", 12.7, 13),
        ]
        repaired, changes = repair_words(words, singing_map)
        assert repaired == words
        assert changes == []

    def test_word_in_a_short_gap_stays(self):
        singing_map = {"lead": [[0, 5], [6, 10]], "backing": []}
        repaired, changes = repair_words([word("and", 5.2, 5.6)], singing_map)
        assert spans(repaired) == [(5.2, 5.6)]
        assert changes == []

    def test_word_after_the_last_singing_stays(self):
        singing_map = {"lead": [[0, 5]], "backing": []}
        repaired, changes = repair_words([word("end", 30, 31)], singing_map)
        assert spans(repaired) == [(30, 31)]
        assert changes == []

    def test_next_word_right_where_singing_resumes(self):
        singing_map = {"lead": [[0, 5], [20, 25]], "backing": []}
        words = [word("door", 12, 13), word("two", 20, 21)]
        repaired, changes = repair_words(words, singing_map)
        assert spans(repaired) == [(12, 13), (20, 21)]
        assert changes == []


class TestRepairWords:
    def test_input_is_not_changed(self):
        singing_map = {"lead": [[0, 1]], "backing": []}
        words = [word("held", 0, 10)]
        before = copy.deepcopy(words)
        repaired, _ = repair_words(words, singing_map)
        assert words == before
        assert repaired[0]["word"] == "held" and repaired[0]["score"] == 0.9

    def test_no_sound_measured_changes_nothing(self):
        words = [word("held", 0, 10)]
        repaired, changes = repair_words(words, {"lead": [], "backing": []})
        assert spans(repaired) == [(0, 10)]
        assert changes == []

    def test_words_sung_through_are_untouched(self):
        singing_map = {"lead": [[0, 10]], "backing": []}
        words = [word("a", 0, 1), word("b", 1.2, 4), word("c", 4.5, 9)]
        repaired, changes = repair_words(words, singing_map)
        assert repaired == words
        assert changes == []
