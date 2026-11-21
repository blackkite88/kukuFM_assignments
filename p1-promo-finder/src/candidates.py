"""Candidate window generation over event boundaries using drama heuristics."""

import re
from typing import List

from pydantic import BaseModel

from src.parse import Event

DRAMA_KEYWORDS = {
    "slap",
    "reveal",
    "secret",
    "truth",
    "betray",
    "threat",
    "kill",
    "die",
    "death",
    "murder",
    "money",
    "affair",
    "divorce",
    "pregnant",
    "trap",
    "arrest",
    "exposed",
    "police",
    "evidence",
    "contract",
    "revenge",
    "brother",
    "father",
    "wife",
    "husband",
    "gun",
    "poison",
}


class CandidateWindow(BaseModel):
    window_id: str
    ep: int
    start_s: float
    end_s: float
    duration_s: float
    events: List[Event]
    first_3s_text: str
    keyword_score: float
    punctuation_density: float
    speaker_change_rate: float
    unresolved_last_event: float
    mid_scene_end: float
    heuristic_score: float


def _count_keywords(text: str) -> int:
    tokens = re.findall(r"\b\w+\b", text.lower())
    return sum(1 for tok in tokens if tok in DRAMA_KEYWORDS)


def _compute_punctuation_density(text: str) -> float:
    words = text.split()
    if not words:
        return 0.0
    punc_count = text.count("?") + text.count("!")
    return punc_count / max(len(words), 1)


def _compute_speaker_changes(events: List[Event], duration: float) -> float:
    dialogue_events = [e for e in events if e.type == "dialogue"]
    if len(dialogue_events) <= 1:
        return 0.0
    changes = sum(
        1
        for i in range(len(dialogue_events) - 1)
        if dialogue_events[i].speaker != dialogue_events[i + 1].speaker
    )
    return changes / max(duration, 1.0)


def _is_unresolved(event: Event) -> float:
    text = event.text.strip()
    if text.endswith("?") or text.endswith("...") or text.endswith("--"):
        return 1.0
    if re.search(r"\b(who|why|how|what|stop|wait|never|kill|dead)\b[!]*$", text, re.I):
        return 0.8
    return 0.0


def generate_candidates(events: List[Event], top_n: int = 15) -> List[CandidateWindow]:
    if not events:
        return []

    ep = events[0].ep
    n = len(events)
    candidates: List[CandidateWindow] = []

    for i in range(n):
        for j in range(i, n):
            window_events = events[i : j + 1]
            start_s = window_events[0].start_s
            end_s = window_events[-1].end_s
            dur = round(end_s - start_s, 2)

            if dur < 20.0 or dur > 60.0:
                continue

            first_cutoff = start_s + 3.0
            first_3s = [
                f"{e.speaker}: {e.text}"
                for e in window_events
                if e.start_s <= first_cutoff
            ]
            first_3s_text = " | ".join(first_3s) if first_3s else window_events[0].text

            full_text = " ".join(e.text for e in window_events)
            kw_score = float(_count_keywords(full_text))
            punc_density = _compute_punctuation_density(full_text)
            speaker_rate = _compute_speaker_changes(window_events, dur)
            unresolved = _is_unresolved(window_events[-1])

            mid_scene = 1.0 if (j + 1 < n and events[j + 1].type != "scene") else 0.0

            heuristic = (
                (kw_score * 2.5)
                + (punc_density * 4.0)
                + (speaker_rate * 8.0)
                + (unresolved * 3.0)
                + (mid_scene * 1.5)
            )

            cand = CandidateWindow(
                window_id=f"ep{ep}_{int(start_s)}_{int(end_s)}",
                ep=ep,
                start_s=start_s,
                end_s=end_s,
                duration_s=dur,
                events=window_events,
                first_3s_text=first_3s_text,
                keyword_score=round(kw_score, 2),
                punctuation_density=round(punc_density, 3),
                speaker_change_rate=round(speaker_rate, 3),
                unresolved_last_event=round(unresolved, 2),
                mid_scene_end=mid_scene,
                heuristic_score=round(heuristic, 3),
            )
            candidates.append(cand)

    candidates.sort(key=lambda c: c.heuristic_score, reverse=True)
    return candidates[:top_n]
