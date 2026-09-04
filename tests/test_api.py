import pytest
from fastapi.testclient import TestClient

from halberd.server.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    import halberd.server.app as app_module
    monkeypatch.setenv("HALBERD_DATA_DIR", str(tmp_path))
    app_module._engine = None
    app_module._session_factory = None
    app = create_app()
    return TestClient(app)


class TestAPI:
    def test_dashboard(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Halberd BAS" in resp.text

    def test_list_techniques(self, client):
        resp = client.get("/api/library/techniques")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 15
        assert any(t["id"] == "T1082" for t in data)

    def test_get_technique(self, client):
        resp = client.get("/api/library/techniques/T1082")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "System Information Discovery"

    def test_get_missing_technique(self, client):
        resp = client.get("/api/library/techniques/T9999")
        assert resp.status_code == 404

    def test_list_chains(self, client):
        resp = client.get("/api/library/chains")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3

    def test_list_agents(self, client):
        resp = client.get("/api/agents/")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_register_agent(self, client):
        resp = client.post("/api/agents/register", json={
            "agent_id": "test123",
            "hostname": "test-host",
            "os": "linux",
        })
        assert resp.status_code == 200
        assert resp.json()["agent_id"] == "test123"

    def test_create_campaign(self, client):
        resp = client.post("/api/campaigns", json={
            "name": "Test Campaign",
            "campaign_type": "technique",
            "target_ids": ["T1082"],
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Campaign"

    def test_list_campaigns(self, client):
        resp = client.get("/api/campaigns")
        assert resp.status_code == 200

    def test_coverage_empty(self, client):
        resp = client.get("/api/results/coverage")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 15
        assert all(not e["tested"] for e in data)

    def test_library_page(self, client):
        resp = client.get("/library")
        assert resp.status_code == 200
        assert "T1082" in resp.text

    def test_import_page(self, client):
        resp = client.get("/import")
        assert resp.status_code == 200
        assert "Import" in resp.text

    def test_cleanup_check_only(self, client):
        resp = client.post("/api/library/cleanup", json={
            "technique_id": "T1082",
            "check_only": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "checked"
        assert "actions" in data

    def test_cleanup_all(self, client):
        resp = client.post("/api/library/cleanup", json={"all": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cleaned"
        assert len(data["actions"]) >= 15

    def test_cleanup_requires_target(self, client):
        resp = client.post("/api/library/cleanup", json={})
        assert resp.status_code == 400
