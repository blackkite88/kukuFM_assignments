"""Promo stitcher joining earlier context segments for low standalone scores."""

from typing import List, Optional

from pydantic import BaseModel

from src.candidates import CandidateWindow
from src.llm import complete
from src.parse import Event
from src.score import WindowScore


class Segment(BaseModel):
    ep: int
    start_s: float
    end_s: float


class StitchedPromo(BaseModel):
    promo_id: str
    ep: int
    segments: List[Segment]
    duration_s: float
    hook_text: str
    hook_score: float
    cliffhanger_text: str
    cliffhanger_score: float
    standalone_score: float
    why: str


class StitchDecision(BaseModel):
    should_stitch: bool
    earlier_start_s: Optional[float] = None
    earlier_end_s: Optional[float] = None
    new_standalone_score: float
    why: str


def stitch_window(
    candidate: CandidateWindow,
    score: WindowScore,
    all_events: List[Event],
) -> StitchedPromo:
    if score.standalone_score >= 6.0:
        return StitchedPromo(
            promo_id=candidate.window_id,
            ep=candidate.ep,
            segments=[
                Segment(
                    ep=candidate.ep,
                    start_s=candidate.start_s,
                    end_s=candidate.end_s,
                )
            ],
            duration_s=candidate.duration_s,
            hook_text=score.hook_text,
            hook_score=score.hook_score,
            cliffhanger_text=score.cliffhanger_text,
            cliffhanger_score=score.cliffhanger_score,
            standalone_score=score.standalone_score,
            why=score.why,
        )

    earlier_events = [e for e in all_events if e.end_s <= candidate.start_s]
    max_extra = 60.0 - candidate.duration_s

    if not earlier_events or max_extra < 5.0:
        return StitchedPromo(
            promo_id=candidate.window_id,
            ep=candidate.ep,
            segments=[
                Segment(
                    ep=candidate.ep,
                    start_s=candidate.start_s,
                    end_s=candidate.end_s,
                )
            ],
            duration_s=candidate.duration_s,
            hook_text=score.hook_text,
            hook_score=score.hook_score,
            cliffhanger_text=score.cliffhanger_text,
            cliffhanger_score=score.cliffhanger_score,
            standalone_score=score.standalone_score,
            why=score.why,
        )

    earlier_text = "\n".join(
        f"[{e.start_s:.1f}s - {e.end_s:.1f}s] {e.speaker}: {e.text}"
        for e in earlier_events[-5:]
    )
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an editor assembling a microdrama promo. The main clip lacks standalone context. "
                "Decide if adding a short earlier setup clip (5-15s) makes the promo make sense standalone. "
                "Total duration must not exceed 60s. Output valid JSON."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Main clip ({candidate.start_s:.1f}s - {candidate.end_s:.1f}s, duration {candidate.duration_s:.1f}s):\n"
                f"Missing context: {score.missing_context}\n"
                f"Earlier candidate scenes in episode {candidate.ep}:\n{earlier_text}\n"
                f"Max extra duration allowed: {max_extra:.1f}s.\n"
                "Return JSON with keys: should_stitch (bool), earlier_start_s (float or null), "
                "earlier_end_s (float or null), new_standalone_score (float), why (str)."
            ),
        },
    ]

    try:
        decision: StitchDecision = complete(prompt, schema=StitchDecision)
        if (
            decision.should_stitch
            and decision.earlier_start_s is not None
            and decision.earlier_end_s is not None
        ):
            e_start = round(decision.earlier_start_s, 2)
            e_end = round(decision.earlier_end_s, 2)
            extra_dur = e_end - e_start
            if 0.0 < extra_dur <= max_extra and e_end <= candidate.start_s:
                segments = [
                    Segment(ep=candidate.ep, start_s=e_start, end_s=e_end),
                    Segment(ep=candidate.ep, start_s=candidate.start_s, end_s=candidate.end_s),
                ]
                tot_dur = round(extra_dur + candidate.duration_s, 2)
                return StitchedPromo(
                    promo_id=f"{candidate.window_id}_stitched",
                    ep=candidate.ep,
                    segments=segments,
                    duration_s=tot_dur,
                    hook_text=score.hook_text,
                    hook_score=score.hook_score,
                    cliffhanger_text=score.cliffhanger_text,
                    cliffhanger_score=score.cliffhanger_score,
                    standalone_score=decision.new_standalone_score,
                    why=f"{score.why} (Stitched context: {decision.why})",
                )
    except Exception:
        pass

    fallback_setup = earlier_events[-1]
    setup_dur = fallback_setup.end_s - fallback_setup.start_s
    if 3.0 <= setup_dur <= max_extra:
        segments = [
            Segment(ep=candidate.ep, start_s=fallback_setup.start_s, end_s=fallback_setup.end_s),
            Segment(ep=candidate.ep, start_s=candidate.start_s, end_s=candidate.end_s),
        ]
        return StitchedPromo(
            promo_id=f"{candidate.window_id}_stitched",
            ep=candidate.ep,
            segments=segments,
            duration_s=round(setup_dur + candidate.duration_s, 2),
            hook_text=score.hook_text,
            hook_score=score.hook_score,
            cliffhanger_text=score.cliffhanger_text,
            cliffhanger_score=score.cliffhanger_score,
            standalone_score=6.5,
            why=f"{score.why} (Joined setup from {fallback_setup.start_s:.1f}s)",
        )

    return StitchedPromo(
        promo_id=candidate.window_id,
        ep=candidate.ep,
        segments=[
            Segment(
                ep=candidate.ep,
                start_s=candidate.start_s,
                end_s=candidate.end_s,
            )
        ],
        duration_s=candidate.duration_s,
        hook_text=score.hook_text,
        hook_score=score.hook_score,
        cliffhanger_text=score.cliffhanger_text,
        cliffhanger_score=score.cliffhanger_score,
        standalone_score=score.standalone_score,
        why=score.why,
    )
