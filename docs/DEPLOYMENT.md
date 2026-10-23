# Deploy Smart IT Helpdesk — Phase 5

**Status:** deployment code is prepared on `phase5-deployment`. A public Render URL has not yet been verified. Creating the hosting resources and completing the live checks below are still required.

The Docker image builds React, then serves the compiled UI and FastAPI from one HTTPS origin. Neon stores accounts, tickets, document text and chat history. No AI key, paid AI service or persistent application disk is required. The hosted database is separate from the PostgreSQL database on your PC; local accounts and uploaded documents are not copied automatically.

## 1. Create the database on Neon Free

1. Open [Neon Console](https://console.neon.tech/) and sign in or create your own account.
2. Create a project named `smart-it-helpdesk` on the **Free** plan. Choose **AWS Asia Pacific (Singapore)** and PostgreSQL **17**. Use a dedicated project for this application.
3. Keep the provided database and role names, or create a dedicated database and its owning role.
4. Click **Connect**. Select the intended branch, database and role. Turn **Connection pooling off** to obtain a direct connection for this small single-service deployment.
5. Copy only the connection URI beginning `postgresql://`, without a `psql` command or surrounding quotes. Keep `sslmode=require` and any `channel_binding=require` query option supplied by Neon.
6. Store the URI privately. Paste it only into Render's `DATABASE_URL` secret field in the next step. Do not commit it, put it in React code, or send it in chat/screenshots.

The app selects the Psycopg 3 driver itself. There is no need to change `postgresql://` to another prefix. No SQL needs to be pasted into Neon: startup applies the versioned migrations.

## 2. Create the Render service

1. Open [Render Dashboard](https://dashboard.render.com/) and sign in with your account.
2. Choose **New → Blueprint** and select `skmdsaadi/SmartITHelpdesk`. If asked to authorize GitHub, grant access to this repository.
3. Select the **`phase5-deployment` branch** and the root `render.yaml`. The repository's current `main` branch does not yet include this deployment configuration.
4. Review the proposed resources: **one Docker Web Service**, **Free** plan, **Singapore**. This Blueprint does not create a Render database or a paid service.
5. Enter these four private values when prompted:

| Environment variable | Value to enter |
| --- | --- |
| `DATABASE_URL` | The direct PostgreSQL URI from Neon |
| `BOOTSTRAP_ADMIN_NAME` | Your desired administrator display name |
| `BOOTSTRAP_ADMIN_EMAIL` | The email you will use to sign in |
| `BOOTSTRAP_ADMIN_PASSWORD` | A private password/passphrase of 12–128 characters |

6. Apply the Blueprint. Render builds the Docker image and runs `python -m app.start`.
7. Wait for the service to show **Live**, then open its assigned `https://….onrender.com` URL.

If using **New → Web Service** instead, select the same repo/branch, **Docker**, **Free**, **Singapore**, and leave Root Directory blank. Use `./Dockerfile`, Docker context `.`, and health-check path `/healthz`. Add the four private variables above plus `APP_ENV=production`, `COOKIE_SECURE=true`, `ALLOW_REGISTRATION=true`, and `SESSION_HOURS=12`. Set automatic deploys to **Off**. Build and start commands come from the Dockerfile.

Render supplies `RENDER_EXTERNAL_URL`; the application automatically allows that exact HTTPS origin. No frontend API URL or CORS setting is needed. For a custom domain later, also set `ALLOWED_ORIGINS=https://your-domain.example` and configure that domain in Render.

## 3. Sign in and remove bootstrap secrets

1. Sign in with the administrator email/password you entered in Render. Your local PC administrator account is separate.
2. In Render → service → **Environment**, remove `BOOTSTRAP_ADMIN_NAME`, `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`. Keep `DATABASE_URL` and the other settings.
3. Save and redeploy. Sign in again if needed.

Bootstrap only creates an administrator when no active administrator exists. It never changes an existing account's role or password, and changing bootstrap values does not reset a password. After successful startup the bootstrap values are also removed from the serving process environment. Removing the values from Render prevents them from being supplied to later deployments.

Migrations and administrator creation share a transaction protected by a PostgreSQL advisory lock. A failure stops startup. A restart preserves existing accounts, tickets and source text. This does not replace database backups or make incompatible future schema changes automatically safe.

## 4. Verify the live application

- Open `/healthz`: expect HTTP 200 with version `0.5.0`. This is a lightweight process check.
- Open `/api/v1/health`: expect `status: ok`, `database: ready` and `ai: ready_demo`. This checks the database/schema and initializes the local classifier.
- Sign in as administrator. Upload `docs/examples/IT_Helpdesk_Demo_Guide.txt` from **Knowledge** and inspect its passages.
- Ask `How do I troubleshoot a Wi-Fi connection?`. Follow the source link and refresh the page.
- Sign out. Choose **Create account** to create a separate employee test account. Submit a Wi-Fi ticket and apply or override its AI category suggestion.
- Sign in as administrator, update that ticket and add a reply. Confirm the employee sees the update.
- In Render, manually redeploy the same commit. Confirm the accounts, ticket, document and conversation remain available.
- Test the public URL on a phone. Record the URL and deployment commit for the capstone submission.

Share only the public application URL when asking for deployment verification. Do not share passwords or database connection strings. An HTTP 200 on `/healthz` alone is not evidence that the complete app works.

## Registration and demo limits

The Blueprint enables employee self-registration so an evaluator can create an account. All active knowledge documents are visible to all signed-in users. Use the included illustrative guide or other material intended for that audience. For a closed demonstration, create the required employee accounts first, then set `ALLOW_REGISTRATION=false` in Render and in `render.yaml` before the next Blueprint sync.

The container runs one Uvicorn worker with a concurrency ceiling of 16; production uses four synchronous worker threads and serializes password hashing/verification. Numerical libraries use one thread. This is a small capstone demo, not a tested company-scale service.

Login and registration limits are held in that worker's memory and reset on restart. Forwarded client-IP headers are not trusted; users behind the same Render proxy may share the limit (20 login attempts per five minutes; 10 registrations per 30 minutes). Chat and upload limits use account IDs. Add a durable shared limiter and an appropriate trusted-proxy configuration before scaling or relying on stronger abuse protection. Email verification, password recovery and administrator user management are not implemented.

## Free-plan behavior

Checked against official documentation on **23 October 2026**; provider allowances can change.

- Render Free has **512 MB RAM** and **0.1 CPU**, sleeps after **15 minutes** without inbound traffic, and can take about a minute to wake. The workspace shares **750 free instance hours/month**. Local filesystem changes do not persist. Review bandwidth/build usage and billing settings; exceeding allowances can suspend services or incur charges when a payment method is present.
- Neon Free currently includes **1 GB PostgreSQL storage** and **100 CU-hours per project/month**, with scale-to-zero after five idle minutes. Monitor the project's usage dashboard.
- Render's frequent health probe uses `/healthz`, which does not query Neon or fit the model. The user-facing readiness endpoint is separate, allowing an idle database to sleep.

The quotas in the app bound knowledge uploads and conversations; they do not guarantee staying within every hosting allowance. No keep-alive automation is included.

## Updates and troubleshooting

Automatic deploys are off. After a reviewed code update, choose **Manual Deploy → Deploy latest commit** in Render. Deploy the branch containing all phases. After the work is merged to `main`, update both the Render service branch and `render.yaml` together.

| Symptom | Check |
| --- | --- |
| `render.yaml` cannot be found | Select the `main` branch after all phase pull requests are merged |
| Frontend build missing | Use the root Dockerfile/context; do not deploy only `backend/` |
| Startup stopped / database preparation failed | Check the direct Neon URI, database/role, TLS query options, project state and network access; keep the URI private |
| First deployment requires bootstrap values | Supply all three `BOOTSTRAP_ADMIN_*` values in Render Environment and redeploy |
| Admin settings invalid | Name 2–100 characters, valid email, password 12–128 characters |
| Existing email / no password or role changed | Bootstrap cannot promote an employee; use an unused admin email if no admin exists |
| Login error after using PC credentials | Use the separate administrator created for the hosted database |
| HTTP 403 on a custom domain | Add the exact HTTPS origin to `ALLOWED_ORIGINS` and redeploy |
| HTTP 429 | Wait for the request-limit window; do not repeatedly resubmit |
| Slow first page | Allow the free service/database to wake, then retry |
| HTTP 503 under simultaneous load | Allow in-flight work to finish; inspect Render memory/CPU and Neon usage |
| `/docs` returns 404 online | Interactive API docs are disabled in production; they remain available locally |

If a deployment fails, report the error text with credentials redacted. Do not delete the database or downgrade migrations as a troubleshooting shortcut. Back up data before schema changes; a Render code rollback does not roll back Neon data or schema.

## Official references

- [Render Free](https://render.com/docs/free) and [compute plans](https://render.com/docs/compute-plans)
- [Render Blueprint fields](https://render.com/docs/blueprint-spec), [default environment variables](https://render.com/docs/environment-variables), [health checks](https://render.com/docs/health-checks)
- [Neon Free limits](https://neon.com/faqs/free-plan-limits-and-quotas), [regions](https://neon.com/docs/introduction/regions), [connection strings](https://neon.com/docs/connect/connect-from-any-app)
