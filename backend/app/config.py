"""Environment settings. Secrets stay in backend/.env, never in frontend code."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=False)
DATABASE_URL = os.getenv("DATABASE_URL", "")
ALLOWED_ORIGINS = {
    item.strip().rstrip("/")
    for item in os.getenv(
        "ALLOWED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4173,"
        "http://localhost:4173,http://127.0.0.1:8000",
    ).split(",") if item.strip()
}
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
SESSION_HOURS = max(1, min(24, int(os.getenv("SESSION_HOURS", "12"))))
ALLOW_REGISTRATION = os.getenv("ALLOW_REGISTRATION", "true").lower() == "true"
COOKIE_NAME = "helpdesk_session"
