# Category model card — Phase 3

## Intended use

Assist a signed-in employee or administrator in choosing an IT ticket category. Every category remains under human control. The model does not prescribe repairs, classify urgency, grant privileges, resolve tickets or generate conversational answers.

This release is an English synthetic-data demonstration. Real-office performance, Bangla/Banglish support and multi-issue routing have not been established.

## Dataset and fit

The [dataset provenance](../backend/data/README.md) describes 324 project-generated examples and 108 intent groups. Each category has 54 rows. No operational ticket was used. Independent human label review remains pending.

A deterministic grouped, category-stratified split produces 216 training, 54 validation and 54 held-out test examples. TF-IDF vocabulary/IDF and Logistic Regression coefficients use only training data. The train set is not enlarged with validation or test examples for serving.

The pipeline combines:

- Word TF-IDF: unigrams/bigrams, sublinear term frequency, Unicode accent normalization, English stop words, maximum 12,000 features.
- Character TF-IDF: within-word 3–5 character n-grams, sublinear term frequency, maximum 18,000 features.
- Logistic Regression: `C=4`, `max_iter=2000`, `random_state=27`, default multiclass handling and solver in the pinned scikit-learn version.

Parameters and candidate threshold grid were fixed before the first held-out evaluation. No model tuning was performed to remove observed held-out errors.

## Abstention

A prediction is withheld if the text has non-Latin alphabetic characters, too few distinct alphabetic words, fewer than two recognized TF-IDF features, insufficient similarity to the training examples, a small top-two score gap, or a low top-class score. Script detection is not general language identification; Latin-script Banglish may still receive a suggestion without validated performance.

Fixed minimums are a 0.10 top-two score gap and 0.12 maximum cosine similarity to a training example. Candidate score thresholds range from 0.35 to 0.95, plus an all-abstain option. Validation chooses maximum suggestion coverage subject to at least 90% accuracy among accepted validation examples and zero accepted validation negative controls. The selected threshold is **0.50**. If no threshold qualifies, the system abstains on all requests.

The small validation set does not make those constraints production guarantees. `model_score` is a classifier probability, not a calibrated probability that a decision is correct. The interface labels it as a model score.

## Observed evaluation

| Metric | Validation | Held-out test |
| --- | ---: | ---: |
| Examples | 54 | 54 |
| Raw correct predictions | 52 | 50 |
| Raw accuracy | 96.30% | 92.59% |
| Macro-F1 | 0.9616 | 0.9255 |
| Suggestions accepted | 45 | 36 |
| Suggestion coverage | 83.33% | 66.67% |
| Correct among accepted suggestions | 45 / 45 | 36 / 36 |
| Unrelated negative controls accepted | 0 / 12 | 1 / 12 |

The majority-class baseline is 16.67% because the positive-class partitions are balanced. Accepted accuracy excludes abstentions and negative controls; do not confuse it with overall accuracy. The 36/36 result is a small synthetic subset, not a promise of perfect reliability.

The four raw held-out errors were one DNS request predicted as Software, one authenticator-phone request predicted as Email, and two Windows/OS issues predicted as Hardware. The abstention policy withheld all four, but it also withheld 14 correct positive-class predictions. One unrelated test request passed the suggestion policy, so out-of-domain rejection is incomplete.

Machine-readable [report](evaluation/report.json), [split membership](evaluation/split_manifest.json), [all test predictions](evaluation/test_predictions.csv) and [confusion matrix](evaluation/confusion_matrix.csv) preserve the evidence. Reproduction instructions are in the README. Numeric versions are recorded in the report. Native Windows execution was not performed in the development test environment; its dependency wheel resolution was checked.

## Serving and privacy

The backend fits and caches one pipeline per process. Training and scoring run locally; no external LLM or AI API receives ticket text. There is no executable model deserialization. A protected administrator endpoint serves the report; signed-in users may classify their own draft text. Draft classification is not stored on its own.

Creating a ticket recomputes its assessment server-side and saves the result, model version, timestamp and selected category in PostgreSQL JSONB. Clients cannot supply an assessment. Later administrator changes update the ticket category and activity history while keeping this creation-time snapshot unchanged. Old tickets have a null snapshot. Missing/corrupt model dependencies or data produce a manual-selection fallback.

## Next evidence needed

Review the synthetic labels, acquire an approved anonymized real-ticket set, evaluate on independent grouped/time-separated data, quantify ambiguity and language coverage, and assess calibration before using scores as probabilities of correctness. Do not repeatedly tune against the held-out test set reported here; it is now observed development evidence.

## Technical references

- scikit-learn, [Common pitfalls and data leakage](https://scikit-learn.org/stable/common_pitfalls.html)
- scikit-learn, [Pipelines and composite estimators](https://scikit-learn.org/stable/modules/compose.html)
- scikit-learn, [Text feature extraction](https://scikit-learn.org/stable/modules/feature_extraction.html)
- scikit-learn, [Model persistence and security](https://scikit-learn.org/stable/model_persistence.html)

These are methodology references, not sources of the synthetic examples.
