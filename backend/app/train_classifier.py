"""Reproduce and export evaluation; no database or external AI API is used."""
import argparse
import csv
import json
from pathlib import Path

from .classifier import CategoryModel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "evaluation")
    args = parser.parse_args()
    model = CategoryModel()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(json.dumps(model.report, indent=2) + "\n", encoding="utf-8")
    membership = {s: [{"id": r["id"], "group": r["group"], "category": r["category"]} for r in rows]
                  for s, rows in model.splits.items()}
    (args.output / "split_manifest.json").write_text(json.dumps(membership, indent=2) + "\n", encoding="utf-8")
    with (args.output / "test_predictions.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["id", "group", "actual", "top_prediction", "model_score", "suggested_category", "reason"])
        for row in model.splits["test"]:
            result = model.predict(row["text"])
            writer.writerow([row["id"], row["group"], row["category"], result["scores"][0]["category"],
                             result["model_score"], result["suggested_category"], result["reason"]])
    with (args.output / "confusion_matrix.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["actual / predicted", *model.labels])
        writer.writerows([label, *row] for label, row in zip(model.labels, model.report["test"]["confusion_matrix"]))
    test = model.report["test"]
    print("English synthetic demonstration only; real-office performance has NOT been measured.")
    print(f"Examples: {model.report['examples']}; train/validation/test: {model.report['split_counts']}")
    print(f"Held-out accuracy: {test['accuracy']:.2%}; macro-F1: {test['macro_f1']:.4f}")
    print(f"Suggestion coverage: {test['coverage']:.2%}; score threshold: {model.threshold}")
    print(f"Evaluation files: {args.output.resolve()}")


if __name__ == "__main__":
    main()
