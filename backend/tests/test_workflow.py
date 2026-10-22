from datetime import timedelta
from unittest.mock import patch
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

PASSWORD = "Example-only-test-passphrase!"

def register(client, **overrides):
    data = {"name": "Test Employee", "email": uuid.uuid4().hex + "@example.com", "password": PASSWORD}
    data.update(overrides)
    response = client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 201, response.text
    return response.json(), data

def admin_client(clients):
    from app.database import get_engine
    from app.models import User
    from app.security import password_hasher
    email = uuid.uuid4().hex + "@example.com"
    with Session(get_engine()) as db:
        db.add(User(name="Test Administrator", email=email, role="admin", password_hash=password_hasher.hash(PASSWORD)))
        db.commit()
    client = clients()
    response = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return client

def ticket(client, **overrides):
    data = {"title": "Office Wi-Fi disconnected", "description": "The office Wi-Fi disconnects every ten minutes.",
            "category": "Network", "priority": "High"}
    data.update(overrides)
    response = client.post("/api/v1/tickets", json=data)
    assert response.status_code == 201, response.text
    return response.json()

def test_registration_cookie_password_and_logout(clients):
    from app.database import get_engine
    from app.models import AuthSession, User
    from app.security import token_hash
    client = clients()
    user, data = register(client)
    assert user["role"] == "employee" and "password_hash" not in user
    token = client.cookies.get("helpdesk_session")
    with Session(get_engine()) as db:
        stored = db.get(User, user["id"])
        assert stored.password_hash.startswith("$argon2id$") and stored.password_hash != PASSWORD
        assert db.get(AuthSession, token_hash(token)) is not None
        assert db.get(AuthSession, token) is None
    login = client.post("/api/v1/auth/login", json={"email": data["email"].upper(), "password": PASSWORD})
    assert login.status_code == 200
    assert "HttpOnly" in login.headers["set-cookie"] and "SameSite=lax" in login.headers["set-cookie"]
    assert client.get("/api/v1/auth/me").json()["id"] == user["id"]
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    client.cookies.set("helpdesk_session", token, path="/api")
    assert client.get("/api/v1/auth/me").status_code == 401

def test_duplicate_registration_and_no_public_admin_role(clients):
    client = clients()
    _, data = register(client)
    assert client.post("/api/v1/auth/register", json={**data, "email": data["email"].upper()}).status_code == 409
    assert client.post("/api/v1/auth/register", json={**data, "role": "admin"}).status_code == 422
    bad = client.post("/api/v1/auth/login", json={"email": data["email"], "password": "wrong"})
    assert bad.status_code == 401 and "incorrect" in bad.json()["detail"]

def test_employee_isolation_and_access_controls(clients):
    a, b = clients(), clients()
    register(a); register(b)
    t = ticket(a)
    ticket(b, title="Private printer problem", category="Printer")
    assert a.get("/api/v1/tickets").json()["total"] == 1
    assert b.get("/api/v1/tickets/" + str(t["id"])).status_code == 404
    assert b.post("/api/v1/tickets/" + str(t["id"]) + "/comments", json={"body": "Should be denied"}).status_code == 404
    update = {"status": "Resolved", "category": "Network", "priority": "High", "version": t["version"]}
    assert a.patch("/api/v1/tickets/" + str(t["id"]), json=update).status_code == 403
    assert a.get("/api/v1/dashboard").json()["total"] == 1
    assert clients().get("/api/v1/tickets").status_code == 401

def test_admin_workflow_comments_history_and_stale_edits(clients):
    employee = clients(); register(employee)
    t = ticket(employee)
    admin = admin_client(clients)
    url = "/api/v1/tickets/" + str(t["id"])
    update = {"status": "In Progress", "category": "Network", "priority": "High", "version": t["version"]}
    result = admin.patch(url, json=update)
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "In Progress"
    assert admin.patch(url, json=update).status_code == 409
    assert employee.post(url + "/comments", json={"body": "The issue still happens."}).status_code == 201
    assert admin.post(url + "/comments", json={"body": "Please reconnect and test again."}).status_code == 201
    resolved = admin.patch(url, json={**update, "status": "Resolved", "version": result.json()["version"]})
    assert resolved.status_code == 200 and resolved.json()["resolved_at"]
    detail = employee.get(url).json()
    assert len(detail["comments"]) == 2 and len(detail["events"]) == 3
    assert employee.get("/api/v1/dashboard").json()["resolved"] == 1
    reopened = admin.patch(url, json={**update, "status": "Open", "version": resolved.json()["version"]})
    assert reopened.status_code == 200 and reopened.json()["resolved_at"] is None

def test_filters_search_validation_and_pagination(clients):
    client = clients(); register(client)
    ticket(client, title="Printer shows 100% error", category="Printer", priority="Low")
    ticket(client, title="Office login is unavailable", category="Access")
    assert client.get("/api/v1/tickets?category=Printer").json()["total"] == 1
    assert client.get("/api/v1/tickets?priority=High").json()["total"] == 1
    assert client.get("/api/v1/tickets?search=%25").json()["total"] == 1  # literal wildcard
    page = client.get("/api/v1/tickets?page_size=1&page=2").json()
    assert page["total"] == 2 and len(page["items"]) == 1
    for query in ["status=Unknown", "page=0", "page_size=51"]:
        assert client.get("/api/v1/tickets?" + query).status_code == 422
    assert client.post("/api/v1/tickets", json={"title": "      ", "description": " " * 30, "category": "Network"}).status_code == 422
    assert client.post("/api/v1/tickets", json={"title": "Valid title", "description": "A valid description for a test", "category": "Network", "created_by": 1}).status_code == 422

def test_csrf_origin_and_header_protection(clients):
    client = clients()
    payload = {"email": "user@example.com", "password": PASSWORD}
    assert client.post("/api/v1/auth/login", json=payload, headers={"X-Helpdesk-Request": ""}).status_code == 403
    assert client.post("/api/v1/auth/login", json=payload, headers={"Origin": "https://untrusted.example"}).status_code == 403
    assert client.post("/api/v1/auth/login", json=payload, headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403

def test_expired_and_inactive_sessions(clients):
    from app.database import get_engine
    from app.models import AuthSession, User, utcnow
    from app.security import token_hash
    client = clients(); user, data = register(client)
    with Session(get_engine()) as db:
        session = db.get(AuthSession, token_hash(client.cookies.get("helpdesk_session")))
        session.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": data["email"], "password": PASSWORD}).status_code == 200
    with Session(get_engine()) as db:
        db.get(User, user["id"]).is_active = False
        db.commit()
    assert client.get("/api/v1/auth/me").status_code == 401

def test_health_and_login_throttle(clients):
    client = clients()
    response = client.get("/api/v1/health")
    assert response.status_code == 200 and response.json()["components"]["database"] == "ready"
    assert response.json()["components"]["ai"] == "ready_demo"
    assert response.headers["cache-control"] == "no-store"
    # Skip expensive Argon2 work here: this test specifically exercises the limiter.
    with patch("app.main.password_hasher.verify", return_value=False):
        for _ in range(20):
            assert client.post("/api/v1/auth/login", json={"email": "missing@example.com", "password": PASSWORD}).status_code == 401
        assert client.post("/api/v1/auth/login", json={"email": "missing@example.com", "password": PASSWORD}).status_code == 429

def test_second_app_instance_reads_persisted_ticket(clients, app_context):
    from fastapi.testclient import TestClient
    creator = clients(); register(creator)
    t = ticket(creator)
    with TestClient(app_context, cookies=dict(creator.cookies), headers={"X-Helpdesk-Request": "1"}) as another:
        detail = another.get("/api/v1/tickets/" + str(t["id"]))
        assert detail.status_code == 200 and detail.json()["title"] == t["title"]

def test_migration_model_alignment(app_context):
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext
    from app.database import get_engine
    from app.models import Base
    with get_engine().connect() as conn:
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []
