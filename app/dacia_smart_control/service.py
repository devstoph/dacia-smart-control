"""Async service wrapping renault-api for a single Dacia Spring."""

from __future__ import annotations

import json
from dataclasses import fields
from typing import Any

import aiohttp

from .config import Config
from renault_api.renault_client import RenaultClient
from renault_api.renault_vehicle import RenaultVehicle


def _to_dict(data: Any) -> dict[str, Any]:
    """Convert a renault-api dataclass to a plain dict."""
    if data is None:
        return {}
    if hasattr(data, "raw_data"):
        return dict(data.raw_data or {})
    try:
        return {f.name: getattr(data, f.name) for f in fields(data)}
    except TypeError:
        return {}


class RenaultService:
    """Manages the connection to the Renault/Dacia API for one vehicle."""

    def __init__(self, config: Config) -> None:
        """Initialize the service."""
        self._config = config
        self._websession: aiohttp.ClientSession | None = None
        self._vehicle: RenaultVehicle | None = None

    async def close(self) -> None:
        """Release the underlying aiohttp session."""
        if self._websession:
            await self._websession.close()
            self._websession = None

    async def _get_vehicle(self) -> RenaultVehicle:
        """Log in (if needed) and return the API vehicle object."""
        if self._vehicle:
            return self._vehicle
        self._websession = aiohttp.ClientSession()
        client = RenaultClient(websession=self._websession, locale=self._config.locale)
        credential_file = self._config.credential_file
        if credential_file.is_file() and self._config.password is None:
            credential = json.loads(credential_file.read_text())
            client.session.set_login_token(credential["login_token"])
            self._config.account_id = credential.get("account_id")
            self._config.vin = credential.get("vin") or self._config.vin
        elif self._config.email and self._config.password:
            await client.session.login(self._config.email, self._config.password)
        else:
            raise RuntimeError(
                "No credentials available: set DSC_EMAIL and DSC_PASSWORD "
                "for the first run, or point DSC_CREDENTIAL_FILE at a saved "
                "credential file."
            )
        account_id = self._config.account_id
        if not account_id:
            person = await client.get_person()
            account_id = person.accounts[0].accountId
        account = await client.get_api_account(account_id)
        vin = self._config.vin
        if not vin:
            vehicles = await account.get_vehicles()
            vin = vehicles.vehicleLinks[0].vin
        self._vehicle = await account.get_api_vehicle(vin)
        if client.session.login_token:
            credential_file.parent.mkdir(parents=True, exist_ok=True)
            credential_file.write_text(
                json.dumps(
                    {
                        "login_token": client.session.login_token,
                        "account_id": account_id,
                        "vin": vin,
                    }
                )
            )
        return self._vehicle

    async def status(self) -> dict[str, Any]:
        """Return battery, cockpit, hvac and location data for the vehicle."""
        vehicle = await self._get_vehicle()
        return {
            "battery": _to_dict(await vehicle.get_battery_status()),
            "cockpit": _to_dict(await vehicle.get_cockpit()),
            "hvac": _to_dict(await vehicle.get_hvac_status()),
            "location": _to_dict(await vehicle.get_location()),
        }

    async def charge_start(self) -> dict[str, Any]:
        """Start charging immediately."""
        vehicle = await self._get_vehicle()
        result = await vehicle.set_charge_start()
        return _to_dict(result)

    async def hvac_start(self, temperature: float) -> dict[str, Any]:
        """Start HVAC (pre-conditioning) at the given temperature."""
        vehicle = await self._get_vehicle()
        result = await vehicle.set_ac_start(temperature)
        return _to_dict(result)

    async def hvac_stop(self) -> dict[str, Any]:
        """Stop HVAC."""
        vehicle = await self._get_vehicle()
        result = await vehicle.set_ac_stop()
        return _to_dict(result)

    async def horn(self) -> dict[str, Any]:
        """Sound the horn."""
        vehicle = await self._get_vehicle()
        return dict(await vehicle.start_horn())

    async def lights(self) -> dict[str, Any]:
        """Flash the lights."""
        vehicle = await self._get_vehicle()
        return dict(await vehicle.start_lights())

    async def refresh_location(self) -> dict[str, Any]:
        """Ask the vehicle to report its current GPS position."""
        vehicle = await self._get_vehicle()
        return dict(await vehicle.refresh_location())

    async def charge_schedule(self) -> dict[str, Any]:
        """Return the current charge schedule."""
        vehicle = await self._get_vehicle()
        return dict(await vehicle.get_charge_schedule())

    async def vehicle_details(self) -> dict[str, Any]:
        """Return vehicle details (model, VIN, ...)."""
        vehicle = await self._get_vehicle()
        return _to_dict(await vehicle.get_details())
