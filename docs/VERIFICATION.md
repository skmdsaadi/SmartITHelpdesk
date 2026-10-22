# Phase 2 verification

## Observed checks

| Check | Result |
| --- | --- |
| TypeScript and Vite production build | Passed |
| Python dependency consistency | Passed |
| Python 3.11 / Windows x64 binary dependency resolution | Passed dry run |
| Database-backed integration tests | 10 passed |
| Registration and session cookies through the Vite proxy | Passed in browser |
| Employee ticket creation and reply | Passed in browser |
| Administrator login, metadata update and reply | Passed in browser |
| Page reload and API process restart with the database retained | Ticket and reply remained accessible |
| Ticket search and clearing filters | Passed in browser |
| Logout | Returned to sign-in screen |
| Desktop 1440 px and mobile 390 px layout | No horizontal document overflow |
| Browser JavaScript errors in the tested workflow | None |
| Update helper: backup, exact source copy and environment/secret/Git preservation | Passed |
| Update helper: wrong-project and corrupt-package rejection | Passed |

Integration tests cover password hashing and token storage, case-insensitive duplicate email handling, public role/owner injection rejection, employee isolation, unauthorized reads/replies/updates, audit events, resolution/reopening, stale revisions, query validation, literal wildcard search, pagination, CSRF guards, expired/inactive sessions, login throttling, separate-client persistence and model/migration alignment.

## Environment and limits

The checks ran on Linux, Python 3.12 and Node 24. The user's target is Windows, Python 3.11 and Node 24. Windows binary package resolution was checked; native Windows installation and PowerShell execution were not run here.

Integration and browser checks used PGlite 0.5.11 with pglite-socket 0.2.14, which exposes a WebAssembly build of PostgreSQL through its wire protocol. Application queries, migrations, constraints and transactions ran against that engine. This is not a native PostgreSQL 17 service test or a concurrency/load test. The delivered application requires PostgreSQL and does not include PGlite.

The local PostgreSQL installer, creation of a native database/role and the local setup prompt sequence still need to run on the user's computer. The administrator creation command was exercised against the test database. Database-server restart/disk durability and public hosting were not tested.

Playwright 1.64.1 and headless Chromium 153 exercised the frontend. Screenshots were inspected internally for layout; synthetic test accounts/data are not included in the deliverable.

Starlette emitted one TestClient/httpx deprecation warning. It did not fail the integration tests and does not affect the normal browser/API runtime.

## Running the integration tests

Use a disposable PostgreSQL database and a role permitted to create schemas. Set TEST_DATABASE_URL to its connection URL. The fixture creates a random schema, applies the migration there and drops only that schema afterward. Tests skip when this variable is absent; skipped tests are not a pass.

From backend:

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:TEST_DATABASE_URL = "postgresql+psycopg://TEST_USER:TEST_PASSWORD@127.0.0.1:5432/TEST_DATABASE"
.\.venv\Scripts\python.exe -m pytest -q
~~~

Replace the placeholders locally. Never commit credentials or share the complete connection string.

## User acceptance

On the actual Windows computer, check setup, administrator login, an employee's isolated ticket list, replies/status history and persistence after stopping/restarting the API. AI accuracy and deployment availability have not been measured in this phase.
