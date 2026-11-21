"""Screenplay parser extracting structured events, final 25s endings, and next 15s intros."""

import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Event(BaseModel):
    ep: int
    start_s: float
    end_s: float
    type: str
    speaker: str
    text: str


class EpisodeSlice(BaseModel):
    ep: int
    total_duration_s: float
    all_events: List[Event]
    ending_events: List[Event]
    intro_events: List[Event]


def _parse_time(t_str: str) -> float:
    cleaned = t_str.strip().strip("[]()")
    parts = cleaned.split(":")
    if len(parts) == 3:
        return float(parts[0]) * 3600.0 + float(parts[1]) * 60.0 + float(parts[2])
    if len(parts) == 2:
        return float(parts[0]) * 60.0 + float(parts[1])
    if len(parts) == 1:
        return float(parts[0])
    raise ValueError(f"Invalid timestamp format: {t_str}")


def _extract_timestamps(line: str) -> Tuple[Optional[float], Optional[float], str]:
    range_match = re.search(
        r"\[?(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*(?:-|to)\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\]?",
        line,
    )
    if range_match:
        start = _parse_time(range_match.group(1))
        end = _parse_time(range_match.group(2))
        rest = (line[: range_match.start()] + line[range_match.end() :]).strip()
        return start, end, rest

    single_match = re.search(r"\[?(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\]?", line)
    if single_match:
        start = _parse_time(single_match.group(1))
        rest = (line[: single_match.start()] + line[single_match.end() :]).strip()
        return start, None, rest

    return None, None, line.strip()


def parse_screenplay_text(text: str, ep: int = 1, filename: str = "stream") -> List[Event]:
    raw_lines = text.splitlines()
    raw_events: List[Tuple[float, Optional[float], str, str, str]] = []
    anomalies: List[str] = []

    for idx, line in enumerate(raw_lines, 1):
        sline = line.strip()
        if not sline:
            continue

        start_s, end_s, rest = _extract_timestamps(sline)
        if start_s is None:
            raise ValueError(
                f"Parsing failed at {filename}:{idx}. Missing timestamp in line: '{sline}'"
            )

        rest = rest.lstrip("-: ").strip()
        ev_type = "dialogue"
        speaker = "NARRATOR"
        body = rest

        scene_match = re.match(r"^\[?(?:SCENE|INT\.|EXT\.)\]?[:\s]*(.*)$", rest, re.IGNORECASE)
        action_match = re.match(r"^\[?(?:ACTION)\]?[:\s]*(.*)$", rest, re.IGNORECASE)
        dialogue_match = re.match(r"^([A-Z0-9_\s]{2,20})[:\s]+(.*)$", rest)

        if scene_match:
            ev_type = "scene"
            speaker = "SCENE"
            body = scene_match.group(1).strip()
        elif action_match:
            ev_type = "action"
            speaker = "ACTION"
            body = action_match.group(1).strip()
        elif dialogue_match:
            speaker_candidate = dialogue_match.group(1).strip()
            if speaker_candidate.upper() in ("SCENE", "ACTION"):
                ev_type = speaker_candidate.lower()
                speaker = speaker_candidate.upper()
                body = dialogue_match.group(2).strip()
            else:
                ev_type = "dialogue"
                speaker = speaker_candidate
                body = dialogue_match.group(2).strip()

        raw_events.append((start_s, end_s, ev_type, speaker, body))

    events: List[Event] = []
    prev_start = -1.0
    for i, (start_s, end_s, ev_type, speaker, body) in enumerate(raw_events):
        if start_s < prev_start:
            anomalies.append(
                f"Non-monotonic timestamp at event {i+1}: {start_s}s followed previous {prev_start}s"
            )
            start_s = prev_start
        prev_start = start_s

        if end_s is None:
            if i + 1 < len(raw_events):
                next_start = raw_events[i + 1][0]
                end_s = max(start_s + 1.0, next_start)
            else:
                end_s = start_s + 3.0
        elif end_s <= start_s:
            anomalies.append(f"Invalid duration at event {i+1}: end {end_s} <= start {start_s}")
            end_s = start_s + 2.0

        events.append(
            Event(
                ep=ep,
                start_s=round(start_s, 2),
                end_s=round(end_s, 2),
                type=ev_type,
                speaker=speaker,
                text=body,
            )
        )

    if anomalies:
        for anom in anomalies:
            logger.warning(f"[{filename}] {anom}")

    return events


def parse_screenplay_file(path: Path | str, ep: Optional[int] = None) -> List[Event]:
    p = Path(path)
    if ep is None:
        match = re.search(r"(\d+)", p.stem)
        ep = int(match.group(1)) if match else 1
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()
    return parse_screenplay_text(content, ep=ep, filename=p.name)


def extract_episode_slice(events: List[Event]) -> EpisodeSlice:
    if not events:
        raise ValueError("Cannot extract slice from empty events list.")

    ep = events[0].ep
    total_dur = round(events[-1].end_s, 2)
    cutoff_ending = max(0.0, total_dur - 25.0)

    ending_events = [e for e in events if e.end_s >= cutoff_ending or e.start_s >= cutoff_ending]
    intro_events = [e for e in events if e.start_s <= 15.0]

    return EpisodeSlice(
        ep=ep,
        total_duration_s=total_dur,
        all_events=events,
        ending_events=ending_events,
        intro_events=intro_events,
    )
