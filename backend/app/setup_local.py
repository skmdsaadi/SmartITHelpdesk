"""Interactive local setup; PostgreSQL's administrator password is never saved."""
import getpass
import os
from pathlib import Path
import secrets
import sys

import psycopg
from psycopg import sql
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def provision_local():
    if ENV_PATH.exists():
        print("Existing backend/.env found. Keeping its settings.")
        return
    print("Connect to PostgreSQL installed on this computer.")
    host = "127.0.0.1"
    port = input("PostgreSQL port [5432]: ").strip() or "5432"
    if not port.isdigit() or not 1 <= int(port) <= 65535:
        raise ValueError("Enter a valid port number.")
    password = getpass.getpass("PostgreSQL postgres password: ")
    role, database = "helpdesk_app", "smart_it_helpdesk"
    app_password = secrets.token_urlsafe(32)
    try:
        connection = psycopg.connect(host=host, port=port, dbname="postgres", user="postgres",
                                    password=password, connect_timeout=5, autocommit=True)
    except psycopg.Error:
        raise RuntimeError("Cannot connect. Check PostgreSQL service, port and postgres password.") from None
    del password
    with connection:
        role_exists = connection.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone()
        db_exists = connection.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,)).fetchone()
        if role_exists or db_exists:
            raise RuntimeError("helpdesk_app or smart_it_helpdesk already exists but .env is missing. "
                               "Restore your .env backup before continuing. Existing data was not changed.")
        connection.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE").format(
            sql.Identifier(role), sql.Literal(app_password)))
        try:
            connection.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(
                sql.Identifier(database), sql.Identifier(role)))
        except psycopg.Error:
            connection.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
            raise RuntimeError("Database creation failed. No existing database was changed.") from None
        connection.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))
    url = URL.create("postgresql+psycopg", username=role, password=app_password,
                     host=host, port=int(port), database=database)
    text = "DATABASE_URL=" + url.render_as_string(hide_password=False) + "\n"
    text += "ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:4173,http://localhost:4173,http://127.0.0.1:8000\n"
    text += "COOKIE_SECURE=false\nSESSION_HOURS=12\nALLOW_REGISTRATION=true\n"
    with ENV_PATH.open("x", encoding="utf-8", newline="\n") as file:
        file.write(text)
    if os.name != "nt":
        ENV_PATH.chmod(0o600)
    print("Database and dedicated application account created. Settings saved in backend/.env.")


def main():
    provision_local()
    # Local setup must use this project's file, even if the shell has another
    # project's DATABASE_URL in its environment. Production still uses env vars.
    from dotenv import dotenv_values
    local_values = dotenv_values(ENV_PATH)
    if not local_values.get("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is missing from backend/.env.")
    for key, value in local_values.items():
        if value is not None:
            os.environ[key] = value
    from alembic import command
    from alembic.config import Config
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")
    print("Database migrations complete.")
    from .create_admin import main as create_admin
    create_admin(only_if_missing=True)
    print("Setup complete. Start the backend and frontend.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        sys.exit("Setup cancelled. Run the command again to continue.")
    except (RuntimeError, ValueError) as exc:
        sys.exit(str(exc))
    except Exception:
        sys.exit("Setup could not finish. Check PostgreSQL and the settings in backend/.env. "
                 "Do not share the DATABASE_URL password.")
