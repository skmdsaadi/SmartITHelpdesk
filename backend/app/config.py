"""Environment settings. Secrets stay in backend/.env, never in frontend code."""
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
if os.getenv("APP_ENV") != "production" and os.getenv("RENDER") != "true":
    load_dotenv(BACKEND_DIR / ".env", override=False)
APP_ENV = os.getenv("APP_ENV", "production" if os.getenv("RENDER") == "true" else "development")
PRODUCTION = APP_ENV == "production"
DATABASE_URL = os.getenv("DATABASE_URL", "")


def allowed_origins(environ, production):
    default = "" if production else (
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4173,"
        "http://localhost:4173,http://127.0.0.1:8000"
    )
    origins = {item.strip().rstrip("/") for item in environ.get("ALLOWED_ORIGINS", default).split(",") if item.strip()}
    if production and environ.get("RENDER_EXTERNAL_URL"):
        origins.add(environ["RENDER_EXTERNAL_URL"].rstrip("/"))
    if production:
        if not origins:
            raise ValueError("Set ALLOWED_ORIGINS to the public HTTPS origin, or use RENDER_EXTERNAL_URL.")
        for origin in origins:
            parsed = urlsplit(origin)
            if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                    or parsed.path or parsed.query or parsed.fragment or "*" in origin):
                raise ValueError("Production allowed origins must be exact HTTPS origins without paths or wildcards.")
    return origins


ALLOWED_ORIGINS = allowed_origins(os.environ, PRODUCTION)
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true" if PRODUCTION else "false").lower() == "true"
SESSION_HOURS = max(1, min(24, int(os.getenv("SESSION_HOURS", "12"))))
ALLOW_REGISTRATION = os.getenv("ALLOW_REGISTRATION", "true").lower() == "true"
COOKIE_NAME = "helpdesk_session"
FRONTEND_DIST = Path(os.getenv("FRONTEND_DIST", str(BACKEND_DIR.parent / "frontend" / "dist"))).resolve()


def validate_runtime():
    if APP_ENV not in {"development", "production"}:
        raise ValueError("APP_ENV must be development or production.")
    if PRODUCTION:
        if not COOKIE_SECURE:
            raise ValueError("Production requires COOKIE_SECURE=true.")
        from sqlalchemy.engine import make_url
        try:
            url = make_url(DATABASE_URL)
        except Exception:
            raise ValueError("Set DATABASE_URL to a PostgreSQL connection URI.") from None
        if url.get_backend_name() != "postgresql" or not url.host or not url.database:
            raise ValueError("Production requires a PostgreSQL host and database.")
        if url.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
            raise ValueError("Production DATABASE_URL must require TLS (sslmode=require or verify-full).")
