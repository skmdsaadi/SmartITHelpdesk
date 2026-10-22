from unittest.mock import patch
from sqlalchemy.orm import Session

from test_workflow import admin_client, register, ticket

DRAFT = {"title": "Office Wi-Fi will not connect", "description": "My laptop cannot connect to the office wireless network. The WiFi connection fails every time."}


def test_ai_auth_validation_and_admin_report(clients):
    anon = clients()
    assert anon.post("/api/v1/ai/classify", json=DRAFT).status_code == 401
    employee = clients(); register(employee)
    assert employee.get("/api/v1/ai/model").status_code == 403
    assert employee.post("/api/v1/ai/classify", json={**DRAFT, "description": " " * 30}).status_code == 422
    assert employee.post("/api/v1/ai/classify", json={**DRAFT, "category": "Network"}).status_code == 422
    assert employee.post("/api/v1/ai/classify", json=DRAFT, headers={"Origin": "https://untrusted.example"}).status_code == 403
    assert employee.post("/api/v1/ai/classify", json=DRAFT, headers={"X-Helpdesk-Request": ""}).status_code == 403
    result = employee.post("/api/v1/ai/classify", json=DRAFT)
    assert result.status_code == 200 and result.json()["suggested_category"] == "Network"
    admin = admin_client(clients)
    report = admin.get("/api/v1/ai/model")
    assert report.status_code == 200 and report.json()["examples"] == 324
    assert report.json()["test"]["count"] == 54


def test_manual_override_and_snapshot_persistence(clients):
    from app.database import get_engine
    from app.models import Ticket
    employee = clients(); register(employee)
    submitted = ticket(employee, **DRAFT, category="Hardware")
    assert submitted["category"] == "Hardware"
    snapshot = submitted["ai_assessment"]
    assert snapshot["suggested_category"] == "Network" and snapshot["selected_category"] == "Hardware"
    assert snapshot["model_version"] and snapshot["recorded_at"]
    # The JSONB data is really persisted, not reconstructed by the response layer.
    with Session(get_engine()) as db:
        assert db.get(Ticket, submitted["id"]).ai_assessment["model_version"] == snapshot["model_version"]
    detail_url = "/api/v1/tickets/" + str(submitted["id"])
    stranger = clients(); register(stranger)
    assert stranger.get(detail_url).status_code == 404
    admin = admin_client(clients)
    changed = admin.patch(detail_url, json={"category": "Network", "priority": "High", "status": "In Progress", "version": 1})
    assert changed.status_code == 200
    assert changed.json()["ai_assessment"] == snapshot
    assert employee.get(detail_url).json()["ai_assessment"] == snapshot
    forged = {**DRAFT, "category": "Network", "ai_assessment": {"suggested_category": "Access"}}
    assert employee.post("/api/v1/tickets", json=forged).status_code == 422


def test_bangla_and_missing_model_do_not_block_tickets(clients):
    employee = clients(); register(employee)
    unsupported = ticket(employee, title="আমার ল্যাপটপে সমস্যা", description="আমার ল্যাপটপে ওয়াইফাই সংযোগ কাজ করছে না।")
    assert unsupported["ai_assessment"]["reason"] == "unsupported_language"
    with patch("app.classifier.get_model", return_value=None):
        manual = ticket(employee, **DRAFT)
        assert manual["ai_assessment"]["reason"] == "unavailable"
        assert employee.get("/api/v1/health").json()["components"]["ai"] == "unavailable"
        admin = admin_client(clients)
        assert admin.get("/api/v1/ai/model").status_code == 503


def test_legacy_ticket_without_snapshot_is_readable(clients):
    from app.database import get_engine
    from app.models import Ticket
    employee = clients(); user, _ = register(employee)
    with Session(get_engine()) as db:
        old = Ticket(title="Existing Phase 2 request", description="This ticket predates the AI classifier.",
                     category="Software", created_by=user["id"], ai_assessment=None)
        db.add(old); db.commit(); old_id = old.id
    response = employee.get("/api/v1/tickets/" + str(old_id))
    assert response.status_code == 200 and response.json()["ai_assessment"] is None
