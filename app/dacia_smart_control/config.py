"""Configuration for Dacia Smart Control, loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Runtime configuration for the app."""

    locale: str
    email: str | None
    password: str | None
    account_id: str | None
    vin: str | None
    credential_file: Path
    app_token: str | None

    @classmethod
    def from_env(cls) -> Config:
        """Build a Config from environment variables."""
        credential_file = os.environ.get(
            "DSC_CREDENTIAL_FILE",
            str(Path.home() / ".dacia-smart-control" / "credential.json"),
        )
        return cls(
            locale=os.environ.get("DSC_LOCALE", "fr_FR"),
            email=os.environ.get("DSC_EMAIL"),
            password=os.environ.get("DSC_PASSWORD"),
            account_id=os.environ.get("DSC_ACCOUNT_ID"),
            vin=os.environ.get("DSC_VIN"),
            credential_file=Path(credential_file),
            app_token=os.environ.get("DSC_APP_TOKEN"),
        )
