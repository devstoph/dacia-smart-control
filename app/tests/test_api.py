"""Tests for the Dacia Smart Control API layer (mocked vehicle service)."""

# ruff: noqa: PLR2004

from __future__ import annotations

from typing import Any

import pytest
from dacia_smart_control.config import Config
from dacia_smart_control.main import create_app
from fastapi.testclient import TestClient

FAKE_STATUS: dict[str, Any] = {
    "battery": {
        "batteryLevel": 64,
        "batteryAutonomy": 145,
        "plugStatus": 1,
        "chargingStatus": 1,
        "chargingRemainingTime": 75,
    },
    "cockpit": {"totalMileage": 1234.5},
    "hvac": {"hvacStatus": "off", "externalTemperature": 12.5},
    "location": {"gpsLatitude": 48.85, "gpsLongitude": 2.35},
}


class FakeService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.hvac_temperature: float | None = None

    async def status(self) -> dict[str, Any]:
        return FAKE_STATUS

    async def charge_start(self) -> dict[str, Any]:
        self.calls.append(("charge_start", None))
        return {"chargeStartImpact": "Start"}

    async def hvac_start(self, temperature: float) -> dict[str, Any]:
        self.hvac_temperature = temperature
        self.calls.append(("hvac_start", temperature))
        return {"action": "start"}

    async def hvac_stop(self) -> dict[str, Any]:
        self.calls.append(("hvac_stop", None))
        return {"action": "cancel"}

    async def horn(self) -> dict[str, Any]:
        self.calls.append(("horn", None))
        return {"status": "ok"}

    async def lights(self) -> dict[str, Any]:
        self.calls.append(("lights", None))
        return {"status": "ok"}

    async def refresh_location(self) -> dict[str, Any]:
        self.calls.append(("refresh_location", None))
        return {"status": "ok"}

    async def charge_schedule(self) -> dict[str, Any]:
        return {"schedules": []}

    async def vehicle_details(self) -> dict[str, Any]:
        return {"vin": "VF1AAAAA555777999", "model": {"label": "SPRING"}}


@pytest.fixture(name="client")
def client_fixture() -> TestClient:
    fake = FakeService()
    config = Config(
        locale="fr_FR",
        email=None,
        password=None,
        account_id=None,
        vin=None,
        credential_file=None,  # type: ignore[arg-type]
        app_token=None,
    )
    app = create_app(config=config, service=fake)
    return TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Dacia Spring" in response.text


def test_manifest_and_sw(client: TestClient) -> None:
    assert client.get("/manifest.webmanifest").status_code == 200
    assert client.get("/sw.js").status_code == 200


def test_status(client: TestClient) -> None:
    response = client.get("/api/status")
    assert response.status_code == 200
    body = response.json()
    assert body["battery"]["batteryLevel"] == 64
    assert body["cockpit"]["totalMileage"] == 1234.5


def test_openapi_schema(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in (
        "/api/status",
        "/api/charge/start",
        "/api/hvac/start",
        "/api/hvac/stop",
        "/api/horn",
        "/api/lights",
    ):
        assert path in paths


def test_charge_start(client: TestClient) -> None:
    response = client.post("/api/charge/start")
    assert response.status_code == 200


def test_hvac_start_and_stop(client: TestClient) -> None:
    response = client.post("/api/hvac/start", json={"temperature": 22})
    assert response.status_code == 200
    response = client.post("/api/hvac/stop")
    assert response.status_code == 200


def test_hvac_start_validation(client: TestClient) -> None:
    response = client.post("/api/hvac/start", json={"temperature": 30})
    assert response.status_code == 422


def test_horn_and_lights(client: TestClient) -> None:
    assert client.post("/api/horn").status_code == 200
    assert client.post("/api/lights").status_code == 200


def test_refresh_location(client: TestClient) -> None:
    assert client.post("/api/location/refresh").status_code == 200


def test_schedule_and_details(client: TestClient) -> None:
    assert client.get("/api/charge/schedule").status_code == 200
    response = client.get("/api/vehicle")
    assert response.json()["model"]["label"] == "SPRING"


def test_app_token_required() -> None:
    config = Config(
        locale="fr_FR",
        email=None,
        password=None,
        account_id=None,
        vin=None,
        credential_file=None,  # type: ignore[arg-type]
        app_token="secret-token",
    )
    app = create_app(config=config, service=FakeService())
    client = TestClient(app)
    response = client.get("/api/status")
    assert response.status_code == 401
    response = client.get("/api/status", headers={"X-App-Token": "secret-token"})
    assert response.status_code == 200
