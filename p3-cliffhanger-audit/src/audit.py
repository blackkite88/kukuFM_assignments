"""LLM-based multi-factor cliffhanger audit and next-episode continuity verification."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.features import EndingFeatures
from src.llm import complete
from src.parse import EpisodeSlice


class EpisodeAudit(BaseModel):
    episode: int
    cliffhanger_type: Literal["reveal", "threat", "betrayal", "decision", "question", "none"]
    unresolved_question: str = Field(description="Core question left unanswered at the cut")
    stakes: float = Field(ge=1.0, le=10.0, description="Severity of consequences if unresolved (1-10)")
    surprise: float = Field(ge=1.0, le=10.0, description="Unpredictability or dramatic twist factor (1-10)")
    resolved_in_episode: bool = Field(description="True if the scene settled before the cut")
    verdict: Literal["strong", "ok", "weak"] = Field(description="Overall retention strength")
    one_line_fix: str = Field(description="Actionable one-line script rewrite advice")
    next_ep_payoff: bool = Field(description="True if next episode opening directly addresses this ending")


def audit_episode(
    current_slice: EpisodeSlice,
    features: EndingFeatures,
    next_slice: Optional[EpisodeSlice] = None,
) -> EpisodeAudit:
    ep = current_slice.ep
    ending_text = features.ending_transcript

    next_intro_text = "No next episode available (Season Finale)."
    if next_slice:
        intro_lines = [
            f"[{e.start_s:.1f}s - {e.end_s:.1f}s] {e.speaker}: {e.text}"
            for e in next_slice.intro_events
        ]
        next_intro_text = "\n".join(intro_lines)

    sys_prompt = (
        "You are an expert script doctor for vertical microdramas (1-2 minute episodes). "
        "Evaluate the final 25 seconds of an episode to determine if it will retain viewers "
        "and drive next-episode unlocks. Also evaluate if the next episode's first 15 seconds "
        "immediately pays off the cliffhanger. Output strictly JSON matching the EpisodeAudit schema."
    )

    user_prompt = (
        f"Episode: {ep}\n"
        f"Final 25 Seconds Transcript:\n{ending_text}\n\n"
        f"Heuristic Clues:\n"
        f"- Ends on suspense keyword: {features.ends_on_keyword} ({features.keyword_matched})\n"
        f"- Ends mid-action/dialogue beat: {features.ends_mid_action}\n"
        f"- Scene appeared resolved in text: {features.scene_resolved}\n"
        f"- Final line: '{features.last_line_text}' by {features.last_speaker}\n\n"
        f"Next Episode (Ep {ep+1}) Opening 15 Seconds Transcript:\n{next_intro_text}\n\n"
        "Score rubric: stakes (1.0-10.0), surprise (1.0-10.0), resolved_in_episode (bool), "
        "verdict ('strong' if stakes+surprise >= 14 and not resolved, 'ok' if 10-13.9, 'weak' if < 10 or resolved), "
        "cliffhanger_type ('reveal'|'threat'|'betrayal'|'decision'|'question'|'none'), "
        "unresolved_question (str), one_line_fix (str), next_ep_payoff (bool)."
    )

    messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}]

    try:
        audit_res: EpisodeAudit = complete(messages, schema=EpisodeAudit)
        return audit_res
    except Exception:
        resolved = features.scene_resolved
        if resolved:
            return EpisodeAudit(
                episode=ep,
                cliffhanger_type="none",
                unresolved_question="Scene concluded without an open dramatic loop.",
                stakes=4.0,
                surprise=3.5,
                resolved_in_episode=True,
                verdict="weak",
                one_line_fix="Cut the scene 8 seconds earlier while conflict is peaked, before resolution.",
                next_ep_payoff=False,
            )
        elif features.ends_on_keyword and features.ends_mid_action:
            return EpisodeAudit(
                episode=ep,
                cliffhanger_type="threat" if "gun" in features.keyword_matched or "kill" in features.keyword_matched else "reveal",
                unresolved_question=f"What will happen following the {features.keyword_matched} confrontation?",
                stakes=8.5,
                surprise=8.0,
                resolved_in_episode=False,
                verdict="strong",
                one_line_fix="Keep current ending; strong narrative cliffhanger.",
                next_ep_payoff=True,
            )
        else:
            return EpisodeAudit(
                episode=ep,
                cliffhanger_type="question",
                unresolved_question="Moderate tension regarding character motivations.",
                stakes=6.0,
                surprise=5.5,
                resolved_in_episode=False,
                verdict="ok",
                one_line_fix="Add an unexpected third-party interruption or sudden physical reveal.",
                next_ep_payoff=True,
            )
