# Phase 4 verification

## Observed results

| Check | Result |
| --- | --- |
| Automated account/ticket/classifier/document/retrieval/API tests | **40 passed** |
| SQLAlchemy models compared with migrated database schema | Matched |
| TypeScript checking and Vite production build | Passed |
| Python dependency consistency | `pip check` passed |
| Added pypdf dependency for Windows x64 / Python 3.11 | Wheel-resolution dry run passed; not native execution |
| UTF-8/BOM/Windows line endings and page-aware chunking | Passed |
| Real text PDF extraction and mixed blank-page warnings | Passed |
| Malformed, encrypted, textless, excessive-page, oversized and timed-out PDF cases | Rejected with actionable responses |
| Actual request size without Content-Length | Oversized streamed upload returned 413 |
| Upload/admin authorization and CSRF checks | Passed |
| Private conversation isolation, including no administrator override | Passed |
| Exact text/source citation equality | Passed |
| Duplicate question request and mismatched idempotency payload | Same turn returned / conflicting payload rejected |
| Document deactivation, reactivation and deletion | Search, source routes and history obeyed current visibility |
| Re-upload after deletion | Did not revive deleted citation links |
| Capacity/turn/thread quota failures | No partial document or conversation persisted |
| Retrieval failure | 503 with transaction rollback; ticket submission remained functional |

The 40 tests comprise 19 existing regression tests, 11 document-extraction cases, 3 retrieval tests and 7 document/chat API tests. The inherited regression suite includes session hashing, employee ticket isolation, stale ticket edits, category snapshots and classifier split integrity. One existing Starlette TestClient/httpx deprecation warning remains; it did not fail tests.

## Browser verification

The production-code UI was exercised through the Vite development proxy with a running FastAPI process and PostgreSQL-wire database:

- Upgrade from revision 0002 to 0003 with an existing administrator and ticket.
- Administrator login, invalid-PDF error, successful TXT and real PDF upload, and source text inspection.
- Employee registration, browsing without upload controls, a matching Wi-Fi question and source deep link.
- Page reload and a full API-process restart preserving source text, conversation history and citation IDs.
- A deliberately lost response after the server saved a question, followed by a UI retry that reused its request UUID and produced no duplicate turn.
- Unrelated-question fallback, deactivate/reactivate effects on earlier quotations and employee source access.
- Uploaded markup displayed literally without execution, document removal and owner conversation deletion.
- Desktop 1440×1000 and mobile 390×844 library, chat and source layouts, with no horizontal document overflow. Captures were visually inspected locally.
- No browser JavaScript exceptions in the exercised workflows.

Browser automation used isolated Chromium contexts for administrator and employee sessions. The first run exposed an upload-input accessible-label issue, which was corrected; subsequent checks passed. No phase-4 screenshot is published in this change; the README's earlier captures are explicitly identified as Phase 3.

## Environment and limits of the evidence

Tests ran on Linux, Python 3.12, Node 24, Playwright 1.64.1 and Chromium 153, using the pinned application dependencies. PGlite 0.5.11 with pglite-socket 0.2.14 supplied a WebAssembly PostgreSQL engine over the PostgreSQL wire protocol. Queries, migrations, foreign keys, JSONB and transactions were exercised. PGlite is only a verification tool, not a runtime dependency.

This is not a native Windows/PostgreSQL 17, load/concurrency, operating-system sandbox, production deployment or database-server durability test. The restart check retained the database process while restarting the API. The user reported successful Phase 3 acceptance on their Windows installation; Phase 4 still requires the local acceptance steps below. The added PDF wheel was resolved for Python 3.11/Windows, but PowerShell and the Windows PDF process were not executed here.

The retrieval acceptance examples are illustrative and were designed with the demo guide. Seven positive questions and four unrelated/underspecified questions behaved as expected. These are functional checks, not independent accuracy measurements. The classifier's frozen Phase 3 evaluation is unchanged. See [knowledge methodology](KNOWLEDGE_METHOD.md) and [classifier model card](MODEL_CARD.md) for distinct scopes and limitations.

## Reproduce tests

From `D:\Projects\SmartITHelpdesk\backend`, database-free tests:

```powershell
& {
    $ErrorActionPreference = "Stop"
    Set-Location "D:\Projects\SmartITHelpdesk\backend"
    .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw "Test installation failed." }
    .\.venv\Scripts\python.exe -m pytest tests/test_classifier.py tests/test_documents.py tests/test_retrieval.py -q
}
```

For the full suite, set `TEST_DATABASE_URL` to a disposable PostgreSQL database and run `python -m pytest -q` using the same virtual environment. The fixture creates a randomly named schema, applies migrations and removes only that test schema at completion. Without the explicit test URL, database tests skip; skipped tests are not passing evidence. Do not use or commit production credentials.

The Windows acceptance workflow is in [PHASE4_SETUP.md](PHASE4_SETUP.md): preserve an earlier ticket, upload the included TXT, check an actual text PDF, ask a question, follow its source, refresh history and test deactivation.
