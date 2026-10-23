# Phase 5 deployment verification

Verified on 23 October 2026, version 0.5.0. **This records pre-deployment checks. No live Render/Neon URL has yet been verified.**

## Automated checks

**55 tests passed**, with no skipped tests in this run. This includes the 40 Phase 4 tests plus 15 deployment cases, counting parametrized origin cases separately.

- Production origins accept the exact Render URL and an explicitly configured custom HTTPS domain; empty, HTTP, wildcard, path-bearing and credential-bearing origins fail validation.
- Production requires secure cookies and PostgreSQL TLS.
- The built UI and assets are served; unknown API routes, missing assets, environment-file paths and traversal attempts return 404.
- `/healthz` performs no database query or classifier initialization.
- HTTPS login sets Secure, HttpOnly, SameSite=Lax and `/api` cookie flags, authenticates subsequent requests, and rejects a different origin.
- Blank-database startup migrates through revision 0003 and creates the first admin. Later starts need no bootstrap values and do not reset its password or duplicate the account.
- Missing/invalid bootstrap values roll back the initial migrations; an existing employee email is not promoted or overwritten.
- A failed preparation step cannot start Uvicorn.
- Earlier ticket, classifier, source visibility, chat privacy, idempotency and migration/model alignment checks still pass.

One inherited warning remains: Starlette TestClient deprecates its httpx integration. Tests use the existing pinned development dependencies; this warning did not cause failures.

`pip check`, Python compilation, TypeScript checking, the Vite production build and `git diff --check` passed. Local YAML parsing confirms one Free Docker service, string environment values, automatic deploys off and unpopulated secret fields. Render's authenticated Blueprint validator was not run.

## Browser checks with production settings

Chromium loaded the compiled React bundle from FastAPI, with no Vite server. A local HTTPS reverse proxy and PostgreSQL TLS proxy exercised `APP_ENV=production`, database TLS validation, secure cookies and production response headers.

Passed:

1. Empty database → startup migration → administrator provisioning → HTTPS sign-in.
2. Readiness returns database ready and AI ready_demo; Swagger, secret paths and unknown routes return 404.
3. Administrator upload of the included guide, a Wi-Fi question, exact source citation and highlighted source link.
4. Refreshing a hash deep link works from the production bundle.
5. Restarting the application with all bootstrap variables removed retains the administrator session and uploaded source.
6. Mobile view at 390 × 844 has no horizontal overflow. No JavaScript exceptions or CSP violations were observed.

The mobile source page was visually inspected. Test captures contain illustrative accounts/content and were kept as temporary QA artifacts, not added to the repository.

## Environment and limits

- Python 3.12 and the repository's pinned packages, on Linux.
- PGlite 0.5.11 / socket adapter 0.2.14 provided a disposable PostgreSQL-compatible database. Startup tests explicitly select their random schemas because this adapter does not honor PostgreSQL startup `options` in the same way as a native server.
- These checks do not establish native PostgreSQL 17 concurrency, Neon network behavior, Render cold-start time, memory usage at the 512 MB limit, or sustained load capacity.
- Docker is unavailable in the verification environment. The constituent frontend build and Python startup were executed, but the complete Docker image still needs to build successfully on Render.
- Local TLS proxies use a disposable test certificate; the browser test accepts that certificate. This does not test Render's public TLS certificate issuance.
- No independent real-ticket or retrieval-quality evaluation was added, and the classifier metrics are unchanged from Phase 3.

Follow [the deployment guide](DEPLOYMENT.md), record the actual live URL/deployed commit, and complete its live acceptance checklist before marking the deployment deliverable complete.
