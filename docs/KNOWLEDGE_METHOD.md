# Knowledge search methodology — Phase 4

## Problem and approach

Repeated IT questions often have an answer in an approved guide, but users have difficulty locating it. This module provides a searchable library and a private conversation interface. It returns relevant, verbatim passages with document and page/section references. It is an extractive retrieval system, not generative RAG: there is no LLM, generated diagnosis, translation or paid API dependency.

## Ingestion

Only administrators can upload. The browser sends the selected file's raw bytes; title and filename are query parameters. The server validates the filename/extension, actual bytes and extracted text. It does not trust the browser's MIME type. Original filenames are reduced to a basename and are never used as filesystem paths.

TXT accepts UTF-8 with or without a byte-order mark, including Windows line endings. PDF uses pinned pypdf 6.21.2. Encrypted, malformed, oversized or textless files are rejected. Image-only/scanned PDFs require OCR outside this application. A mixed PDF reports pages without extractable text; those pages are excluded. Tables and complex visual reading order may be lost, so administrators must review the extracted passages.

PDF extraction runs in a child interpreter. A 15-second timeout terminates it; on POSIX a 256 MiB address-space limit and 12-second CPU limit additionally apply. Decoded Flate data and page content streams are limited to 4 MiB. Windows has file/page/text/timeout limits but does not have the POSIX memory cap. Production PDF ingestion should use an OS/container-isolated worker with a hard memory quota on every supported platform; this child process is not a complete security sandbox.

Whitespace is normalized and paragraphs become passages. Long paragraphs split at a nearby word boundary, at most 1,000 characters, with 120 characters of overlap. Chunks retain their PDF page number; TXT uses a passage number without inventing a page. Chunk text is immutable. To revise content, upload a reviewed replacement and deactivate/remove the earlier document.

## Ranking and response

1. Read only active source chunks under a transaction-level shared corpus lock.
2. Build word TF-IDF with 1–2-grams and up to 12,000 features, and character TF-IDF with `char_wb` 3–5-grams and up to 20,000 features. Both use sublinear term frequency. Normalize common Wi-Fi spellings and remove English stop words plus a small documented generic-help word list for the word features.
3. Score a question using `0.8 × word cosine similarity + 0.2 × character cosine similarity`.
4. Require a score of at least 0.18, at least two shared non-stop-word terms and at least 55% of the highest candidate score. Suppress near-duplicate passages and return at most three.
5. Save question, method `tfidf-passages-v1`, corpus revision and source IDs/ranks/scores. Render a fixed explanatory message and exact current source text.

These thresholds are hand-set heuristics. They are not calibrated probabilities or independently validated decision thresholds. Similar words do not establish that a passage answers a question correctly, so the UI labels results as matching passages. A no-match result directs users to rephrase or create a ticket. Empty libraries explain that an administrator needs to add documents. Retrieval dependency failures return 503 without saving a partial conversation/turn and do not block ticket submission.

An in-memory index is cached by a hash of chunk IDs and text; it is rebuilt when the source corpus changes. Fitting IDF on the searchable source corpus is standard retrieval indexing, not classifier training on question labels. User questions are not added to the source corpus. Each question is searched independently; chat history does not resolve pronouns, translate or supply conversational memory.

## Scope and evaluation

The included `docs/examples/IT_Helpdesk_Demo_Guide.txt` was authored for this capstone and contains no real company policy or employee data. Seven illustrative English questions retrieve the expected top passage, and four unrelated/underspecified questions return no match in the automated acceptance checks. These questions and passages were designed together; these checks are not a held-out benchmark and do not establish real-world retrieval accuracy.

Unicode text is preserved, but retrieval quality for Bangla/Banglish or cross-language questions is not validated. Character matching cannot substitute for multilingual embeddings or translation. An independent evaluation should label representative real questions and expected passages, separately measure retrieval recall/ranking and false-positive/no-answer behavior, and report results by language and document type.

## Permissions and retention

- Active documents are available to all signed-in users. This phase has no department-specific or per-document access lists.
- Administrators upload, activate/deactivate and remove documents. Version checks reject stale management actions.
- Every user, including an administrator, can list/read/delete only their own conversations. Hidden IDs return the same 404 as unknown IDs.
- Source links enforce the current document permissions. Deactivation hides a source from search and subsequent chat-history reads; reactivation restores its retained citation links.
- Removal deletes extracted chunks and their citation links. Earlier answers show that their sources are no longer available. Questions and fixed response metadata remain until the conversation is deleted. Re-upload creates distinct source IDs and does not revive deleted citations.
- Only metadata and extracted text are stored; original PDFs/TXT bytes are discarded after processing. No file is sent to an external AI service. Application output displays extracted text as escaped text, not executable markup.
- Access already granted cannot retract a screenshot or downloaded text. Production backups have their own retention policy, which is not implemented here.

## Operational limits

| Item | Limit |
| --- | --- |
| HTTP request/upload body | 2 MiB, measured from actual received bytes |
| PDF length | 50 pages |
| Extracted text per document | 200,000 characters |
| Chunks per document | 300 |
| Stored documents, including inactive | 30 |
| Total stored chunks, including inactive | 500 |
| Question | 5–2,000 trimmed characters |
| Conversations per user | 100 |
| Questions per conversation | 50 |
| Upload requests | 6 per user per minute, process-local |
| Question requests | 20 per user per minute, process-local; idempotent replays are exempt |
| Concurrent PDF extraction | One per API process |

Quotas are enforced transactionally. Production still needs shared rate limits, controlled account provisioning, backup/restore, monitoring, representative load tests and a resource-constrained extraction worker. The current limits deliberately target a small capstone corpus.

## Primary references

- pypdf extraction, reading order and OCR limitations: <https://pypdf.readthedocs.io/en/stable/user/extract-text.html>
- Starlette request-body limits: <https://www.starlette.io/middleware/#requestbodylimitmiddleware>
- scikit-learn text feature extraction: <https://scikit-learn.org/stable/modules/feature_extraction.html#text-feature-extraction>
