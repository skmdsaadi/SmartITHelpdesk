# Smart IT Helpdesk

A capstone project for handling workplace IT support requests.

**Release: Phase 2 / 0.2.0.** Accounts, PostgreSQL storage and ticket management are implemented. The AI classifier, knowledge upload, retrieval chat, public deployment and final evaluation are subsequent phases.

## Problem

Employees report IT problems through scattered calls and messages. The IT team loses context, repeats questions, and has difficulty tracking progress. Smart IT Helpdesk gives each issue an owner, a conversation and a recorded resolution workflow.

## Current features

- Employee registration; local administrator provisioning; login/logout.
- Argon2 password hashes and revocable PostgreSQL-backed sessions.
- Employees create tickets and access only their own tickets.
- Administrators view all tickets and update category, priority and status.
- Categories: Email, Network, Hardware, Software, Printer, Access.
- Priorities: Low, Normal, High. Statuses: Open, In Progress, Resolved.
- Replies and a chronological history of ticket metadata changes.
- Dashboard counts, search, filters and pagination backed by database queries.
- Stale administrator edits are rejected with HTTP 409.
- Responsive desktop/mobile interface; dates shown in Asia/Dhaka.
- No seeded users, default passwords, fabricated counts or simulated AI answers.

## Stack

| Part | Technology |
| --- | --- |
| Frontend | React, Vite, TypeScript |
| Styling | Tailwind CSS and responsive CSS |
| Backend | Python 3.11+, FastAPI, Pydantic |
| Storage | PostgreSQL, SQLAlchemy 2.0, Psycopg 3 |
| Migrations | Alembic |
| Authentication | pwdlib / Argon2, opaque server-side sessions |
| Planned AI | TF-IDF + Logistic Regression; source-linked document retrieval |

Node 22.12+ is required. Exact resolved versions are in the dependency lockfiles.

## Windows setup

Follow [docs/WINDOWS_SETUP.md](docs/WINDOWS_SETUP.md). All terminal commands use PowerShell. No environment activation, BAT file or machine-wide script-policy change is needed.

For Phase 1, use apply_update.py from the update bundle. It validates the package, backs up affected source files and preserves environments, secrets and Git history. Its backup is a **source-code backup**, not a PostgreSQL backup.

For a fresh checkout:

~~~powershell
Set-Location "D:\Projects\SmartITHelpdesk\backend"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.setup_local
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
~~~

In another PowerShell:

~~~powershell
Set-Location "D:\Projects\SmartITHelpdesk\frontend"
npm.cmd ci
npm.cmd run dev
~~~

Open <http://127.0.0.1:5173>. Keep both server windows running. Use this hostname consistently; localhost and 127.0.0.1 have separate cookies.

### Local setup

The setup command prompts for the PostgreSQL port and postgres password, creates a dedicated non-superuser role called helpdesk_app and database smart_it_helpdesk, writes the application's settings to backend/.env, applies migrations and asks you to create the helpdesk administrator.

The PostgreSQL administrator password is never saved. Existing .env settings are kept. An existing role/database without the matching .env stops setup rather than taking it over. Running setup again reapplies pending migrations and creates an administrator only if none is active.

The helpdesk password needs 12–128 characters. Password input is intentionally invisible.

To deliberately create another administrator:

~~~powershell
Set-Location "D:\Projects\SmartITHelpdesk\backend"
.\.venv\Scripts\python.exe -m app.create_admin
~~~

An existing email is never silently promoted or reset.

## Usage

1. Sign in with the administrator created during setup.
2. Create a ticket; open it and use Manage ticket to change status/category/priority.
3. Send a reply. Conversation and change history remain on the ticket.
4. Sign out and create an employee account to test employee access.
5. The employee can see and reply to their own tickets. The API also enforces permissions.
6. Refresh a ticket or reload the page to fetch recent changes. This release has no push/live-update channel.

API documentation: <http://127.0.0.1:8000/docs>. For write requests, set the x-helpdesk-request header to 1. Login sets the session cookie.

## Code and documentation

| Location | Contents |
| --- | --- |
| backend/app | API, models, authentication and local setup |
| backend/alembic | Versioned migrations |
| backend/tests | Database-backed integration tests |
| backend/.env.example | Settings template; never commit .env |
| frontend/src | Login, overview, ticket and reply screens |
| docs/WINDOWS_SETUP.md | PowerShell setup and troubleshooting |
| docs/ARCHITECTURE.md | Schema, API and security decisions |
| docs/VERIFICATION.md | Observed tests and limitations |

## Version control

Before applying Phase 2, commit the working Phase 1 source if you have not done so:

~~~powershell
Set-Location "D:\Projects\SmartITHelpdesk"
git init -b main
git add .gitignore README.txt backend frontend
git commit -m "Set up React frontend and FastAPI health endpoint"
~~~

Skip git init if the repository already exists. After Phase 2 works:

~~~powershell
Set-Location "D:\Projects\SmartITHelpdesk"
git add .gitignore README.md README.txt backend frontend docs
git commit -m "Add PostgreSQL accounts and ticket management"
~~~

If Git requests identity, configure your own name and email. Do not invent authors or backdate commits. GitHub creation/push will follow; this archive does not claim a remote repository exists.

## Phase 3 AI methodology

- Acquire labeled IT-issue examples with documented source and permission.
- Group duplicates before train/validation/test splitting to prevent leakage.
- Fit TF-IDF + Logistic Regression on training data only.
- Select uncertainty thresholds on validation data and retain manual review.
- Report measured test accuracy, macro-F1 and a confusion matrix.
- Add admin-uploaded PDF/TXT extraction and source-linked TF-IDF retrieval.
- Evaluate English first; Bangla/Banglish support needs separate evidence.

No model is trained or evaluated in this release. There are no claimed accuracy figures.

## Following phases

AI and document assistance; measured evaluation; usage screenshots and final report; GitHub publication; free-host deployment. Verify hosting quotas when deploying. Before public access, configure HTTPS, secure cookies, exact origins, registration policy and shared rate limits.
