"""CLI runner executing end-to-end cliffhanger audit pipeline."""

import argparse
import sys
from pathlib import Path
from typing import List

from src.audit import EpisodeAudit, audit_episode
from src.export import export_audit_results
from src.features import EndingFeatures, extract_ending_features
from src.parse import EpisodeSlice, extract_episode_slice, parse_screenplay_file


def run_pipeline(input_dir: str, output_dir: str) -> None:
    in_path = Path(input_dir)
    out_path = Path(output_dir)

    if not in_path.exists():
        print(f"Input directory '{input_dir}' does not exist.")
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

    print(f"Found {len(files)} episode screenplay file(s) in {input_dir}. Beginning audit...")

    slices: List[EpisodeSlice] = []
    for f in files:
        events = parse_screenplay_file(f)
        if events:
            ep_slice = extract_episode_slice(events)
            slices.append(ep_slice)

    features_list: List[EndingFeatures] = []
    audits: List[EpisodeAudit] = []

    for idx, curr_slice in enumerate(slices):
        feats = extract_ending_features(curr_slice.ep, curr_slice.ending_events)
        features_list.append(feats)

        next_slice = slices[idx + 1] if idx + 1 < len(slices) else None
        print(f"Auditing Episode {curr_slice.ep:02d} (Duration: {curr_slice.total_duration_s:.1f}s)...")
        ep_audit = audit_episode(curr_slice, feats, next_slice)
        audits.append(ep_audit)
        print(f"  Verdict: {ep_audit.verdict.upper()} | Stakes: {ep_audit.stakes}/10 | Surprise: {ep_audit.surprise}/10")

    export_audit_results(audits, slices, features_list, out_path)

    strong_count = sum(1 for a in audits if a.verdict == "strong")
    ok_count = sum(1 for a in audits if a.verdict == "ok")
    weak_count = sum(1 for a in audits if a.verdict == "weak")

    print(f"\nAudit complete! Evaluated {len(audits)} episodes:")
    print(f"  - Strong Endings: {strong_count}")
    print(f"  - OK Endings:     {ok_count}")
    print(f"  - Weak Endings:   {weak_count} (Immediate rewrites recommended)")
    print(f"Results saved to '{output_dir}'.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit microdrama screenplay endings.")
    parser.add_argument(
        "--input",
        type=str,
        default="data/",
        help="Directory containing screenplay files.",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="outputs/",
        help="Directory to save audit CSV, JSON, and rewrites.",
    )
    args = parser.parse_args()
    run_pipeline(args.input, args.out)


if __name__ == "__main__":
    main()
