# Smart IT Helpdesk

An AI capstone that brings employee IT requests, administrator workflows and category suggestions into one web application.

**Version 1.0.0 — final capstone release.** React + Vite + TypeScript + Tailwind CSS, Python + FastAPI, PostgreSQL, a scikit-learn ticket classifier and document-backed conversations.

**Live application:** <https://smart-it-helpdesk-hdw5.onrender.com/> (Render Free web service + Neon Free PostgreSQL). The free service sleeps when idle, so the first visit can take about a minute to load. Evaluators can register an employee account; administrator access is provided on request.

| Deliverable | Location |
| --- | --- |
| Project proposal | [docs/PROPOSAL.md](docs/PROPOSAL.md) |
| Final report | [docs/FINAL_REPORT.md](docs/FINAL_REPORT.md) |
| AI model card | [docs/MODEL_CARD.md](docs/MODEL_CARD.md) |
| Knowledge search method | [docs/KNOWLEDGE_METHOD.md](docs/KNOWLEDGE_METHOD.md) |
| Evaluation evidence | [docs/evaluation/](docs/evaluation/README.md) |
| Deployment guide | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |

## Problem and proposed solution

IT teams often receive issues through scattered calls, messages and email. Requests lack consistent categories, employees cannot see progress, and administrators repeat triage work. Smart IT Helpdesk provides a central ticket, conversation and status history. An AI model suggests a category while the person submitting the issue keeps the final choice.

The six categories are **Email, Network, Hardware, Software, Printer and Access**. The application does not diagnose devices, run repair commands or automatically grant access.

## Working features

- Employee registration, administrator provisioning, secure sign-in and sign-out.
- PostgreSQL-backed tickets, comments, activity history and dashboard counts.
- Employees see their own requests; administrators can view and manage all requests.
- Status, priority and category filters, search and pagination.
- English ticket-category suggestions with model scores and an explicit **Use category** action.
- Manual selection when a suggestion is uncertain, unsupported or unavailable.
- An immutable AI assessment at ticket creation, stored alongside the person's selected category.
- An administrator **AI insights** page with measured metrics, confusion matrix and limitations.
- Administrator PDF/TXT upload, extracted-text preview, activation and removal.
- **Ask helpdesk** searches active documents and returns matching passages with source links.
- Private conversations saved in PostgreSQL, including protection against duplicate network retries.
- Document deactivation/removal also hides its quotations in earlier chat responses.
- Responsive desktop and mobile layouts.

## Deployment

The application is deployed at <https://smart-it-helpdesk-hdw5.onrender.com/>. To deploy your own copy, follow [the Render + Neon deployment guide](docs/DEPLOYMENT.md) and deploy the `main` branch: the root Dockerfile builds React and serves it with FastAPI on one HTTPS origin. The Blueprint selects one free web service; create the separate PostgreSQL database on Neon Free. Keep database and administrator credentials in the hosting environment.

## Setup

**Already running Phase 2 or 3?** Follow [Phase 4 Windows upgrade](docs/PHASE4_SETUP.md).

**First installation?** Install Python 3.11, Node 22.12+ and PostgreSQL 17, then follow [Windows setup](docs/WINDOWS_SETUP.md) for database and administrator creation. Exact dependencies are recorded in the lockfiles.

From Windows PowerShell, backend:

```powershell
& {
    $ErrorActionPreference = "Stop"
    Set-Location "D:\Projects\SmartITHelpdesk\backend"
    if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Environment creation failed." }
    }
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Package installation failed." }
    .\.venv\Scripts\python.exe -m app.setup_local
    if ($LASTEXITCODE -ne 0) { throw "Database setup failed." }
    .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
}
```

In another PowerShell, frontend:

```powershell
& {
    Set-Location "D:\Projects\SmartITHelpdesk\frontend"
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw "Frontend installation failed." }
    npm.cmd run dev
}
```

Open <http://127.0.0.1:5173>. Use this hostname consistently. The Vite proxy forwards `/api` to FastAPI on port 8000. API documentation is at <http://127.0.0.1:8000/docs>.

The local setup helper keeps an existing `backend/.env`, applies pending Alembic migrations and keeps the existing administrator. On first use it creates a dedicated non-superuser database account and asks for administrator details. Application secrets are ignored by Git.

## Try the AI workflow

1. Sign in and choose **Create ticket**.
2. Title: `Unable to connect to office Wi-Fi`.
3. Description: `My laptop cannot connect to the office wireless network. The Wi-Fi connection fails every time.`
4. Click **Suggest category**. Review the score and choose **Use Network**, or select another category yourself.
5. Submit the ticket. The detail page shows the AI assessment and category selected at submission.
6. As administrator, change the category or status. The event history records the change; the original AI assessment stays intact.
7. Open **AI insights** as administrator to inspect the evaluation.

Changing the title or description clears an earlier suggestion. The server recomputes the assessment from the submitted text, so stale or client-forged predictions are not stored. Existing Phase 2 tickets remain readable with no fabricated historical AI result.

## Try document-backed chat

1. Sign in as administrator and open **Knowledge**.
2. Set the title to `Demo IT Support Guide` and upload [the included demo TXT file](docs/examples/IT_Helpdesk_Demo_Guide.txt).
3. Open **View passages** to inspect the extracted text.
4. Open **Ask helpdesk** and ask `How do I troubleshoot a Wi-Fi connection?`.
5. Follow the document-title link in the response to its highlighted source passage.
6. Refresh the page to confirm that your conversation is saved.
7. Ask an unrelated question, such as `How do I bake a chocolate birthday cake?`, to see the no-match response.

The included guide is illustrative content, not an approved company policy. Active documents are readable by all signed-in users. Only administrators manage documents; every account, including administrators, can read only its own conversations.

**This is extractive document search, not an LLM-generated answer.** Word/character TF-IDF ranks passages; replies quote the matching text. Each question is searched independently. No API key, paid AI service or external document upload is involved. The app does not translate, perform OCR or validate the correctness of an uploaded policy. See [knowledge methodology, permissions and limits](docs/KNOWLEDGE_METHOD.md).

## Demo screenshots

Captures use demo accounts and illustrative ticket text. Model metrics describe the synthetic evaluation dataset, not measured real-office performance.

**Create a ticket and explicitly apply a category suggestion:**

![Ticket creation with a Network suggestion selected by the employee](docs/screenshots/create-ai-desktop.png)

**Administrator AI insights on desktop:**

![Desktop AI insights with synthetic evaluation metrics, data splits and confusion matrix](docs/screenshots/ai-insights-desktop.png)

<details>
<summary>View AI insights on mobile</summary>

![Mobile AI insights with the same metrics and limitations](docs/screenshots/ai-insights-mobile.png)

</details>

**Ask helpdesk — answer quoted from an uploaded guide, with a source link:**

![Ask helpdesk conversation showing a matching passage and its source](docs/screenshots/ask-helpdesk-desktop.png)

**Knowledge library (administrator upload and activation):**

![Knowledge page listing an uploaded guide](docs/screenshots/knowledge-desktop.png)

**Ticket list and ticket detail with conversation and history:**

![Ticket list with filters](docs/screenshots/tickets-desktop.png)

![Ticket detail with AI assessment, replies and activity history](docs/screenshots/ticket-detail-desktop.png)

## AI methodology and results

The bundled dataset contains **324 synthetic English examples**, grouped into **108 issue intents**. It was generated for this capstone; it is not a collection of real employee tickets and its labels have not undergone independent human review.

Word and character TF-IDF features feed a Logistic Regression classifier. Whole intent groups are divided into 216 training, 54 validation and 54 test examples. Vocabulary and IDF are fitted on training data only. Validation chooses an abstention threshold; test examples are never used to fit the model or choose the threshold.

| Held-out synthetic test metric | Observed result |
| --- | --- |
| Accuracy before abstention | 50 / 54 = 92.59% |
| Macro-F1 | 0.9255 |
| Suggestion coverage | 36 / 54 = 66.67% |
| Correct among accepted suggestions | 36 / 36 |
| Majority-class baseline | 16.67% |
| Unrelated test requests incorrectly accepted | 1 / 12 |

**These small synthetic results do not establish real-office accuracy.** Scores are not calibrated confidence guarantees. Bangla and Banglish have not been validated. A person confirms every category.

The model fits once per backend process from the bundled training partition. It requires no paid API, external AI service or downloaded model pickle. See the [model card](docs/MODEL_CARD.md), [dataset provenance](backend/data/README.md) and [evaluation evidence](docs/evaluation/README.md).

To reproduce evaluation without a database:

```powershell
Set-Location "D:\Projects\SmartITHelpdesk\backend"
.\.venv\Scripts\python.exe -m app.train_classifier
```

This writes `backend/evaluation/report.json`, `split_manifest.json`, `test_predictions.csv` and `confusion_matrix.csv`. Local output is ignored by Git. The administrator page calculates the same report from the running model.

## Project structure

| Location | Purpose |
| --- | --- |
| `frontend/src/` | React application and responsive UI |
| `backend/app/main.py` | Authenticated API and ticket workflow |
| `backend/app/classifier.py` | Grouped splits, fitted pipeline, abstention and metrics |
| `backend/app/train_classifier.py` | Reproducible evaluation export |
| `backend/app/knowledge_api.py` | Document management, private conversations and source visibility |
| `backend/app/documents.py`, `pdf_worker.py` | Validated upload, bounded PDF extraction and chunking |
| `backend/app/retrieval.py` | Local TF-IDF passage ranking and no-match behavior |
| `Dockerfile`, `render.yaml` | Single-service hosting configuration |
| `backend/app/start.py`, `web.py` | Transactional startup and compiled UI serving |
| `backend/data/` | Synthetic examples, negative controls and provenance |
| `backend/alembic/` | Versioned database migrations |
| `backend/tests/` | Model, authorization and persistence regression tests |
| `docs/` | Setup, architecture, methodology and observed verification |

## Verification

Fifty-five automated tests passed, including account/ticket/classifier checks, PDF extraction, chat privacy, exact citations, retry handling, source revocation and deployment startup/security cases. The production frontend build and local HTTPS browser workflow passed. Migrations preserve earlier accounts and tickets. The Docker image was then built and deployed on Render with a Neon database (live URL above). See [Phase 5 verification and limits](docs/PHASE5_VERIFICATION.md), [Phase 4 verification](docs/PHASE4_VERIFICATION.md) and [Phase 3 evidence](docs/VERIFICATION.md).

To run database-free tests:

```powershell
& {
    Set-Location "D:\Projects\SmartITHelpdesk\backend"
    .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
    if ($LASTEXITCODE -ne 0) { throw "Test dependency installation failed." }
    .\.venv\Scripts\python.exe -m pytest tests/test_classifier.py tests/test_documents.py tests/test_retrieval.py -q
}
```

Integration tests additionally require `TEST_DATABASE_URL` for a disposable PostgreSQL database. They create a randomly named schema and remove only that schema. Without this explicit setting integration tests are skipped, not counted as passing.

## Limitations and future work

- The classifier is trained and evaluated on 324 synthetic English examples. Real-office accuracy needs a permissioned, anonymized ticket set with independent label review.
- Retrieval thresholds are hand-set; an independent evaluation with real IT guides and questions is still needed.
- Bangla and Banglish are not validated. A multilingual embedding model is the natural next step.
- Knowledge search quotes passages; it does not generate answers. An optional LLM layer could summarize retrieved passages while keeping source links.
- Production use would need shared rate limits, email verification, password recovery, backups and monitoring.

## Version history

Development happened in reviewed phases, each on its own branch and merged by pull request:

| Phase | Branch | Content |
| --- | --- | --- |
| 1–2 | `main` | FastAPI, PostgreSQL accounts, tickets, admin workflow |
| 3 | `phase3-ai-classifier` | TF-IDF + Logistic Regression category suggestions and evaluation |
| 4 | `phase4-knowledge-chat` | PDF/TXT knowledge library and source-backed chat |
| 5 | `phase5-deployment` | Docker, Render Blueprint and Neon deployment |
| 6 | `phase6-final` | Proposal, final report, final README and screenshots |

Authentication details are documented in [architecture](docs/ARCHITECTURE.md); deployment limits in [the deployment guide](docs/DEPLOYMENT.md).
