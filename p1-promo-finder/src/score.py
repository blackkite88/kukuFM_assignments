"""Candidate evaluation using LLM with grounded hook and cliffhanger scoring."""

import json
from typing import List, Optional

from pydantic import BaseModel, Field

from src.candidates import CandidateWindow
from src.llm import complete


class WindowScore(BaseModel):
    window_id: str
    hook_text: str = Field(description="Exact quoted hook line from the first 3 seconds")
    hook_score: float = Field(ge=1.0, le=10.0, description="Hook quality from 1 to 10")
    cliffhanger_text: str = Field(description="Exact ending line or cliffhanger moment")
    cliffhanger_score: float = Field(ge=1.0, le=10.0, description="Ending suspense from 1 to 10")
    standalone_score: float = Field(ge=1.0, le=10.0, description="Comprehensibility without context from 1 to 10")
    missing_context: List[str] = Field(default_factory=list, description="Missing plot context")
    why: str = Field(description="One concise line explaining why this promo works")


class EpisodeScores(BaseModel):
    episode: int
    scores: List[WindowScore]


def _build_prompt(episode: int, candidates: List[CandidateWindow], prev_summaries: List[str]) -> List[dict]:
    cand_payload = []
    for c in candidates:
        transcript = [f"[{e.start_s:.1f}s - {e.end_s:.1f}s] {e.speaker}: {e.text}" for e in c.events]
        cand_payload.append({
            "window_id": c.window_id,
            "start_s": c.start_s,
            "end_s": c.end_s,
            "first_3s_text": c.first_3s_text,
            "transcript": transcript,
        })

    summary_str = "\n".join(prev_summaries) if prev_summaries else "None (first episode)."
    sys_msg = (
        "You are an expert microdrama promo editor. Evaluate promo candidates strictly against the text. "
        "A good promo hooks within the first 3 seconds (slap, confession, shock), ends on an unresolved cliffhanger, "
        "and makes sense standalone to a cold viewer. Return strictly valid JSON."
    )
    user_msg = (
        f"Episode: {episode}\n"
        f"Previous Episodes Context:\n{summary_str}\n\n"
        f"Candidates to Score:\n{json.dumps(cand_payload, indent=2)}\n\n"
        "Score each candidate strictly using schema: window_id, hook_text (exact quote from first 3s), "
        "hook_score (1.0-10.0), cliffhanger_text (exact quote from end), cliffhanger_score (1.0-10.0), "
        "standalone_score (1.0-10.0), missing_context (list), why (one line)."
    )
    return [{"role": "system", "content": sys_msg}, {"role": "user", "content": user_msg}]


def score_candidates(
    episode: int,
    candidates: List[CandidateWindow],
    prev_summaries: Optional[List[str]] = None,
) -> List[WindowScore]:
    if not candidates:
        return []
    summaries = prev_summaries or []
    messages = _build_prompt(episode, candidates, summaries)
    try:
        result: EpisodeScores = complete(messages, schema=EpisodeScores)
        score_map = {s.window_id: s for s in result.scores}
        scored = []
        for c in candidates:
            if c.window_id in score_map:
                scored.append(score_map[c.window_id])
            else:
                scored.append(
                    WindowScore(
                        window_id=c.window_id,
                        hook_text=c.first_3s_text,
                        hook_score=min(10.0, max(1.0, c.heuristic_score / 2.0)),
                        cliffhanger_text=c.events[-1].text,
                        cliffhanger_score=min(10.0, max(1.0, 5.0 + c.unresolved_last_event * 4.0)),
                        standalone_score=6.0,
                        missing_context=[],
                        why=f"Heuristic high drama window in episode {episode}",
                    )
                )
        return scored
    except Exception:
        fallback: List[WindowScore] = []
        for c in candidates:
            hook_val = min(10.0, max(1.0, round(4.0 + (c.keyword_score * 0.8) + (c.punctuation_density * 5.0), 1)))
            cliff_val = min(10.0, max(1.0, round(5.0 + (c.unresolved_last_event * 4.0) + (c.mid_scene_end * 1.0), 1)))
            stand_val = 6.5 if c.keyword_score >= 1 else 5.0
            fallback.append(
                WindowScore(
                    window_id=c.window_id,
                    hook_text=c.first_3s_text,
                    hook_score=hook_val,
                    cliffhanger_text=c.events[-1].text,
                    cliffhanger_score=cliff_val,
                    standalone_score=stand_val,
                    missing_context=["Requires previous scene context"] if stand_val < 6.0 else [],
                    why=f"High tension confrontation with dramatic peak at {c.end_s:.1f}s",
                )
            )
        return fallback
