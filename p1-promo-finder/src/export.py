"""Export pipeline results to JSON, CSV, and markdown rationale."""

import json
from pathlib import Path
from typing import List

import pandas as pd

from src.rank import RankedPromo


def export_results(
    ranked_promos: List[RankedPromo], rationale: str, output_dir: Path | str
) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    json_path = out / "promos.json"
    data = [p.model_dump() for p in ranked_promos]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    csv_rows = []
    for p in ranked_promos:
        segs_str = "; ".join(
            f"ep{s.ep}:{s.start_s:.1f}s-{s.end_s:.1f}s" for s in p.segments
        )
        csv_rows.append(
            {
                "rank": p.rank,
                "promo_id": p.promo_id,
                "ep": p.ep,
                "duration_s": p.duration_s,
                "segments": segs_str,
                "hook_text": p.hook_text,
                "hook_score": p.hook_score,
                "cliffhanger_text": p.cliffhanger_text,
                "cliffhanger_score": p.cliffhanger_score,
                "standalone_score": p.standalone_score,
                "total_score": p.total_score,
                "why": p.why,
            }
        )
    df = pd.DataFrame(csv_rows)
    df.to_csv(out / "promos.csv", index=False)

    rationale_path = out / "top10_rationale.md"
    with open(rationale_path, "w", encoding="utf-8") as f:
        f.write(rationale)
