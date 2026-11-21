"""Computes correlation and agreement between model predictions and human labels."""

from pathlib import Path

import pandas as pd


def evaluate_agreement(csv_path: str = "eval/manual_review.csv") -> None:
    p = Path(csv_path)
    if not p.exists():
        print(f"File {csv_path} does not exist.")
        return

    df = pd.read_csv(p)
    labelled = df.dropna(
        subset=["human_hook_score", "human_cliff_score", "human_standalone_score"]
    )
    if labelled.empty:
        print("Manual review template has no completed human labels yet.")
        print(
            "Fill in human_hook_score, human_cliff_score, human_standalone_score in eval/manual_review.csv."
        )
        return

    hook_corr = labelled["hook_score_pred"].corr(labelled["human_hook_score"])
    cliff_corr = labelled["cliff_score_pred"].corr(labelled["human_cliff_score"])
    stand_corr = labelled["standalone_score_pred"].corr(
        labelled["human_standalone_score"]
    )

    print("=== Model vs Human Agreement Metrics ===")
    print(f"Sample Size: {len(labelled)} rows")
    print(f"Hook Score Pearson Correlation: {hook_corr:.3f}")
    print(f"Cliffhanger Score Pearson Correlation: {cliff_corr:.3f}")
    print(f"Standalone Score Pearson Correlation: {stand_corr:.3f}")


if __name__ == "__main__":
    evaluate_agreement()
