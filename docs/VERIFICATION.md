# Phase 3 verification

This records the earlier category-classifier release. See [Phase 4 verification](PHASE4_VERIFICATION.md) for document upload and chat checks.

## Observed checks

| Check | Observed result |
| --- | --- |
| TypeScript check and Vite production build | Passed |
| Python dependency consistency (`pip check`) | Passed |
| Runtime dependency wheels for Python 3.11 / Windows x64 | Resolution dry run passed; not native execution |
| Automated model + database-backed API tests | **19 passed** |
| Exact duplicate rejection and Windows CRLF-independent dataset identity | Passed |
| Intent-group train/validation/test separation | Passed |
| Mutating held-out test text cannot affect learned coefficients or chosen threshold | Passed |
| AI endpoint authentication, input validation, CSRF and administrator report access | Passed |
| Manual category override, server-generated JSONB snapshot and owner isolation | Passed |
| Original snapshot survives later administrator category correction | Passed |
| Bangla text and unavailable-model fallback preserve ordinary ticket submission | Passed |
| Migration from revision 0001 with an existing ticket to revision 0002 | Passed in browser test setup; old ticket stayed readable |
| Browser suggestion, explicit Apply, manual override and stale-response cancellation | Passed |
| Ticket/reply/AI snapshot after page reload and API-process restart | Persisted correctly with database retained |
| Registration, login, comments, status updates, search and logout | Browser regression passed |
| AI form, ticket detail and evaluation at desktop 1440 px / mobile 390 px | No horizontal document overflow; screenshots inspected |
| Browser JavaScript errors in exercised flows | None |

The original account/ticket tests also cover password and session-token hashing, duplicate email normalization, role/owner injection rejection, employee isolation, stale edit conflicts, resolution/reopening, query validation, literal wildcard search, session expiry/inactive accounts and login throttling. Migration metadata matched the SQLAlchemy models.

## Environment and practical limits

Checks ran on Linux with Python 3.12, Node 24, the pinned numerical dependencies, Playwright 1.64.1 and headless Chromium 153. The target user machine is Windows/Python 3.11/Node 24. Windows wheels were resolved, including the added scientific packages; PowerShell commands and Windows execution were not run in this test environment. The Windows-only tzdata pin was already part of Phase 2; Linux pip marker evaluation omits it during the cross-platform dry run.

Database tests used PGlite 0.5.11 with pglite-socket 0.2.14, exposing a WebAssembly PostgreSQL build through the PostgreSQL wire protocol. Real application queries, Alembic migrations, JSONB, constraints and transactions executed against that engine. This is not a native PostgreSQL 17 service test or a load/concurrency test. PGlite is not an application dependency.

The API-process restart test retained the database process; it does not establish database-server disk durability. Public hosting, distributed rate limits and production performance are not verified. The app is still a local development release.

One Starlette TestClient/httpx deprecation warning was emitted. It did not fail tests and is unrelated to normal browser/API runtime.

Screenshot accounts (`Demo Employee`, `Demo IT Admin`) and tickets are seeded test data. The three captures in [the README](../README.md#demo-screenshots) were inspected for desktop/mobile layout and contain only demo data and synthetic evaluation results. No operational company data or pre-provisioned production account is bundled.

## Reproduce the automated tests

From the backend folder:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests/test_classifier.py -q
```

For all 19 tests, supply `TEST_DATABASE_URL` for a disposable PostgreSQL database and a role allowed to create schemas. The fixture creates a random schema, applies migrations there, and drops only that schema at completion. Without this setting, the database-backed tests skip; a skip is not a pass.

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://TEST_USER:TEST_PASSWORD@127.0.0.1:5432/TEST_DATABASE"
.\.venv\Scripts\python.exe -m pytest -q
```

Replace placeholders locally and never commit credentials. Model evaluation can be reproduced separately with `python -m app.train_classifier`; it does not require a database.

## Model evidence and remaining acceptance

Measured synthetic test accuracy is 50/54 (92.59%), macro-F1 0.9255 and suggestion coverage 36/54. All 36 accepted positive-class examples were correct, but one of twelve unrelated test controls was falsely accepted. See MODEL_CARD.md and docs/evaluation for all counts and limitations. These are not measurements of real-office accuracy.

On the actual Windows computer, follow PHASE3_SETUP.md, verify an earlier ticket remains readable, submit an English ticket using or overriding its suggestion, refresh its saved assessment, and inspect AI insights as administrator.
