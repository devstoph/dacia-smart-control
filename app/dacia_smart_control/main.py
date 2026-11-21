"""FastAPI application exposing dashboard + REST API for the Dacia Spring."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import Depends
from fastapi import FastAPI
from fastapi import Header
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pydantic import Field

from .config import Config
from .service import RenaultService

STATIC_DIR = Path(__file__).parent / "static"

OK_STATUS_CODE = 200


class HvacStartRequest(BaseModel):
    temperature: float = Field(default=21.0, ge=15, le=25)


def create_app(config: Config | None = None, service: Any | None = None) -> FastAPI:
    """Create the FastAPI app.

    `service` allows injecting a mock for testing; production builds
    a real RenaultService lazily.
    """
    config = config or Config.from_env()
    app = FastAPI(
        title="Dacia Smart Control",
        description=(
            "Control and monitor a Dacia Spring EV: battery and charging "
            "status, HVAC pre-conditioning, horn/lights and location."
        ),
        version="1.0.0",
        docs_url="/docs",
    )
    lifecycle: dict[str, RenaultService] = {}

    def get_service() -> Any:
        if service is not None:
            return service
        if "service" not in lifecycle:
            lifecycle["service"] = RenaultService(config)
        return lifecycle["service"]

    async def check_token(x_app_token: str | None = Header(default=None)) -> None:
        expected = config.app_token
        if expected and x_app_token != expected:
            raise HTTPException(status_code=401, detail="Invalid app token")

    _register_system_routes(app)
    _register_vehicle_routes(app, get_service, check_token)
    _register_action_routes(app, get_service, check_token)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


def _register_system_routes(app: FastAPI) -> None:
    """Serve the dashboard, PWA assets and health check."""

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/manifest.webmanifest", include_in_schema=False)
    async def manifest() -> FileResponse:
        return FileResponse(STATIC_DIR / "manifest.webmanifest")

    @app.get("/sw.js", include_in_schema=False)
    async def service_worker() -> FileResponse:
        return FileResponse(STATIC_DIR / "sw.js")

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, Any]:
        return {"status": "ok"}


def _register_vehicle_routes(app: FastAPI, get_service: Any, check_token: Any) -> None:
    """Register read-only vehicle data routes."""

    @app.get("/api/status", tags=["vehicle"], summary="Vehicle status")
    async def status(_: None = Depends(check_token)) -> dict[str, Any]:
        return await get_service().status()

    @app.get("/api/vehicle", tags=["vehicle"], summary="Vehicle details")
    async def vehicle_details(_: None = Depends(check_token)) -> dict[str, Any]:
        return await get_service().vehicle_details()

    @app.get("/api/charge/schedule", tags=["charging"], summary="Get charge schedule")
    async def charge_schedule(_: None = Depends(check_token)) -> dict[str, Any]:
        return await get_service().charge_schedule()


def _register_action_routes(app: FastAPI, get_service: Any, check_token: Any) -> None:
    """Register vehicle control routes."""

    @app.post("/api/charge/start", tags=["charging"], summary="Start charging now")
    async def charge_start(_: None = Depends(check_token)) -> dict[str, Any]:
        return await get_service().charge_start()

    @app.post("/api/hvac/start", tags=["hvac"], summary="Start pre-conditioning")
    async def hvac_start(
        request: HvacStartRequest, _: None = Depends(check_token)
    ) -> dict[str, Any]:
        return await get_service().hvac_start(request.temperature)

    @app.post("/api/hvac/stop", tags=["hvac"], summary="Stop pre-conditioning")
    async def hvac_stop(_: None = Depends(check_token)) -> dict[str, Any]:
        return await get_service().hvac_stop()

    @app.post("/api/horn", tags=["actions"], summary="Sound the horn")
    async def horn(_: None = Depends(check_token)) -> dict[str, Any]:
        return await get_service().horn()

    @app.post("/api/lights", tags=["actions"], summary="Flash the lights")
    async def lights(_: None = Depends(check_token)) -> dict[str, Any]:
        return await get_service().lights()

    @app.post("/api/location/refresh", tags=["actions"], summary="Refresh GPS position")
    async def refresh_location(_: None = Depends(check_token)) -> dict[str, Any]:
        return await get_service().refresh_location()


@lru_cache(maxsize=1)
def get_app() -> FastAPI:
    """Return the singleton production app (uvicorn entry point)."""
    return create_app()
