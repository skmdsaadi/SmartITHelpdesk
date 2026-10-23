"""Hosting regressions: secrets, bootstrap transactions, cookies and static serving."""
import os
from unittest.mock import Mock, patch
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


def test_render_origin_and_development_defaults():
    from app.config import allowed_origins
    assert allowed_origins({"RENDER_EXTERNAL_URL": "https://helpdesk.onrender.com"}, True) == {"https://helpdesk.onrender.com"}
    assert "http://127.0.0.1:5173" in allowed_origins({}, False)
    assert allowed_origins({"RENDER_EXTERNAL_URL": "https://helpdesk.onrender.com", "ALLOWED_ORIGINS": "https://it.example.com/"}, True) == {
        "https://helpdesk.onrender.com", "https://it.example.com"}


@pytest.mark.parametrize("origin", ["", "*", "http://example.com", "https://example.com/path", "https://user:secret@example.com", "https://*.example.com"])
def test_production_rejects_unsafe_origins(origin):
    from app.config import allowed_origins
    with pytest.raises(ValueError):
        allowed_origins({"ALLOWED_ORIGINS": origin}, True)


def test_production_requires_secure_cookies_and_database_tls(monkeypatch):
    from app import config
    monkeypatch.setattr(config, "APP_ENV", "production")
    monkeypatch.setattr(config, "PRODUCTION", True)
    monkeypatch.setattr(config, "COOKIE_SECURE", False)
    with pytest.raises(ValueError, match="COOKIE_SECURE"):
        config.validate_runtime()
    monkeypatch.setattr(config, "COOKIE_SECURE", True)
    monkeypatch.setattr(config, "DATABASE_URL", "postgresql://demo:secret@db.example.com/helpdesk")
    with pytest.raises(ValueError, match="TLS"):
        config.validate_runtime()
    monkeypatch.setattr(config, "DATABASE_URL", config.DATABASE_URL + "?sslmode=require&channel_binding=require")
    config.validate_runtime()


def test_static_assets_keep_api_and_private_paths_404(tmp_path):
    from app.web import mount_frontend
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>Helpdesk</html>")
    (dist / "assets" / "app-123.js").write_text("console.log('helpdesk')")
    (tmp_path / ".env").write_text("PRIVATE=must-not-be-served")
    app = FastAPI()
    mount_frontend(app, dist)
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert "text/html" in client.get("/").headers["content-type"]
        assert client.head("/").content == b""
        assert client.get("/assets/app-123.js").status_code == 200
        for path in ["/api/v1/missing", "/assets/missing.js", "/.env", "/backend/.env", "/assets/%2e%2e/%2e%2e/.env"]:
            assert client.get(path).status_code == 404


def test_liveness_never_queries_database_or_fits_model():
    from app.main import app
    with patch("app.main.get_engine", side_effect=AssertionError("Must not connect")), patch("app.main.classifier.get_model", side_effect=AssertionError("Must not train")):
        with TestClient(app) as client:
            response = client.get("/healthz")
            assert response.status_code == 200 and response.json()["version"] == "1.0.0"


def test_https_login_uses_secure_cookie_and_exact_origin(app_context, clients, monkeypatch):
    from app import config
    from test_workflow import register
    _, data = register(clients())
    origin = "https://helpdesk.onrender.com"
    monkeypatch.setattr(config, "COOKIE_SECURE", True)
    monkeypatch.setattr(config, "PRODUCTION", True)
    monkeypatch.setattr(config, "ALLOWED_ORIGINS", {origin})
    # Do not invoke production lifespan against the intentionally non-TLS test DB.
    client = TestClient(app_context, base_url=origin, headers={"X-Helpdesk-Request": "1", "Origin": origin})
    try:
        response = client.post("/api/v1/auth/login", json={"email": data["email"], "password": data["password"]})
        assert response.status_code == 200
        cookie = response.headers["set-cookie"]
        assert all(part in cookie for part in ["Secure", "HttpOnly", "SameSite=lax", "Path=/api"])
        assert client.get("/api/v1/auth/me").status_code == 200
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        assert response.headers["strict-transport-security"] == "max-age=31536000"
        assert client.post("/api/v1/auth/logout", headers={"Origin": "https://other.onrender.com"}).status_code == 403
        assert client.post("/api/v1/auth/logout").status_code == 204
    finally:
        client.close()


@pytest.fixture
def startup_database(monkeypatch):
    raw = os.getenv("TEST_DATABASE_URL")
    if not raw:
        pytest.skip("Set TEST_DATABASE_URL to a disposable PostgreSQL database.")
    from app import start
    schema = "helpdesk_start_" + uuid.uuid4().hex
    base_url = make_url(raw).set(drivername="postgresql+psycopg")
    control = create_engine(base_url)
    with control.begin() as conn:
        previous_path = conn.execute(text("SHOW search_path")).scalar()
        conn.execute(text('CREATE SCHEMA "' + schema + '"'))
    engine = create_engine(base_url.update_query_dict({"options": "-csearch_path=" + schema}))
    @event.listens_for(engine, "connect")
    def set_test_schema(connection, _record):
        # Explicit SET also supports test adapters that ignore startup options.
        previous_autocommit = connection.autocommit
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute('SET search_path TO "' + schema + '"')
        connection.autocommit = previous_autocommit
    monkeypatch.setattr(start, "get_engine", lambda: engine)
    for key in start.BOOTSTRAP_KEYS:
        monkeypatch.delenv(key, raising=False)
    yield engine
    engine.dispose()
    with control.begin() as conn:
        conn.execute(text('DROP SCHEMA "' + schema + '" CASCADE'))
        conn.execute(text("SELECT set_config('search_path', :path, false)"), {"path": previous_path})
    control.dispose()


def bootstrap_values(monkeypatch):
    values = {"BOOTSTRAP_ADMIN_NAME": "Deployment Test Admin", "BOOTSTRAP_ADMIN_EMAIL": "deployment@example.com",
              "BOOTSTRAP_ADMIN_PASSWORD": "Example-deployment-test-only!"}
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    return values


def test_startup_migrates_and_never_resets_existing_admin(startup_database, monkeypatch):
    from app.start import prepare_database
    from app.models import User
    from app.security import password_hasher
    values = bootstrap_values(monkeypatch)
    prepare_database()
    with Session(startup_database) as db:
        user = db.scalar(select(User))
        old_hash = user.password_hash
        assert user.role == "admin" and user.email == "deployment@example.com"
        assert password_hasher.verify(values["BOOTSTRAP_ADMIN_PASSWORD"], old_hash)
        assert db.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0003"
    assert not any(key in os.environ for key in values)
    prepare_database()  # Subsequent starts need no bootstrap secrets.
    bootstrap_values(monkeypatch)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "Different-example-test-password!")
    prepare_database()
    with Session(startup_database) as db:
        assert db.scalar(select(User)).password_hash == old_hash
        assert len(db.scalars(select(User)).all()) == 1


def test_missing_or_invalid_bootstrap_rolls_back_migrations(startup_database, monkeypatch):
    from app.start import prepare_database
    with pytest.raises(ValueError, match="First deployment"):
        prepare_database()
    assert inspect(startup_database).get_table_names() == []
    bootstrap_values(monkeypatch)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "weak")
    with pytest.raises(ValueError) as error:
        prepare_database()
    assert "weak" not in str(error.value)
    assert inspect(startup_database).get_table_names() == []


def test_bootstrap_cannot_promote_existing_employee(startup_database, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from app import config
    from app.models import User
    from app.start import prepare_database
    with startup_database.begin() as connection:
        migration = Config(str(config.BACKEND_DIR / "alembic.ini"))
        migration.attributes["connection"] = connection
        command.upgrade(migration, "head")
    with Session(startup_database) as db:
        db.add(User(name="Existing Employee", email="deployment@example.com", password_hash="unchanged", role="employee"))
        db.commit()
    bootstrap_values(monkeypatch)
    with pytest.raises(ValueError, match="No password or role"):
        prepare_database()
    with Session(startup_database) as db:
        user = db.scalar(select(User))
        assert user.role == "employee" and user.password_hash == "unchanged"


def test_failed_preparation_cannot_start_server(tmp_path, monkeypatch):
    from app import start
    (tmp_path / "index.html").write_text("<html></html>")
    (tmp_path / "assets").mkdir()
    monkeypatch.setattr(start.config, "FRONTEND_DIST", tmp_path)
    monkeypatch.setattr(start, "prepare_database", Mock(side_effect=ValueError("Preparation failed")))
    execute = Mock()
    monkeypatch.setattr(start.os, "execv", execute)
    with pytest.raises(ValueError, match="Preparation failed"):
        start.main()
    execute.assert_not_called()
