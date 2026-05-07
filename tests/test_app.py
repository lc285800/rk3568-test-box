from fastapi.testclient import TestClient

from board_agent.app import create_app
from board_agent.config import Settings


def make_client() -> TestClient:
    app = create_app(Settings(mode="mock"))
    return TestClient(app)


def test_health_system_and_resources_endpoints():
    client = make_client()

    assert client.get("/api/health").status_code == 200
    assert client.get("/api/system").status_code == 200
    resources = client.get("/api/resources")

    assert resources.status_code == 200
    assert resources.json()["mode"] == "mock"


def test_create_dry_run_task():
    client = make_client()

    response = client.post(
        "/api/tasks",
        json={"interface": "demo", "action": "ping", "params": {}, "dry_run": True},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "queued"
