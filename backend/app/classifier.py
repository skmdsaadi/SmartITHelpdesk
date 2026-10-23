"""Small, reproducible English demo classifier. Never deserializes executable models.

The pipeline is fitted once per process on the bundled training partition. Validation
selects an abstention threshold; held-out test rows are used only for reporting.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import logging
from pathlib import Path
import platform
import re
import threading
import unicodedata

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CATEGORIES = ("Access", "Email", "Hardware", "Network", "Printer", "Software")
ALGORITHM_VERSION = "tfidf-lr-demo-v1"
SPLIT_SEED = "helpdesk-group-split-27"
MIN_MARGIN = 0.10
MIN_SIMILARITY = 0.12
THRESHOLDS = (0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.01)
_model = None
_failed = False
_lock = threading.Lock()
log = logging.getLogger(__name__)


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).lower().split())


def input_issue(text: str) -> str | None:
    if any(char.isalpha() and "LATIN" not in unicodedata.name(char, "") for char in text):
        return "unsupported_language"
    if len(set(re.findall(r"[a-z]{2,}", normalize(text)))) < 4:
        return "insufficient_detail"
    return None


def read_dataset(data_dir: Path = DATA_DIR):
    rows = json.loads((data_dir / "ticket_examples.json").read_text(encoding="utf-8"))
    negatives = json.loads((data_dir / "out_of_scope.json").read_text(encoding="utf-8"))
    if not rows or len(rows) > 20000:
        raise ValueError("Dataset must contain 1 to 20,000 examples.")
    ids, texts, groups = set(), set(), {}
    for row in rows:
        if row["category"] not in CATEGORIES or row["language"] != "en":
            raise ValueError("Invalid category or language in dataset.")
        key = re.sub(r"[^a-z0-9]+", " ", normalize(row["text"])).strip()
        if row["id"] in ids or key in texts or len(row["text"]) > 10000 or input_issue(row["text"]):
            raise ValueError("Duplicate or invalid training example.")
        ids.add(row["id"]); texts.add(key)
        if row["group"] in groups and groups[row["group"]] != row["category"]:
            raise ValueError("Each intent group must have exactly one category.")
        groups[row["group"]] = row["category"]
    partitions = {}
    for category in CATEGORIES:
        names = sorted((g for g, c in groups.items() if c == category),
                       key=lambda name: sha256((SPLIT_SEED + name).encode()).hexdigest())
        if len(names) < 12:
            raise ValueError("Each category needs at least 12 independent intent groups.")
        holdout = max(2, len(names) // 6)
        for i, name in enumerate(names):
            partitions[name] = "validation" if i < holdout else "test" if i < 2 * holdout else "train"
    splits = {name: [r for r in rows if partitions[r["group"]] == name]
              for name in ("train", "validation", "test")}
    negative_keys = set()
    if set(negatives) != {"validation", "test"}:
        raise ValueError("Negative controls need separate validation and test partitions.")
    for values in negatives.values():
        if not values:
            raise ValueError("Negative control partition cannot be empty.")
        for value in values:
            key = re.sub(r"[^a-z0-9]+", " ", normalize(value)).strip()
            if key in texts or key in negative_keys:
                raise ValueError("Negative controls overlap another partition.")
            negative_keys.add(key)
    # Semantic canonicalization avoids changing the model ID on Windows CRLF checkouts.
    canonical = json.dumps({"rows": rows, "negatives": negatives}, sort_keys=True,
                           ensure_ascii=False, separators=(",", ":"))
    return rows, splits, negatives, sha256(canonical.encode()).hexdigest()


def assessment(reason: str, *, model_version: str | None = None, scores=None,
               similarity=None, margin=None):
    messages = {
        "suggested": "Review this suggestion, then choose the category for your ticket.",
        "low_confidence": "The categories are too close or the score is too low. Choose a category yourself.",
        "out_of_scope": "This text does not match the training examples closely enough. Choose a category yourself.",
        "unsupported_language": "This demo is evaluated in English. Write the issue in English or choose a category yourself.",
        "insufficient_detail": "Describe the affected device or application and what is happening, using a few more words.",
        "unavailable": "AI suggestions are unavailable. You can still choose a category and submit your ticket.",
    }
    scores = scores or []
    return {
        "suggested_category": scores[0]["category"] if reason == "suggested" else None,
        "model_score": scores[0]["score"] if scores else None,
        "needs_review": reason != "suggested", "reason": reason,
        "message": messages[reason], "scores": scores,
        "margin": round(margin, 6) if margin is not None else None,
        "similarity": round(similarity, 6) if similarity is not None else None,
        "model_version": model_version, "scope": "synthetic_english_demo",
    }


class CategoryModel:
    def __init__(self, data_dir: Path = DATA_DIR):
        import numpy as np
        import scipy
        import sklearn
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import FeatureUnion, Pipeline
        from threadpoolctl import threadpool_limits

        rows, self.splits, negatives, self.dataset_hash = read_dataset(data_dir)
        self.version = ALGORITHM_VERSION + ":" + self.dataset_hash[:12]
        self.pipeline = Pipeline([
            ("features", FeatureUnion([
                ("words", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True,
                                        strip_accents="unicode", stop_words="english", max_features=12000)),
                ("characters", TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5),
                                             sublinear_tf=True, max_features=18000)),
            ])),
            ("classifier", LogisticRegression(C=4.0, max_iter=2000, random_state=27)),
        ])
        train = self.splits["train"]
        # IDF, vocabulary and coefficients are learned ONLY from the training rows.
        with threadpool_limits(limits=1):
            self.pipeline.fit([r["text"] for r in train], [r["category"] for r in train])
        self.word_vectorizer = dict(self.pipeline.named_steps["features"].transformer_list)["words"]
        self.training_vectors = self.word_vectorizer.transform([r["text"] for r in train])
        self.labels = list(self.pipeline.named_steps["classifier"].classes_)
        self.threshold = 1.01
        val_raw = [self.raw(r["text"]) for r in self.splits["validation"]]
        neg_raw = [self.raw(t) for t in negatives["validation"]]
        candidates = []
        for threshold in THRESHOLDS:
            accepted = [i for i, raw in enumerate(val_raw) if self.reason(raw, threshold) == "suggested"]
            correct = sum(val_raw[i]["scores"][0]["category"] == self.splits["validation"][i]["category"]
                          for i in accepted)
            negative_accepted = sum(self.reason(raw, threshold) == "suggested" for raw in neg_raw)
            precision = correct / len(accepted) if accepted else None
            candidates.append({"threshold": threshold, "accepted": len(accepted),
                               "precision": precision, "negative_accepted": negative_accepted})
        eligible = [c for c in candidates if c["accepted"] > 0 and c["precision"] >= 0.90
                    and c["negative_accepted"] == 0]
        if eligible:
            self.threshold = max(eligible, key=lambda c: (c["accepted"], -c["threshold"]))["threshold"]
        self.report = {
            "status": "ready", "model_version": self.version,
            "algorithm": "Word + character TF-IDF with Logistic Regression",
            "language": "English", "dataset_type": "Project-authored synthetic examples",
            "scope": "synthetic_english_demo", "dataset_sha256": self.dataset_hash,
            "examples": len(rows), "groups": len({r["group"] for r in rows}),
            "categories": self.labels,
            "split_counts": {s: len(r) for s, r in self.splits.items()},
            "split_group_counts": {s: len({r["group"] for r in rs}) for s, rs in self.splits.items()},
            "per_category_counts": dict(Counter(r["category"] for r in rows)),
            "split_method": "Fixed SHA-256 ordering of intent groups, stratified by category",
            "split_seed": SPLIT_SEED,
            "threshold": self.threshold, "minimum_margin": MIN_MARGIN,
            "minimum_similarity": MIN_SIMILARITY,
            "threshold_policy": "Highest validation coverage with >=90% accepted precision and zero accepted validation negative controls; otherwise abstain on all.",
            "validation_candidates": candidates,
            "validation": self.evaluate(self.splits["validation"]),
            "test": self.evaluate(self.splits["test"]),
            "negative_controls": {s: {"count": len(values), "accepted": sum(
                self.predict(t)["suggested_category"] is not None for t in values)} for s, values in negatives.items()},
            "majority_baseline_accuracy": max(Counter(r["category"] for r in self.splits["test"]).values()) / len(self.splits["test"]),
            "versions": {"python": platform.python_version(), "scikit_learn": sklearn.__version__,
                         "numpy": np.__version__, "scipy": scipy.__version__},
            "limitations": [
                "All examples and negative controls are synthetic; these metrics do not establish real-office accuracy.",
                "The test partition contains only 54 examples from 18 held-out intent groups.",
                "Scores are model probabilities, not calibrated estimates of correctness.",
                "English only; Bangla and Banglish performance has not been validated.",
                "A single category cannot represent every multi-issue ticket. A person must confirm the category.",
                "Negative controls are small and cannot guarantee detection of every unrelated request.",
                "No customer tickets are sent to an external AI service or automatically added to training.",
            ],
        }

    def raw(self, text: str):
        import numpy as np
        issue = input_issue(text)
        if issue:
            return {"issue": issue, "scores": [], "margin": None, "similarity": None, "known_terms": 0}
        vector = self.word_vectorizer.transform([text])
        probs = self.pipeline.predict_proba([text])[0]
        ranked = np.argsort(-probs, kind="stable")
        known_terms = len(set(self.word_vectorizer.build_analyzer()(text)) & self.word_vectorizer.vocabulary_.keys())
        return {
            "issue": None,
            "scores": [{"category": self.labels[i], "score": float(probs[i])} for i in ranked],
            "margin": float(probs[ranked[0]] - probs[ranked[1]]),
            "similarity": float((vector @ self.training_vectors.T).max()),
            "known_terms": known_terms,
        }

    @staticmethod
    def reason(raw, threshold):
        if raw["issue"]:
            return raw["issue"]
        if raw["known_terms"] < 2 or raw["similarity"] < MIN_SIMILARITY:
            return "out_of_scope"
        if raw["scores"][0]["score"] < threshold or raw["margin"] < MIN_MARGIN:
            return "low_confidence"
        return "suggested"

    def predict(self, text: str):
        raw = self.raw(text)
        return assessment(self.reason(raw, self.threshold), model_version=self.version,
                          scores=[{**s, "score": round(s["score"], 6)} for s in raw["scores"]],
                          similarity=raw["similarity"], margin=raw["margin"])

    def evaluate(self, rows):
        from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
        truth = [r["category"] for r in rows]
        raw = [self.raw(r["text"]) for r in rows]
        predicted = [r["scores"][0]["category"] for r in raw]
        accepted = [i for i, r in enumerate(raw) if self.reason(r, self.threshold) == "suggested"]
        return {
            "count": len(rows), "accuracy": float(accuracy_score(truth, predicted)),
            "macro_f1": float(f1_score(truth, predicted, average="macro", zero_division=0)),
            "confusion_matrix": confusion_matrix(truth, predicted, labels=self.labels).tolist(),
            "per_category": classification_report(truth, predicted, labels=self.labels,
                                                   output_dict=True, zero_division=0),
            "accepted": len(accepted), "coverage": len(accepted) / len(rows),
            "accepted_accuracy": sum(truth[i] == predicted[i] for i in accepted) / len(accepted) if accepted else None,
        }


def get_model() -> CategoryModel | None:
    global _model, _failed
    if _model is not None or _failed:
        return _model
    with _lock:
        if _model is None and not _failed:
            try:
                _model = CategoryModel()
            except Exception:
                # Keep manual ticket creation available if dependencies/data are damaged.
                _failed = True
                log.exception("Category model unavailable; manual ticket workflow remains available.")
    return _model


def classify(title: str, description: str):
    model = get_model()
    if model is None:
        return assessment("unavailable")
    try:
        return model.predict(title + "\n" + description)
    except Exception:
        log.exception("Category inference failed; no ticket text is logged.")
        return assessment("unavailable", model_version=model.version)
