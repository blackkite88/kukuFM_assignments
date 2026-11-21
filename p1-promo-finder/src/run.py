"""End-to-end promo finding pipeline execution."""

import argparse
import sys
from pathlib import Path
from typing import List

from src.candidates import generate_candidates
from src.export import export_results
from src.parse import Event, parse_screenplay_file
from src.rank import rank_promos
from src.score import score_candidates
from src.stitch import StitchedPromo, stitch_window


def _build_summary(events: List[Event]) -> str:
    high_drama = [
        e.text
        for e in events
        if any(
            kw in e.text.lower()
            for kw in ("kill", "betray", "secret", "divorce", "slap", "arrest")
        )
    ]
    if high_drama:
        return "Key conflict: " + "; ".join(high_drama[:2])
    return (
        f"Episode covers events from {events[0].speaker} through {events[-1].speaker}."
    )


def run_pipeline(input_dir: str, output_dir: str) -> None:
    in_path = Path(input_dir)
    out_path = Path(output_dir)

    if not in_path.exists():
        print(
            f"Input directory '{input_dir}' does not exist. Please create it and add screenplay files."
        )
        sys.exit(0)

    files = sorted(
        [
            p
            for p in in_path.glob("*")
            if p.is_file()
            and p.name != "README.txt"
            and not p.name.startswith(".")
            and p.suffix.lower() in (".txt", ".md", ".screenplay")
        ]
    )

    if not files:
        print(
            f"No screenplay files found in '{input_dir}'. "
            f"Please place episode files (e.g. ep01.txt .. ep50.txt) into '{input_dir}' as described in data/README.txt."
        )
        return

    print(f"Discovered {len(files)} screenplay file(s) in {input_dir}. Beginning pipeline...")

    all_stitched: List[StitchedPromo] = []
    recent_summaries: List[str] = []

    for file_path in files:
        events = parse_screenplay_file(file_path)
        if not events:
            continue
        ep = events[0].ep
        print(f"Processing Episode {ep:02d} ({file_path.name}) - {len(events)} events parsed.")

        candidates = generate_candidates(events, top_n=15)
        print(f"  Generated {len(candidates)} candidate windows (20-60s).")

        scores = score_candidates(ep, candidates, recent_summaries)

        ep_stitched: List[StitchedPromo] = []
        for cand, sc in zip(candidates, scores):
            stitched = stitch_window(cand, sc, events)
            ep_stitched.append(stitched)

        all_stitched.extend(ep_stitched)
        summary = _build_summary(events)
        recent_summaries.append(f"Ep {ep}: {summary}")
        if len(recent_summaries) > 2:
            recent_summaries.pop(0)

    ranked, rationale = rank_promos(all_stitched)
    export_results(ranked, rationale, out_path)
    print(f"Successfully exported {len(ranked)} ranked promos to '{output_dir}'.")
    if ranked:
        print(f"Top Promo: Rank #1 - {ranked[0].promo_id} (Score: {ranked[0].total_score})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Promo Finder microdrama pipeline."
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/",
        help="Input directory containing screenplay files.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="outputs/",
        help="Output directory to save promos and rationale.",
    )
    args = parser.parse_args()
    run_pipeline(args.input, args.out)


if __name__ == "__main__":
    main()
