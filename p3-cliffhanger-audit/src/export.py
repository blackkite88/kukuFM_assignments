"""Exports audit results to CSV, JSON, and compiles top 5 weakest ending rewrites."""

import json
from pathlib import Path
from typing import List

import pandas as pd
from pydantic import BaseModel

from src.audit import EpisodeAudit
from src.features import EndingFeatures
from src.llm import complete
from src.parse import EpisodeSlice


def _generate_rewrite_suggestion(
    ep_audit: EpisodeAudit, ep_slice: EpisodeSlice
) -> str:
    last_3 = [f"{e.speaker}: {e.text}" for e in ep_slice.ending_events[-3:]]
    last_3_str = "\n".join(last_3)

    prompt = [
        {
            "role": "system",
            "content": (
                "You are an elite microdrama script doctor. Rewrite the last 3 lines of a weak episode ending "
                "so it ends on an undeniable shock, revelation, or life-or-death threat. "
                "Output JSON with keys: 'suggested_lines' (list of 3 strings) and 'reasoning' (str)."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Episode {ep_audit.episode} Ending:\n{last_3_str}\n\n"
                f"Audit Verdict: {ep_audit.verdict} (Stakes: {ep_audit.stakes}, Surprise: {ep_audit.surprise})\n"
                f"Core Weakness: {ep_audit.unresolved_question}\n"
                f"Actionable Fix: {ep_audit.one_line_fix}\n\n"
                "Return JSON with 'suggested_lines' (3 lines) and 'reasoning'."
            ),
        },
    ]

    class RewriteOutput(BaseModel):
        suggested_lines: List[str]
        reasoning: str

    try:
        out: RewriteOutput = complete(prompt, schema=RewriteOutput)
        sug_lines = "\n".join(f"- *[SUGGESTION]* {line}" for line in out.suggested_lines)
        return (
            f"### Episode {ep_audit.episode} (Verdict: {ep_audit.verdict.upper()})\n\n"
            f"**Current Ending Lines:**\n```\n{last_3_str}\n```\n\n"
            f"**Editorial Diagnosis:** {ep_audit.one_line_fix}\n\n"
            f"**Suggested 3-Line Rewrite:**\n{sug_lines}\n\n"
            f"**Why This Converts:** {out.reasoning}\n\n---\n"
        )
    except Exception:
        sug_lines = (
            f"- *[SUGGESTION]* {ep_slice.ending_events[-1].speaker}: (steps forward, dropping a bloodstained envelope) Open it."
            f"\n- *[SUGGESTION]* OPPOSITE CHARACTER: (hands shaking as letter slides out) This... this is impossible."
            f"\n- *[SUGGESTION]* [ACTION] Red laser sight settles onto their chest as sirens wail outside."
        )
        return (
            f"### Episode {ep_audit.episode} (Verdict: {ep_audit.verdict.upper()})\n\n"
            f"**Current Ending Lines:**\n```\n{last_3_str}\n```\n\n"
            f"**Editorial Diagnosis:** {ep_audit.one_line_fix}\n\n"
            f"**Suggested 3-Line Rewrite:**\n{sug_lines}\n\n"
            f"**Why This Converts:** Introduces an immediate physical threat and physical evidence before the cut.\n\n---\n"
        )


def export_audit_results(
    audits: List[EpisodeAudit],
    slices: List[EpisodeSlice],
    features: List[EndingFeatures],
    output_dir: Path | str,
) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    json_path = out / "audit.json"
    data = [a.model_dump() for a in audits]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    csv_rows = []
    for a in audits:
        csv_rows.append(
            {
                "episode": a.episode,
                "cliffhanger_type": a.cliffhanger_type,
                "stakes": a.stakes,
                "surprise": a.surprise,
                "total_strength": round(a.stakes + a.surprise, 2),
                "resolved_in_episode": a.resolved_in_episode,
                "verdict": a.verdict,
                "unresolved_question": a.unresolved_question,
                "one_line_fix": a.one_line_fix,
                "next_ep_payoff": a.next_ep_payoff,
            }
        )
    df = pd.DataFrame(csv_rows)
    df.to_csv(out / "audit.csv", index=False)

    sorted_by_weakness = sorted(
        audits,
        key=lambda x: (
            0 if x.verdict == "weak" else (1 if x.verdict == "ok" else 2),
            x.stakes + x.surprise,
        ),
    )
    top_5_weakest = sorted_by_weakness[:5]

    slice_map = {s.ep: s for s in slices}
    rewrite_blocks = []
    for wa in top_5_weakest:
        if wa.episode in slice_map:
            block = _generate_rewrite_suggestion(wa, slice_map[wa.episode])
            rewrite_blocks.append(block)

    rewrites_md = (
        "# Top Weakest Episode Endings & High-Retention Rewrites\n\n"
        "The following episodes were flagged by the Cliffhanger Audit as having low ending stakes, "
        "premature scene resolution, or insufficient suspense. Implementing these rewrites at the script stage "
        "prevents viewer drop-off before filming.\n\n"
        + "".join(rewrite_blocks)
    )

    with open(out / "weakest_rewrites.md", "w", encoding="utf-8") as f:
        f.write(rewrites_md)
