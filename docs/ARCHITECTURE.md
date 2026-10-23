# Architecture — Phase 5

React calls /api/v1 on the frontend origin. During development the Vite proxy forwards requests to FastAPI on 127.0.0.1:8000. For hosting, FastAPI serves the built React index and assets on that same origin; hash routes need no catch-all that could hide API 404 errors. FastAPI reads/writes PostgreSQL through SQLAlchemy and Psycopg. Same-origin requests carry the HttpOnly session cookie. Browser storage contains no session token.

## Tables

| Table | Purpose |
| --- | --- |
| users | Name, normalized unique email, Argon2 hash, role, active flag |
| auth_sessions | Hash of an opaque token, user FK, expiry |
| tickets | Owner, title, description, category, priority, status, dates, version, nullable AI assessment JSONB |
| ticket_comments | Ticket, author, reply, creation date |
| ticket_events | Ticket, author, metadata change, creation date |
| knowledge_state | Singleton corpus revision and transaction lock |
| knowledge_documents | Title, filename, raw-file hash, extracted-text counts, active flag and version |
| knowledge_chunks | Immutable extracted passages with document FK and PDF page number |
| chat_threads | Owner, title and timestamps |
| chat_turns | Question, idempotency request UUID, retrieval method/revision and outcome |
| chat_citations | Turn/chunk FK pair, rank and relevance score; text is read from the source |
| alembic_version | Migration revision |

Check constraints validate roles/categories/priorities/statuses; foreign keys preserve references. Ownership is enforced in queries before reading a ticket or writing a reply.

Metadata updates lock the ticket row, verify the submitted version and append an event in one transaction. Stale versions receive HTTP 409. Reopening clears the resolved timestamp.

## API

The following API routes start with /api/v1. The separate `/healthz` endpoint performs no database or model work and is used for Render liveness probes.

| Method | Path | Access |
| --- | --- | --- |
| GET | /health | Public readiness |
| POST | /auth/register | Public when enabled; employee role only |
| POST | /auth/login | Public; issues session |
| GET | /auth/me | Signed-in user |
| POST | /auth/logout | Revokes the presented session |
| GET | /dashboard | Data within the user's visibility |
| GET | /tickets | Authorized search/filters/pagination |
| POST | /tickets | Signed-in user; server sets owner and Open status |
| GET | /tickets/{id} | Owner or administrator |
| PATCH | /tickets/{id} | Administrator; category/priority/status/version required |
| POST | /tickets/{id}/comments | Owner or administrator |
| POST | /ai/classify | Signed-in user; title and description only |
| GET | /ai/model | Administrator; synthetic evaluation report |
| GET | /knowledge/documents | Signed-in user; active documents, title search and pagination |
| POST | /knowledge/documents | Administrator; raw file bytes, title/filename query parameters |
| GET | /knowledge/documents/{id} | Signed-in user for active sources; admin may inspect inactive sources |
| PATCH | /knowledge/documents/{id} | Administrator; is_active and current version |
| DELETE | /knowledge/documents/{id} | Administrator; current version query parameter |
| GET | /chat/threads | Current user's conversations only, paginated |
| GET, DELETE | /chat/threads/{id} | Owner only; no administrator override |
| POST | /chat/ask | Signed-in user; question, optional owned thread_id and request UUID |

Hidden and unknown ticket IDs both return 404. Authentication errors return 401, denied administrator operations 403 and invalid inputs 422.

## Authentication

- Argon2 hashes through pwdlib; no plaintext password storage.
- Sessions use 32 random bytes; only SHA-256 token hashes are persisted.
- Expiry defaults to 12 hours; active-user state is checked per request.
- Login rotates the current session; logout revokes its stored token.
- HttpOnly + SameSite=Lax cookies scoped to /api.
- Writes require X-Helpdesk-Request: 1 and an exact allowed Origin if supplied.
- Cross-site browser writes are rejected; there is no permissive CORS policy.
- Input models forbid extra fields, role changes and owner overrides.
- Login/registration and authenticated upload/question operations have process-local limits.
- A 2 MiB ASGI body limit counts actual received bytes, including requests without Content-Length.
- Database errors returned to clients do not reveal connection settings.
- React renders tickets, replies, uploaded text and citations as escaped text.

## Deployment limits

The Render Blueprint enables HTTPS-only cookies, derives the exact allowed origin from RENDER_EXTERNAL_URL, runs one worker, and enables employee registration for evaluation. Production adds CSP, HSTS and framing protections and disables interactive API docs. Memory limits are process-local and reset on restart; add a shared limiter before scaling. Forwarded client IPs are not trusted, so authentication limits can be shared by users behind a proxy. The app is a bounded capstone demonstration. Email verification, password recovery and an admin user-management screen are not implemented.

The classifier runs locally from bundled synthetic English examples. Knowledge search runs locally over administrator uploads. There is no LLM call, OCR, external embedding service or realtime push channel. No local database password or pre-provisioned user is bundled. Test helpers create temporary example accounts only when tests run.

## Technical references

- <https://docs.sqlalchemy.org/en/20/orm/quickstart.html>
- <https://alembic.sqlalchemy.org/en/latest/tutorial.html>
- <https://www.psycopg.org/psycopg3/docs/basic/install.html>
- <https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/>
- <https://tailwindcss.com/docs/installation/using-vite>

The FastAPI tutorial is referenced for password hashing; this application uses opaque sessions rather than JWT.

## AI data flow

The create form sends its title and description to `/ai/classify`. The response contains ranked model scores, an optional suggested category and an explicit abstention reason. The form does not change the selected category until the user clicks Use. Editing text aborts the pending request and discards stale results.

`classifier.py` builds a pipeline lazily once per process under a lock. The model only fits training rows; validation selects a score threshold, and test rows generate the report. No binary model file is loaded. A failed model initialization is cached until backend restart, allowing the ordinary ticket workflow to continue.

POST `/tickets` computes its own assessment, irrespective of the browser preview, then persists the ticket and assessment in one transaction. The JSONB snapshot contains model version, ranked scores, reason, timestamp and category selected at submission. PATCH category/status/priority does not rewrite that snapshot. Migration 0002 adds a nullable field, preserving Phase 2 records.

This deployment is a bounded single-process demo. The classifier has no external API cost. The startup command applies migrations and the first admin in one advisory-locked transaction, stops on failure, then serves the app as an unprivileged container user. It never resets an existing account. Database records persist independently of the application filesystem. See [deployment setup and operational limits](DEPLOYMENT.md). See MODEL_CARD.md for classifier limitations.

## Knowledge and conversation data flow

An authenticated administrator uploads raw bytes to the document endpoint. The endpoint reads a bounded stream after its authorization dependencies run. TXT is decoded as UTF-8; PDF runs in a separate Python interpreter with a 15-second timeout, page/text limits and POSIX resource caps. Original bytes are discarded after extraction. Extracted passages, metadata and warnings are committed together in PostgreSQL.

Document changes take an exclusive lock on the singleton knowledge-state row before checking corpus quotas or changing active state. Retrieval takes a shared lock until its turn and citations are committed. A content-derived cache key prevents use of a stale TF-IDF index after any change, including database replacement. The bounded in-memory index is rebuilt after an API restart without loss of stored source text.

Question submission takes a per-user NO KEY UPDATE row lock, checks its idempotency UUID and verifies thread ownership. The user lock also serializes conversation deletion and enforces conversation quotas. The retrieval result, turn and citation links commit atomically. Replaying the same UUID/question returns the existing turn; mismatched payloads receive 409. No automatic conversational context is added to the query.

Chat responses contain fixed explanatory text and current, active source passages. They do not store a second copy of quoted text in chat records. Deactivation hides quotations on subsequent reads; deletion cascades through source chunks and their citation links. Questions remain in the owner's conversation until the owner deletes that conversation. Previously displayed or downloaded text cannot be retracted from a user's device.

See [knowledge methodology](KNOWLEDGE_METHOD.md) for exact limits and retention behavior.
