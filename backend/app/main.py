"""PostgreSQL accounts, sessions, tickets and an audited admin workflow."""
from typing import Annotated
from contextlib import asynccontextmanager
import anyio
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.body_limit import RequestBodyLimitMiddleware
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from . import classifier, config
from .database import get_engine
from .knowledge_api import router as knowledge_router
from .knowledge_limits import MAX_UPLOAD_BYTES
from .models import AuthSession, Comment, Ticket, TicketEvent, User, utcnow
from .web import mount_frontend
from .schemas import (
    Category, CommentInput, CommentOutput, DashboardOutput, EventOutput, LoginInput,
    Priority, RegisterInput, Status, TicketDetail, TicketInput, TicketOutput,
    TicketPage, TicketUpdate, UserOutput, TicketText, AIResult,
)
from .security import (
    AdminUser, CurrentUser, DB, dummy_hash, limit_auth, password_hasher, password_work,
    start_session, token_hash,
)

def browser_request_guard(request: Request, x_helpdesk_request: Annotated[str | None, Header()] = None):
    """A custom header plus exact Origin validation protects cookie-auth mutations."""
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if x_helpdesk_request != "1" or (origin and origin not in config.ALLOWED_ORIGINS):
            raise HTTPException(403, "Request origin or security header is not allowed.")
        if request.headers.get("sec-fetch-site") == "cross-site":
            raise HTTPException(403, "Cross-site requests are not allowed.")

@asynccontextmanager
async def lifespan(_app):
    config.validate_runtime()
    if config.PRODUCTION:
        anyio.to_thread.current_default_thread_limiter().total_tokens = 4
    yield


app = FastAPI(
    title="Smart IT Helpdesk API", version="1.0.0", lifespan=lifespan,
    docs_url=None if config.PRODUCTION else "/docs",
    redoc_url=None if config.PRODUCTION else "/redoc",
    openapi_url=None if config.PRODUCTION else "/openapi.json", redirect_slashes=False,
    description="Accounts, tickets, category suggestions and document-backed conversations. Write requests require "
                "X-Helpdesk-Request: 1. Login sets an HttpOnly session cookie.",
    dependencies=[Depends(browser_request_guard)],
)
app.include_router(knowledge_router)
app.add_middleware(RequestBodyLimitMiddleware, max_body_size=MAX_UPLOAD_BYTES)

@app.middleware("http")
async def response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    if config.PRODUCTION:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self' data:; connect-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        if request.url.path.startswith("/assets/") and response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response

@app.exception_handler(SQLAlchemyError)
async def database_error(_request: Request, _error: SQLAlchemyError):
    return JSONResponse(status_code=503, content={
        "detail": "Database operation failed. Check PostgreSQL and run database migrations."
    })

@app.get("/healthz", include_in_schema=False)
async def liveness():
    # Render probes this frequently. Do not wake an idle Neon database or fit AI.
    return {"status": "ok", "service": "smart-it-helpdesk", "version": "1.0.0"}


@app.get("/api/v1/health", tags=["System"])
def health(response: Response):
    ready = False
    try:
        with get_engine().connect() as connection:
            ready = connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0003"
    except (SQLAlchemyError, RuntimeError, ValueError):
        pass
    if not ready:
        response.status_code = 503
    return {
        "status": "ok" if ready else "degraded", "service": "smart-it-helpdesk",
        "version": "1.0.0", "timestamp": utcnow(),
        "components": {"api": "ready", "database": "ready" if ready else "needs_setup",
                       "authentication": "ready", "tickets": "ready", "knowledge": "ready" if ready else "needs_setup",
                       "ai": "ready_demo" if classifier.get_model() else "unavailable"},
        "registration_enabled": config.ALLOW_REGISTRATION,
    }

@app.post("/api/v1/auth/register", response_model=UserOutput, status_code=201, tags=["Accounts"])
def register(data: RegisterInput, request: Request, response: Response, db: DB):
    if not config.ALLOW_REGISTRATION:
        raise HTTPException(403, "Account registration is currently disabled.")
    limit_auth(request, "register")
    with password_work:
        hashed = password_hasher.hash(data.password)
    user = User(name=data.name, email=str(data.email).lower(), role="employee", password_hash=hashed)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists.") from None
    start_session(db, user, response, request.cookies.get(config.COOKIE_NAME))
    return user

@app.post("/api/v1/auth/login", response_model=UserOutput, tags=["Accounts"])
def login(data: LoginInput, request: Request, response: Response, db: DB):
    limit_auth(request, "login")
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    with password_work:
        valid = password_hasher.verify(data.password, user.password_hash if user else dummy_hash)
    if not user or not valid or not user.is_active:
        raise HTTPException(401, "Email or password is incorrect.")
    start_session(db, user, response, request.cookies.get(config.COOKIE_NAME))
    return user

@app.get("/api/v1/auth/me", response_model=UserOutput, tags=["Accounts"])
def me(user: CurrentUser):
    return user

@app.post("/api/v1/auth/logout", status_code=204, tags=["Accounts"])
def logout(request: Request, response: Response, db: DB):
    token = request.cookies.get(config.COOKIE_NAME)
    if token:
        db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash(token)))
        db.commit()
    response.delete_cookie(config.COOKIE_NAME, path="/api", httponly=True,
                           secure=config.COOKIE_SECURE, samesite="lax")

def visible_tickets(user: User):
    stmt = select(Ticket)
    if user.role != "admin":
        stmt = stmt.where(Ticket.created_by == user.id)
    return stmt

def find_ticket(db, user: User, ticket_id: int, lock=False):
    stmt = visible_tickets(user).where(Ticket.id == ticket_id)
    if lock:
        stmt = stmt.with_for_update(of=Ticket)
    ticket = db.scalar(stmt)
    if not ticket:
        raise HTTPException(404, "Ticket not found.")
    return ticket

def ticket_detail(db, ticket):
    data = TicketOutput.model_validate(ticket).model_dump()
    data["comments"] = [CommentOutput.model_validate(item) for item in db.scalars(
        select(Comment).where(Comment.ticket_id == ticket.id).order_by(Comment.created_at, Comment.id))]
    data["events"] = [EventOutput.model_validate(item) for item in db.scalars(
        select(TicketEvent).where(TicketEvent.ticket_id == ticket.id).order_by(TicketEvent.created_at, TicketEvent.id))]
    return data

@app.get("/api/v1/dashboard", response_model=DashboardOutput, tags=["Dashboard"])
def dashboard(user: CurrentUser, db: DB):
    filtered = visible_tickets(user)
    base = filtered.subquery()
    groups = dict(db.execute(select(base.c.status, func.count()).group_by(base.c.status)).all())
    return {
        "total": sum(groups.values()), "open": groups.get("Open", 0),
        "in_progress": groups.get("In Progress", 0), "resolved": groups.get("Resolved", 0),
        "high_priority": db.scalar(select(func.count()).select_from(base).where(
            base.c.priority == "High", base.c.status != "Resolved")),
        "recent": db.scalars(filtered.order_by(Ticket.updated_at.desc(), Ticket.id.desc()).limit(5)).all(),
    }

@app.get("/api/v1/tickets", response_model=TicketPage, tags=["Tickets"])
def list_tickets(
    user: CurrentUser, db: DB, status: Status | None = None,
    category: Category | None = None, priority: Priority | None = None,
    search: Annotated[str, Query(max_length=160)] = "",
    page: Annotated[int, Query(ge=1, le=100000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 10,
):
    stmt = visible_tickets(user)
    for field, value in [(Ticket.status, status), (Ticket.category, category), (Ticket.priority, priority)]:
        if value is not None:
            stmt = stmt.where(field == value)
    if search.strip():
        query = search.strip()
        stmt = stmt.where(or_(Ticket.title.icontains(query, autoescape=True),
                              Ticket.description.icontains(query, autoescape=True)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Ticket.created_at.desc(), Ticket.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}

@app.post("/api/v1/tickets", response_model=TicketOutput, status_code=201, tags=["Tickets"])
def create_ticket(data: TicketInput, user: CurrentUser, db: DB):
    ai = classifier.classify(data.title, data.description)
    ai.update(selected_category=data.category, recorded_at=utcnow().isoformat())
    ticket = Ticket(**data.model_dump(), created_by=user.id, status="Open", ai_assessment=ai)
    db.add(ticket)
    db.flush()
    db.add(TicketEvent(ticket_id=ticket.id, user_id=user.id, message="Ticket opened."))
    db.commit()
    db.refresh(ticket)
    return ticket

@app.get("/api/v1/tickets/{ticket_id}", response_model=TicketDetail, tags=["Tickets"])
def get_ticket(ticket_id: int, user: CurrentUser, db: DB):
    return ticket_detail(db, find_ticket(db, user, ticket_id))

@app.patch("/api/v1/tickets/{ticket_id}", response_model=TicketDetail, tags=["Tickets"])
def update_ticket(ticket_id: int, data: TicketUpdate, user: AdminUser, db: DB):
    ticket = find_ticket(db, user, ticket_id, lock=True)
    if data.version != ticket.version:
        raise HTTPException(409, "Another update was saved. Refresh this ticket before changing it.")
    changes = []
    for field in ["status", "priority", "category"]:
        before, after = getattr(ticket, field), getattr(data, field)
        if before != after:
            changes.append(f"{field.capitalize()}: {before} → {after}")
            setattr(ticket, field, after)
    if changes:
        ticket.updated_at = utcnow()
        ticket.version += 1
        if ticket.status == "Resolved" and ticket.resolved_at is None:
            ticket.resolved_at = utcnow()
        elif ticket.status != "Resolved":
            ticket.resolved_at = None
        db.add(TicketEvent(ticket_id=ticket.id, user_id=user.id, message="; ".join(changes)))
        db.commit()
        db.refresh(ticket)
    return ticket_detail(db, ticket)

@app.post("/api/v1/tickets/{ticket_id}/comments", response_model=CommentOutput,
          status_code=201, tags=["Tickets"])
def add_comment(ticket_id: int, data: CommentInput, user: CurrentUser, db: DB):
    ticket = find_ticket(db, user, ticket_id, lock=True)
    comment = Comment(ticket_id=ticket.id, user_id=user.id, body=data.body)
    db.add(comment)
    ticket.updated_at = utcnow()
    db.commit()
    db.refresh(comment)
    return comment


@app.post("/api/v1/ai/classify", response_model=AIResult, tags=["AI"])
def classify_draft(data: TicketText, user: CurrentUser):
    # No ticket IDs or other users' text are involved in a draft prediction.
    return classifier.classify(data.title, data.description)


@app.get("/api/v1/ai/model", tags=["AI"])
def model_evaluation(user: AdminUser):
    model = classifier.get_model()
    if model is None:
        raise HTTPException(503, "AI model unavailable. Check backend packages and bundled dataset, then restart.")
    return model.report


mount_frontend(app, config.FRONTEND_DIST)
