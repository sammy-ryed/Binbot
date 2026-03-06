"""Application configuration — loads credentials from a .env file."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _load_env() -> None:
    """Load the nearest .env file (silently succeeds if it doesn't exist)."""
    load_dotenv(_ENV_PATH)


@dataclass
class Config:
    api_key: str
    api_secret: str
    base_url: str = field(default="https://testnet.binancefuture.com")

    @classmethod
    def from_env(cls) -> "Config":
        """Build a Config from environment variables (reads .env automatically).

        Raises:
            EnvironmentError: if BINANCE_API_KEY or BINANCE_API_SECRET are missing.
        """
        _load_env()

        api_key = os.getenv("BINANCE_API_KEY", "").strip()
        api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
        base_url = os.getenv(
            "BINANCE_BASE_URL", "https://testnet.binancefuture.com"
        ).strip()

        missing = [
            name
            for name, val in (
                ("BINANCE_API_KEY", api_key),
                ("BINANCE_API_SECRET", api_secret),
            )
            if not val
        ]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variable(s): {', '.join(missing)}.\n"
                "Copy .env.example → .env and fill in your Binance Testnet credentials."
            )

        return cls(api_key=api_key, api_secret=api_secret, base_url=base_url)
