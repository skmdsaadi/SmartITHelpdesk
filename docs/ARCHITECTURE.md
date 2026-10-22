# Phase 2 architecture

React calls /api/v1 on the frontend origin. The Vite proxy forwards requests to FastAPI on 127.0.0.1:8000. FastAPI reads/writes PostgreSQL through SQLAlchemy and Psycopg. Same-origin requests carry the HttpOnly session cookie. Browser storage contains no session token.

## Tables

| Table | Purpose |
| --- | --- |
| users | Name, normalized unique email, Argon2 hash, role, active flag |
| auth_sessions | Hash of an opaque token, user FK, expiry |
| tickets | Owner, title, description, category, priority, status, dates, version |
| ticket_comments | Ticket, author, reply, creation date |
| ticket_events | Ticket, author, metadata change, creation date |
| alembic_version | Migration revision |

Check constraints validate roles/categories/priorities/statuses; foreign keys preserve references. Ownership is enforced in queries before reading a ticket or writing a reply.

Metadata updates lock the ticket row, verify the submitted version and append an event in one transaction. Stale versions receive HTTP 409. Reopening clears the resolved timestamp.

## API

All routes start with /api/v1.

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
- Login/registration have a process-local attempt limit.
- Database errors returned to clients do not reveal connection settings.
- React renders ticket/reply content as text, not as HTML.

## Deployment limits

For HTTPS hosting, enable COOKIE_SECURE and configure the exact allowed origin. Add a shared edge/Redis rate limiter before public multi-worker use. Decide registration policy. Email verification, password recovery and an admin user-management screen are not implemented.

There is no classifier, LLM call, file upload or realtime push channel yet. No local database password or test user is bundled.

## Technical references

- <https://docs.sqlalchemy.org/en/20/orm/quickstart.html>
- <https://alembic.sqlalchemy.org/en/latest/tutorial.html>
- <https://www.psycopg.org/psycopg3/docs/basic/install.html>
- <https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/>
- <https://tailwindcss.com/docs/installation/using-vite>

The FastAPI tutorial is referenced for password hashing; this application uses opaque sessions rather than JWT.
