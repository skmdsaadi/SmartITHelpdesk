import json
from pathlib import Path
from unittest.mock import patch

import pytest

from app import classifier


@pytest.fixture(scope="module")
def model():
    value = classifier.get_model()
    assert value is not None
    return value


def test_group_separation_and_measured_counts(model):
    groups = {s: {r["group"] for r in rows} for s, rows in model.splits.items()}
    assert not (groups["train"] & groups["validation"] or groups["train"] & groups["test"]
                or groups["validation"] & groups["test"])
    assert model.report["split_counts"] == {"train": 216, "validation": 54, "test": 54}
    test = model.report["test"]
    assert sum(sum(row) for row in test["confusion_matrix"]) == test["count"]
    assert sum(test["confusion_matrix"][i][i] for i in range(6)) / test["count"] == test["accuracy"]
    assert test["accepted"] / test["count"] == test["coverage"]


def test_test_text_cannot_change_fit_or_selected_threshold(model, tmp_path):
    import numpy as np
    rows = json.loads((classifier.DATA_DIR / "ticket_examples.json").read_text())
    test_ids = {r["id"] for r in model.splits["test"]}
    for row in rows:
        if row["id"] in test_ids:
            row["text"] += " heldoutnonceword neverfitthisword"
    (tmp_path / "ticket_examples.json").write_text(json.dumps(rows))
    (tmp_path / "out_of_scope.json").write_bytes((classifier.DATA_DIR / "out_of_scope.json").read_bytes())
    other = classifier.CategoryModel(tmp_path)
    assert "heldoutnonceword" not in other.word_vectorizer.vocabulary_
    assert other.word_vectorizer.vocabulary_ == model.word_vectorizer.vocabulary_
    assert np.allclose(other.pipeline.named_steps["classifier"].coef_, model.pipeline.named_steps["classifier"].coef_)
    assert other.threshold == model.threshold
    assert other.version != model.version


def test_suggestion_and_manual_review_guards(model):
    match = model.predict("My laptop cannot connect to the office Wi-Fi network and the wireless connection fails.")
    assert match["suggested_category"] == "Network"
    assert len(match["scores"]) == 6 and abs(sum(s["score"] for s in match["scores"]) - 1) < 0.00001
    assert model.predict("আমার কম্পিউটার চালু হচ্ছে না")["reason"] == "unsupported_language"
    assert model.predict("Help help help")["reason"] == "insufficient_detail"
    unrelated = model.predict("Please arrange an evening meal reservation for our wedding guests.")
    assert unrelated["suggested_category"] is None
    uncertain = {"issue": None, "known_terms": 10, "similarity": 0.8, "margin": 0.02,
                 "scores": [{"category": "Network", "score": 0.52}]}
    assert model.reason(uncertain, 0.5) == "low_confidence"


def test_duplicate_rows_rejected_and_crlf_stable(tmp_path):
    original = classifier.read_dataset()[3]
    for name in ["ticket_examples.json", "out_of_scope.json"]:
        text = (classifier.DATA_DIR / name).read_text()
        (tmp_path / name).write_bytes(text.replace("\n", "\r\n").encode())
    assert classifier.read_dataset(tmp_path)[3] == original
    path = tmp_path / "ticket_examples.json"
    rows = json.loads(path.read_text())
    rows.append(rows[0])
    path.write_text(json.dumps(rows))
    with pytest.raises(ValueError, match="Duplicate"):
        classifier.read_dataset(tmp_path)


def test_missing_model_has_explicit_fallback():
    with patch("app.classifier.get_model", return_value=None):
        result = classifier.classify("Network issue", "Office internet is unavailable today.")
    assert result["reason"] == "unavailable" and result["suggested_category"] is None
