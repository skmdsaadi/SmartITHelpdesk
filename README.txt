Smart IT Helpdesk — version 1.0.0 (final)

Existing Phase 2 or 3 installation: follow docs/PHASE4_SETUP.md.
First installation: README.md and docs/WINDOWS_SETUP.md.

Working: PostgreSQL accounts/tickets, English AI category suggestions,
admin PDF/TXT knowledge upload and source-backed private conversations.
Model evidence: docs/MODEL_CARD.md and docs/evaluation/.
Knowledge method: docs/KNOWLEDGE_METHOD.md (extractive search, no LLM or API key).
Free hosting configuration: docs/DEPLOYMENT.md (branch phase5-deployment).
Hosting account setup, verified public URL, independent evaluation and final report remain pending.

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

Live: https://smart-it-helpdesk-hdw5.onrender.com/
Proposal: docs/PROPOSAL.md   Final report: docs/FINAL_REPORT.md
