"""Computes agreement metrics and 3x3 confusion matrix between model and manual labels."""

from pathlib import Path

import pandas as pd


def evaluate_editorial_agreement(csv_path: str = "eval/manual_labels.csv") -> None:
    p = Path(csv_path)
    if not p.exists():
        print(f"File {csv_path} does not exist.")
        return

    df = pd.read_csv(p)
    labelled = df.dropna(subset=["human_verdict"])
    if labelled.empty:
        print("Manual labels template has no completed human verdicts yet.")
        print("Populate human_verdict ('strong', 'ok', 'weak') in eval/manual_labels.csv to run metrics.")
        return

    exact_matches = sum(labelled["verdict_pred"] == labelled["human_verdict"])
    total = len(labelled)
    accuracy = (exact_matches / total) * 100.0

    print("=== Editorial Agreement Evaluation ===")
    print(f"Total Sampled Episodes: {total}")
    print(f"Categorical Verdict Agreement: {accuracy:.1f}% (Target: >= 70.0%)")

    categories = ["strong", "ok", "weak"]
    cm = pd.crosstab(
        labelled["human_verdict"],
        labelled["verdict_pred"],
        rownames=["Human Verdict"],
        colnames=["Model Prediction"],
    ).reindex(index=categories, columns=categories, fill_value=0)

    print("\n3x3 Confusion Matrix:")
    print(cm)


if __name__ == "__main__":
    evaluate_editorial_agreement()
