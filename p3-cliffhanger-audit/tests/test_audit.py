"""Automated tests for parser, slice extraction, feature extraction, and audit schemas."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from src.audit import EpisodeAudit
from src.features import extract_ending_features
from src.parse import extract_episode_slice, parse_screenplay_file

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


def test_ending_extraction_lengths():
    events = parse_screenplay_file(FIXTURES_DIR / "ep01.txt")
    ep_slice = extract_episode_slice(events)

    assert len(ep_slice.all_events) == len(events)
    assert ep_slice.total_duration_s == events[-1].end_s
    assert len(ep_slice.ending_events) > 0
    assert len(ep_slice.intro_events) > 0

    cutoff = ep_slice.total_duration_s - 25.0
    for e in ep_slice.ending_events:
        assert e.end_s >= cutoff or e.start_s >= cutoff

    for e in ep_slice.intro_events:
        assert e.start_s <= 15.0


def test_feature_extraction_detects_suspense():
    events = parse_screenplay_file(FIXTURES_DIR / "ep01.txt")
    ep_slice = extract_episode_slice(events)
    feats = extract_ending_features(ep_slice.ep, ep_slice.ending_events)

    assert feats.ep == 1
    assert feats.ends_on_keyword
    assert feats.ends_mid_action
    assert not feats.scene_resolved
    assert feats.final_beat_length > 0.0


def test_audit_schema_validity():
    with pytest.raises(ValidationError):
        EpisodeAudit(
            episode=1,
            cliffhanger_type="invalid_type",
            unresolved_question="Test",
            stakes=15.0,
            surprise=5.0,
            resolved_in_episode=False,
            verdict="strong",
            one_line_fix="Fix",
            next_ep_payoff=True,
        )

    valid_audit = EpisodeAudit(
        episode=1,
        cliffhanger_type="reveal",
        unresolved_question="Who is the real biological heir?",
        stakes=9.0,
        surprise=8.5,
        resolved_in_episode=False,
        verdict="strong",
        one_line_fix="Excellent tension.",
        next_ep_payoff=True,
    )
    assert valid_audit.episode == 1
    assert valid_audit.verdict == "strong"
