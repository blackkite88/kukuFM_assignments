"""Promo ranking, overlap deduplication, diversity capping, and top-1 rationale."""

from typing import List, Tuple

from pydantic import BaseModel

from src.llm import complete
from src.stitch import Segment, StitchedPromo


class RankedPromo(BaseModel):
    rank: int
    promo_id: str
    ep: int
    segments: List[Segment]
    duration_s: float
    hook_text: str
    hook_score: float
    cliffhanger_text: str
    cliffhanger_score: float
    standalone_score: float
    total_score: float
    why: str


def _intervals_overlap(
    segs1: List[Segment], segs2: List[Segment], threshold: float = 0.35
) -> bool:
    if not segs1 or not segs2:
        return False
    if segs1[0].ep != segs2[0].ep:
        return False

    min1 = min(s.start_s for s in segs1)
    max1 = max(s.end_s for s in segs1)
    min2 = min(s.start_s for s in segs2)
    max2 = max(s.end_s for s in segs2)

    inter = max(0.0, min(max1, max2) - max(min1, min2))
    union = max(max1, max2) - min(min1, min2)
    if union <= 0.0:
        return False
    return (inter / union) >= threshold


def rank_promos(promos: List[StitchedPromo]) -> Tuple[List[RankedPromo], str]:
    if not promos:
        return [], "No promos provided to rank."

    scored_items = []
    for p in promos:
        score = round(
            0.35 * p.hook_score + 0.35 * p.cliffhanger_score + 0.30 * p.standalone_score,
            3,
        )
        scored_items.append((score, p))

    scored_items.sort(key=lambda x: x[0], reverse=True)

    deduped: List[Tuple[float, StitchedPromo]] = []
    for score, promo in scored_items:
        overlap = False
        for _, kept in deduped:
            if _intervals_overlap(promo.segments, kept.segments):
                overlap = True
                break
        if not overlap:
            deduped.append((score, promo))

    top10: List[Tuple[float, StitchedPromo]] = []
    ep_counts: dict[int, int] = {}
    remaining: List[Tuple[float, StitchedPromo]] = []

    for score, promo in deduped:
        if len(top10) < 10:
            count = ep_counts.get(promo.ep, 0)
            if count < 2:
                top10.append((score, promo))
                ep_counts[promo.ep] = count + 1
            else:
                remaining.append((score, promo))
        else:
            remaining.append((score, promo))

    final_ordered = top10 + remaining
    ranked: List[RankedPromo] = []
    for idx, (score, p) in enumerate(final_ordered, 1):
        ranked.append(
            RankedPromo(
                rank=idx,
                promo_id=p.promo_id,
                ep=p.ep,
                segments=p.segments,
                duration_s=p.duration_s,
                hook_text=p.hook_text,
                hook_score=p.hook_score,
                cliffhanger_text=p.cliffhanger_text,
                cliffhanger_score=p.cliffhanger_score,
                standalone_score=p.standalone_score,
                total_score=score,
                why=p.why,
            )
        )

    rationale_text = _generate_rationale(ranked[:10])
    return ranked, rationale_text


def _generate_rationale(top_promos: List[RankedPromo]) -> str:
    if not top_promos:
        return "No top promos to analyze."

    top_item = top_promos[0]
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an executive marketing producer for vertical microdramas. "
                "Write a crisp, authoritative markdown rationale explaining why promo #1 "
                "must be deployed as the primary acquisition cut, how it converts cold traffic, "
                "and how the top 10 candidate cuts balance narrative hooks."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Top Ranked Promo:\n"
                f"Rank 1: Promo ID {top_item.promo_id} (Episode {top_item.ep})\n"
                f"Hook: '{top_item.hook_text}' (Score: {top_item.hook_score}/10)\n"
                f"Cliffhanger: '{top_item.cliffhanger_text}' (Score: {top_item.cliffhanger_score}/10)\n"
                f"Standalone Score: {top_item.standalone_score}/10 | Total: {top_item.total_score}\n"
                f"Editorial Summary: {top_item.why}\n\n"
                f"Total Top 10 Promos Count: {len(top_promos)}\n"
                "Output clean markdown with headings: '### Why #1 Deploys First', "
                "'### Cold Audience Conversion Mechanics', and '### Recommended A/B Testing Order'."
            ),
        },
    ]

    try:
        content = complete(prompt)
        return str(content)
    except Exception:
        return (
            f"### Why #1 Deploys First\n\n"
            f"Promo `{top_item.promo_id}` (Episode {top_item.ep}) ranks #1 with composite score **{top_item.total_score}**. "
            f"Its immediate 3-second hook (*\"{top_item.hook_text}\"*, score {top_item.hook_score}/10) establishes immediate conflict "
            f"without requiring prior plot exposition. The concluding cliffhanger (*\"{top_item.cliffhanger_text}\"*, score {top_item.cliffhanger_score}/10) "
            f"creates an open cognitive loop that directly drives audience click-through.\n\n"
            f"### Cold Audience Conversion Mechanics\n\n"
            f"- **Instant Hook**: Captures scroll-stopping retention in the opening 3 seconds.\n"
            f"- **Standalone Clarity**: Rated {top_item.standalone_score}/10 for cold audience comprehension.\n"
            f"- **Unresolved Stakes**: Stops precisely at high emotional tension.\n\n"
            f"### Recommended A/B Testing Order\n\n"
            f"1. Primary Cut: Rank 1 ({top_item.promo_id})\n"
            f"2. Variant Cut: Rank 2\n"
            f"3. Retargeting Cut: Rank 3\n"
        )
