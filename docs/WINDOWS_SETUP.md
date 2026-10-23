> **Phase 4:** If Phase 2 or 3 already works, follow [PHASE4_SETUP.md](PHASE4_SETUP.md). For a first installation, use the database/setup steps below with the current repository checkout; the older ZIP-update step is only for the Phase 1-to-2 archive workflow.

# Phase 2 setup — Windows PowerShell

## 1. Stop the running servers

Press Ctrl+C in both backend and frontend windows. Keep the existing project at D:\Projects\SmartITHelpdesk.

## 2. PostgreSQL

If already installed, use the existing PostgreSQL port/password. To see local services:

~~~powershell
Get-Service -Name "*postgres*" -ErrorAction SilentlyContinue
~~~

If not installed, run:

~~~powershell
winget install --id PostgreSQL.PostgreSQL.17 --exact --interactive --source winget --accept-source-agreements --accept-package-agreements
~~~

Keep PostgreSQL Server and Command Line Tools selected. Use port 5432 unless another installation occupies it. Choose and remember the postgres password; keep the default locale. Skip Stack Builder.

Official reference: <https://www.postgresql.org/download/windows/>.
Package: <https://github.com/microsoft/winget-pkgs/tree/master/manifests/p/PostgreSQL/PostgreSQL/17>.

## 3. Apply the source update

Download Smart_IT_Helpdesk_Phase2.zip into Downloads. Paste this entire block:

~~~powershell
& {
    $ErrorActionPreference = "Stop"
    $zip = Join-Path $env:USERPROFILE "Downloads\Smart_IT_Helpdesk_Phase2.zip"
    $stage = Join-Path $env:TEMP ("HelpdeskPhase2_" + [guid]::NewGuid().ToString("N"))
    if (-not (Test-Path -LiteralPath $zip)) {
        throw "Phase 2 ZIP file was not found in Downloads."
    }
    Expand-Archive -LiteralPath $zip -DestinationPath $stage
    python (Join-Path $stage "SmartITHelpdesk_Phase2\apply_update.py") --project "D:\Projects\SmartITHelpdesk"
    if ($LASTEXITCODE -ne 0) { throw "Source update failed. Stop here." }
}
~~~

The command prints a source-backup path. It preserves .env, .venv, node_modules, .git, uploads and unlisted files. It does not back up PostgreSQL itself.

## 4. Backend packages and database

~~~powershell
& {
    $ErrorActionPreference = "Stop"
    Set-Location "D:\Projects\SmartITHelpdesk\backend"
    if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
    }
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Package installation failed. Stop here." }
    .\.venv\Scripts\python.exe -m app.setup_local
    if ($LASTEXITCODE -ne 0) { throw "Database setup failed. Stop here." }
}
~~~

| Prompt | Enter |
| --- | --- |
| PostgreSQL port [5432] | Enter for default, or the installed port |
| PostgreSQL postgres password | Password from the installer |
| Full name | Helpdesk administrator's name |
| Admin email | Email for application login |
| Admin password | Passphrase with at least 12 characters |
| Confirm admin password | Same passphrase |

Password characters are invisible. PostgreSQL credentials and helpdesk credentials are separate.

## 5. Start the app

Backend:

~~~powershell
Set-Location "D:\Projects\SmartITHelpdesk\backend"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
~~~

Keep that window running. In another PowerShell:

~~~powershell
& {
    Set-Location "D:\Projects\SmartITHelpdesk\frontend"
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw "Frontend installation failed. Stop here." }
    npm.cmd run dev
}
~~~

Open <http://127.0.0.1:5173>. Sign in using the administrator email/password from step 4.

## 6. Working-phase checks

Create a ticket, set it to In Progress, add a reply and reload to verify persistence. Sign out and create an employee account. That employee must not see the administrator's ticket. Create an employee ticket, then sign in as administrator to resolve it.

Record the Phase 2 Git commit using the main README commands.

## Troubleshooting

| Message or symptom | Action |
| --- | --- |
| ZIP not found | Check Downloads and exact filename; Windows may append (1) |
| Phase 1 not found | Check D:\Projects\SmartITHelpdesk |
| Cannot connect to PostgreSQL | Check service, port and installer password |
| Role/database exists but .env missing | Restore the matching .env; do not delete existing data |
| Database operation failed | Verify PostgreSQL and rerun setup |
| Address already in use | Stop the previous server occupying that port |
| Another update was saved | Refresh the ticket before editing |
| HTTP 403 on a write | Use the documented URL and required header |
| Missing session cookie | Use 127.0.0.1 consistently |
| Admin creation failed after DB setup | Run app.setup_local again |
| Git requests identity | Configure your own name/email |

If a step fails, stop and send the error screenshot. Do not include passwords or backend/.env.
