"""Migrate, provision the first administrator, then serve the built application."""
import os
import sys

from alembic import command
from alembic.config import Config
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from . import config
from .database import get_engine
from .models import User
from .schemas import RegisterInput
from .security import password_hasher

# Transaction-scoped PostgreSQL lock serializes migration/bootstrap across restarts.
STARTUP_LOCK = 0x53495448444B
BOOTSTRAP_KEYS = ("BOOTSTRAP_ADMIN_NAME", "BOOTSTRAP_ADMIN_EMAIL", "BOOTSTRAP_ADMIN_PASSWORD")


def bootstrap_admin(db: Session, environ):
    if db.scalar(select(User.id).where(User.role == "admin", User.is_active)):
        return "An active administrator already exists; its credentials were kept unchanged."
    if not all(environ.get(key) for key in BOOTSTRAP_KEYS):
        raise ValueError("First deployment requires BOOTSTRAP_ADMIN_NAME, BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD.")
    try:
        data = RegisterInput(name=environ[BOOTSTRAP_KEYS[0]], email=environ[BOOTSTRAP_KEYS[1]],
                             password=environ[BOOTSTRAP_KEYS[2]])
    except ValidationError:
        raise ValueError("Administrator settings are invalid. Use a name of 2-100 characters, valid email and password of 12-128 characters.") from None
    email = str(data.email).lower()
    if db.scalar(select(User.id).where(User.email == email)):
        raise ValueError("Bootstrap email already belongs to an account. No password or role was changed.")
    db.add(User(name=data.name, email=email, role="admin", password_hash=password_hasher.hash(data.password)))
    db.flush()
    return "First administrator created. Remove BOOTSTRAP_ADMIN_* from the hosting environment after signing in."


def prepare_database():
    migration = Config(str(config.BACKEND_DIR / "alembic.ini"))
    with get_engine().begin() as connection:
        connection.execute(text("SET LOCAL lock_timeout = '60s'"))
        connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": STARTUP_LOCK})
        migration.attributes["connection"] = connection
        command.upgrade(migration, "head")
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            result = bootstrap_admin(db, os.environ)
            db.commit()
    print("Database migrations complete. " + result, flush=True)
    # Do not leave bootstrap credentials in the serving process or PDF subprocesses.
    for key in BOOTSTRAP_KEYS:
        os.environ.pop(key, None)
    get_engine().dispose()


def main():
    config.validate_runtime()
    if not (config.FRONTEND_DIST / "index.html").is_file() or not (config.FRONTEND_DIST / "assets").is_dir():
        raise ValueError("Frontend build is missing. Run npm ci and npm run build in frontend first.")
    try:
        port = int(os.getenv("PORT", "10000"))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise ValueError("PORT must be an integer between 1 and 65535.") from None
    prepare_database()
    # Render terminates HTTPS at its reverse proxy. No forwarded client IP is trusted:
    # the small demo uses conservative shared per-proxy authentication limits.
    # Per-user chat/upload limits are independent of forwarding headers.
    args = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port),
            "--workers", "1", "--no-proxy-headers", "--limit-concurrency", "16", "--timeout-keep-alive", "5"]
    os.execv(sys.executable, args)


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        sys.exit("Startup stopped: " + str(exc))
    except Exception:
        # Connection errors can include credentials. Keep the hosting log sanitized.
        sys.exit("Startup stopped: database preparation failed. Check the PostgreSQL URI, TLS, access and migrations; no server was started.")
