"""Automated tests for parser, candidate generation, ranking, and schemas."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.candidates import generate_candidates
from src.parse import Event, parse_screenplay_file, parse_screenplay_text
from src.rank import _intervals_overlap, rank_promos
from src.score import EpisodeScores, WindowScore
from src.stitch import Segment, StitchedPromo, stitch_window

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parser_on_fixtures():
    files = list(FIXTURES_DIR.glob("*.txt"))
    assert len(files) == 3
    for f in files:
        events = parse_screenplay_file(f)
        assert len(events) >= 5
        for i in range(len(events) - 1):
            assert events[i].start_s <= events[i + 1].start_s
            assert events[i].start_s < events[i].end_s


def test_parser_unparseable_line_raises_error():
    bad_screenplay = "Scene without any timestamps or markers."
    with pytest.raises(ValueError) as exc:
        parse_screenplay_text(bad_screenplay, ep=1, filename="test.txt")
    assert "Parsing failed at test.txt:1" in str(exc.value)


def test_candidate_window_length_always_20_to_60s():
    events = parse_screenplay_file(FIXTURES_DIR / "ep01.txt")
    candidates = generate_candidates(events, top_n=20)
    assert len(candidates) > 0
    for cand in candidates:
        assert 20.0 <= cand.duration_s <= 60.0
        assert cand.start_s == cand.events[0].start_s
        assert cand.end_s == cand.events[-1].end_s
        assert cand.speaker_change_rate >= 0.0


def test_deduplication_removes_overlaps():
    seg1 = [Segment(ep=1, start_s=10.0, end_s=40.0)]
    seg2 = [Segment(ep=1, start_s=12.0, end_s=42.0)]
    assert _intervals_overlap(seg1, seg2, threshold=0.35)

    p1 = StitchedPromo(
        promo_id="p1",
        ep=1,
        segments=seg1,
        duration_s=30.0,
        hook_text="Hook 1",
        hook_score=9.0,
        cliffhanger_text="Cliff 1",
        cliffhanger_score=9.0,
        standalone_score=9.0,
        why="Strong cut",
    )
    p2 = StitchedPromo(
        promo_id="p2",
        ep=1,
        segments=seg2,
        duration_s=30.0,
        hook_text="Hook 2",
        hook_score=7.0,
        cliffhanger_text="Cliff 2",
        cliffhanger_score=7.0,
        standalone_score=7.0,
        why="Duplicate cut",
    )
    ranked, _ = rank_promos([p1, p2])
    assert len(ranked) == 1
    assert ranked[0].promo_id == "p1"


def test_schema_validity():
    ev = Event(ep=1, start_s=0.0, end_s=5.0, type="dialogue", speaker="A", text="Hello")
    assert ev.ep == 1

    with pytest.raises(ValidationError):
        WindowScore(
            window_id="test",
            hook_text="hi",
            hook_score=15.0,
            cliffhanger_text="bye",
            cliffhanger_score=5.0,
            standalone_score=5.0,
            why="test",
        )

    valid_score = WindowScore(
        window_id="ep1_0_25",
        hook_text="Sign now!",
        hook_score=8.5,
        cliffhanger_text="Who told you?",
        cliffhanger_score=8.0,
        standalone_score=7.0,
        missing_context=[],
        why="Grounded confrontation",
    )
    ep_scores = EpisodeScores(episode=1, scores=[valid_score])
    assert len(ep_scores.scores) == 1


def test_stitch_respects_max_duration():
    events = parse_screenplay_file(FIXTURES_DIR / "ep01.txt")
    candidates = generate_candidates(events, top_n=5)
    cand = candidates[0]
    score = WindowScore(
        window_id=cand.window_id,
        hook_text=cand.first_3s_text,
        hook_score=7.0,
        cliffhanger_text=cand.events[-1].text,
        cliffhanger_score=7.0,
        standalone_score=4.0,
        missing_context=["Missing backstory"],
        why="Needs setup",
    )
    stitched = stitch_window(cand, score, events)
    assert 20.0 <= stitched.duration_s <= 60.0
