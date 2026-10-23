# Phase 4 upgrade — Windows PowerShell

Project folder: `D:\Projects\SmartITHelpdesk`. This adds document upload and source-backed conversations to the existing PostgreSQL application. Migration 0003 adds tables while keeping earlier users, tickets and AI assessments.

## 1. Stop development servers

Press **Ctrl+C** in the backend and frontend PowerShell windows.

## 2. Get the Phase 4 branch

Paste the entire block into Windows PowerShell:

```powershell
& {
    $ErrorActionPreference = "Stop"
    Set-Location "D:\Projects\SmartITHelpdesk"
    $pending = @(git status --porcelain)
    if ($LASTEXITCODE -ne 0) { throw "Cannot read Git status." }
    if ($pending.Count -gt 0) {
        throw "Uncommitted changes found. Stop and share git status --short."
    }
    git fetch origin
    if ($LASTEXITCODE -ne 0) { throw "Git fetch failed." }
    git switch phase4-knowledge-chat
    if ($LASTEXITCODE -ne 0) { throw "Branch switch failed." }
    git pull --ff-only origin phase4-knowledge-chat
    if ($LASTEXITCODE -ne 0) { throw "Git update failed." }
}
```

## 3. Update and start the backend

```powershell
& {
    $ErrorActionPreference = "Stop"
    Set-Location "D:\Projects\SmartITHelpdesk\backend"
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Package installation failed." }
    .\.venv\Scripts\python.exe -m app.setup_local
    if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }
    .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
}
```

Keep this window open. Existing credentials and `backend/.env` remain valid. No AI API key is needed.

## 4. Start the frontend in another PowerShell window

```powershell
& {
    $ErrorActionPreference = "Stop"
    Set-Location "D:\Projects\SmartITHelpdesk\frontend"
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw "Frontend installation failed." }
    npm.cmd run dev
}
```

Open <http://127.0.0.1:5173> and sign in as administrator.

## 5. Upload the example guide

Open **Knowledge**. Enter `Demo IT Support Guide` as the document title and select:

```text
D:\Projects\SmartITHelpdesk\docs\examples\IT_Helpdesk_Demo_Guide.txt
```

Click **Upload document**, then **View passages**. This file is illustrative test content, not an approved policy for your workplace. The app starts with no uploaded documents; it does not seed this example into the database automatically.

## 6. Try the source-backed conversation

Open **Ask helpdesk** and ask:

```text
How do I troubleshoot a Wi-Fi connection?
```

The response should quote the Wi-Fi guide and show a document-title link. Click it to see the highlighted source passage. Return to the conversation and refresh the page to verify history remains saved.

Ask an unrelated question:

```text
How do I bake a chocolate birthday cake?
```

This should show a no-match response. The chat searches each question independently and quotes document text; it does not generate an LLM answer or use earlier messages as context.

Optionally deactivate the example guide, refresh the earlier conversation and confirm its source text is hidden. Reactivate it to make the retained citations visible again. Try a small PDF with selectable text to verify extraction on your Windows installation. Scanned PDFs need OCR; encrypted PDFs are rejected. The file limit is 2 MiB.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Branch switch stops because of changes | Preserve edits and share `git status --short`; do not reset your work |
| Knowledge menu missing | Confirm the Phase 4 branch and restart Vite |
| Upload controls missing | Sign in as administrator |
| No usable text found | Use a PDF with selectable text or a UTF-8 TXT export |
| PDF too complex/slow | Reduce it to fewer pages or export its text |
| Duplicate file | Open the existing document or reactivate it |
| No matching passage | Use terms from the document, inspect its text, or create a ticket |
| Earlier sources unavailable | An administrator deactivated/removed those sources; ask again against current documents |
| Connection interrupted after asking | Retry the unchanged question to reuse the same request ID, or refresh history to see whether it was saved |

Report only an error if one occurs; do not share passwords, `.env` contents or session cookies.
