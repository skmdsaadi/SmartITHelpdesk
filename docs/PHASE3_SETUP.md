# Phase 3 upgrade — Windows PowerShell

Project: `D:\Projects\SmartITHelpdesk`. Prerequisite: working Phase 2 with PostgreSQL and a GitHub remote. This upgrade adds category suggestions, AI snapshots and administrator evaluation. It does not replace the database or reset accounts.

## 1. Stop development servers

Press **Ctrl+C** in both the backend and frontend PowerShell windows.

## 2. Get the Phase 3 branch

Run this entire block in Windows PowerShell:

```powershell
& {
    $ErrorActionPreference = "Stop"
    Set-Location "D:\Projects\SmartITHelpdesk"
    $pending = @(git status --porcelain)
    if ($LASTEXITCODE -ne 0) { throw "Cannot read Git status." }
    if ($pending.Count -gt 0) { throw "There are uncommitted changes. Stop and share git status --short." }
    git fetch origin
    if ($LASTEXITCODE -ne 0) { throw "Git fetch failed." }
    git switch phase3-ai-classifier
    if ($LASTEXITCODE -ne 0) { throw "Branch switch failed." }
    git pull --ff-only origin phase3-ai-classifier
    if ($LASTEXITCODE -ne 0) { throw "Git update failed." }
}
```

No force push, reset or automatic deletion is used. The existing main branch remains available. The published branch can be reviewed in its pull request.

## 3. Update the backend and apply the migration

```powershell
& {
    $ErrorActionPreference = "Stop"
    Set-Location "D:\Projects\SmartITHelpdesk\backend"
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Backend package installation failed." }
    .\.venv\Scripts\python.exe -m app.setup_local
    if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }
    .\.venv\Scripts\python.exe -m app.train_classifier
    if ($LASTEXITCODE -ne 0) { throw "AI evaluation failed." }
    .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
}
```

The existing `.env` is preserved. Migration `0002` adds a nullable JSONB column to tickets; earlier records keep a null AI assessment. Existing administrator credentials remain valid. The model needs no API key. The first backend health or AI request fits the small training partition once in memory; a restart fits it again deterministically.

The evaluation command prints the synthetic test accuracy and writes local evaluation files. It does not train on all 324 examples: only the 216 training rows are used for fitting.

## 4. Start the frontend

In another Windows PowerShell:

```powershell
& {
    Set-Location "D:\Projects\SmartITHelpdesk\frontend"
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw "Frontend package installation failed." }
    npm.cmd run dev
}
```

Open <http://127.0.0.1:5173> and sign in.

## 5. Check the workflow

- Confirm your earlier ticket still appears.
- Create a ticket with title `Unable to connect to office Wi-Fi` and description `My laptop cannot connect to the office wireless network. The Wi-Fi connection fails every time.`
- Click **Suggest category**, then **Use Network**. You can select a different category at any time before submission.
- Submit, refresh and inspect **AI assessment at submission**.
- As administrator, open **AI insights**. The report distinguishes overall accuracy, suggestion coverage and accepted accuracy.
- Try a Bangla description. The demo requests an English description or manual category; ordinary ticket submission remains available.

An old ticket correctly displays that no AI assessment was saved. This is not a failed migration.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Branch not found | Confirm fetch succeeded and origin is the SmartITHelpdesk repository |
| Git reports local changes | Preserve your edits; do not use reset or force commands |
| Backend reports database needs setup | Rerun `app.setup_local` from the backend folder |
| AI unavailable | Check package installation and `backend/data/`; restart the backend after correction |
| Suggest category disabled | Enter a title of at least 5 characters and description of at least 15 characters |
| Suggestion is cleared | Editing title/description invalidates the earlier prediction intentionally |
| Low-confidence message | Select the category yourself; this is expected abstention behavior |
| AI insights missing | The page is visible to administrators only |

Share only an error if one occurs. Do not include database passwords, `.env` content or authentication tokens.
