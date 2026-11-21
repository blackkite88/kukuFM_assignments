"""Code-based feature extraction for episode ending cliffhanger moments."""

import re
from typing import List, Tuple

from pydantic import BaseModel

from src.parse import Event

SUSPENSE_KEYWORDS = {
    "who",
    "why",
    "how",
    "what",
    "where",
    "kill",
    "die",
    "death",
    "gun",
    "weapon",
    "secret",
    "betray",
    "truth",
    "pregnant",
    "divorce",
    "arrest",
    "police",
    "stop",
    "wait",
    "never",
    "detonator",
    "bomb",
    "marry",
    "heir",
    "poison",
    "murder",
    "father",
    "brother",
    "daughter",
}

RESOLUTION_PATTERNS = [
    r"\b(leaves the room|walks away|smiles and hugs|falls asleep|everything will be fine|peace at last)\b",
    r"\b(they kiss|they embrace|problem solved|apologized|all settled)\b",
]


class EndingFeatures(BaseModel):
    ep: int
    ends_on_keyword: bool
    keyword_matched: str
    ends_mid_action: bool
    last_speaker: str
    last_line_text: str
    scene_resolved: bool
    final_beat_length: float
    ending_transcript: str


def _check_keywords(text: str) -> Tuple[bool, str]:
    tokens = re.findall(r"\b\w+\b", text.lower())
    for tok in tokens:
        if tok in SUSPENSE_KEYWORDS:
            return True, tok
    return False, ""


def _is_scene_resolved(text: str) -> bool:
    t_lower = text.lower()
    for pat in RESOLUTION_PATTERNS:
        if re.search(pat, t_lower):
            return True
    return False


def extract_ending_features(ep: int, ending_events: List[Event]) -> EndingFeatures:
    if not ending_events:
        return EndingFeatures(
            ep=ep,
            ends_on_keyword=False,
            keyword_matched="",
            ends_mid_action=False,
            last_speaker="NONE",
            last_line_text="",
            scene_resolved=True,
            final_beat_length=0.0,
            ending_transcript="",
        )

    last_ev = ending_events[-1]
    transcript_lines = [
        f"[{e.start_s:.1f}s - {e.end_s:.1f}s] {e.speaker}: {e.text}"
        for e in ending_events
    ]
    ending_transcript = "\n".join(transcript_lines)

    has_kw, matched_kw = _check_keywords(last_ev.text)
    if not has_kw:
        for ev in reversed(ending_events[:-1]):
            has_kw, matched_kw = _check_keywords(ev.text)
            if has_kw:
                break

    mid_action = False
    if last_ev.type == "action":
        mid_action = True
    elif (
        last_ev.text.strip().endswith("...")
        or last_ev.text.strip().endswith("--")
        or last_ev.text.strip().endswith("?")
    ):
        mid_action = True

    resolved = _is_scene_resolved(ending_transcript)
    beat_len = round(max(1.0, last_ev.end_s - last_ev.start_s), 2)

    return EndingFeatures(
        ep=ep,
        ends_on_keyword=has_kw,
        keyword_matched=matched_kw,
        ends_mid_action=mid_action,
        last_speaker=last_ev.speaker,
        last_line_text=last_ev.text,
        scene_resolved=resolved,
        final_beat_length=beat_len,
        ending_transcript=ending_transcript,
    )
