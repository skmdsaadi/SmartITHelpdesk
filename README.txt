Smart IT Helpdesk — Phase 3 / 0.3.0

Existing Phase 2 installation: follow docs/PHASE3_SETUP.md.
First installation: README.md and docs/WINDOWS_SETUP.md.

Working: PostgreSQL accounts/tickets and English AI category suggestions.
Model evidence: docs/MODEL_CARD.md and docs/evaluation/.
Knowledge upload/chat, deployment and real-ticket evaluation remain pending.

Backend:
  Set-Location "D:\Projects\SmartITHelpdesk\backend"
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  .\.venv\Scripts\python.exe -m app.setup_local
  .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

Frontend (another PowerShell):
  Set-Location "D:\Projects\SmartITHelpdesk\frontend"
  npm.cmd ci
  npm.cmd run dev

Open http://127.0.0.1:5173
