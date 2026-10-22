Smart IT Helpdesk — Phase 2 / 0.2.0

Start with README.md and docs/WINDOWS_SETUP.md.
This release includes PostgreSQL accounts, login/logout, dashboard and tickets.
AI, knowledge upload, GitHub publication and deployment are later phases.

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
