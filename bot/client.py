"""Binance Futures Testnet REST API client.

Handles:
  - HMAC-SHA256 request signing
  - Authenticated GET / POST requests
  - Response parsing and error normalisation
  - Structured logging of every request and response
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Optional
from urllib.parse import urlencode

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

logger = logging.getLogger("binbot.client")


# ── Custom exceptions ─────────────────────────────────────────────────────────

class BinanceAPIError(Exception):
    """Raised when the Binance API returns a logical error (negative code)."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error [{code}]: {message}")


class BinanceNetworkError(Exception):
    """Raised for transport-level failures (timeout, DNS, connection refused)."""


# ── Client ────────────────────────────────────────────────────────────────────

class BinanceClient:
    """Thin, authenticated wrapper around the Binance Futures USDT-M REST API.

    Usage::

        client = BinanceClient(api_key="...", api_secret="...")
        account = client.get_account()
    """

    RECV_WINDOW: int = 5_000   # ms — tolerance for clock skew
    TIMEOUT: int = 10          # seconds per HTTP request

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://testnet.binancefuture.com",
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self.base_url = base_url.rstrip("/")

        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self._api_key})

    # ── Signing helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1_000)

    def _sign(self, params: dict[str, Any]) -> str:
        """Return HMAC-SHA256 hex digest of the URL-encoded parameter string."""
        payload = urlencode(params)
        return hmac.new(
            self._api_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _inject_auth(self, params: dict[str, Any]) -> dict[str, Any]:
        """Return a *new* dict with timestamp, recvWindow, and signature appended."""
        signed: dict[str, Any] = dict(params)
        signed["timestamp"] = self._now_ms()
        signed["recvWindow"] = self.RECV_WINDOW
        signed["signature"] = self._sign(signed)
        return signed

    # ── Response parsing ──────────────────────────────────────────────────────

    @staticmethod
    def _parse_response(response: requests.Response) -> dict[str, Any]:
        """Parse the response body; raise BinanceAPIError on any error shape."""
        try:
            data: Any = response.json()
        except ValueError:
            raise BinanceAPIError(
                -1,
                f"Non-JSON response (HTTP {response.status_code}): {response.text[:300]}",
            )

        # Binance error envelope: {"code": <negative_int>, "msg": "..."}
        if (
            isinstance(data, dict)
            and isinstance(data.get("code"), int)
            and data["code"] < 0
        ):
            raise BinanceAPIError(data["code"], data.get("msg", "Unknown API error"))

        if not response.ok:
            msg = (
                data.get("msg", response.reason)
                if isinstance(data, dict)
                else response.reason
            )
            raise BinanceAPIError(response.status_code, str(msg))

        return data  # type: ignore[return-value]

    # ── HTTP verbs ────────────────────────────────────────────────────────────

    def get(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
        signed: bool = False,
    ) -> dict[str, Any]:
        """Perform a GET request, optionally signed."""
        p: dict[str, Any] = dict(params or {})
        if signed:
            p = self._inject_auth(p)

        url = f"{self.base_url}{endpoint}"
        logger.debug("GET  %s  params=%s", url, _mask(p))

        try:
            resp = self._session.get(url, params=p, timeout=self.TIMEOUT)
        except Timeout:
            raise BinanceNetworkError(f"Request timed out: GET {url}")
        except ConnectionError as exc:
            raise BinanceNetworkError(f"Connection error: {exc}")
        except RequestException as exc:
            raise BinanceNetworkError(f"Request failed: {exc}")

        data = self._parse_response(resp)
        logger.debug("GET  %s  → HTTP %s", url, resp.status_code)
        return data

    def post(
        self,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Perform a signed POST request (parameters sent as form body)."""
        p = self._inject_auth(dict(params or {}))

        url = f"{self.base_url}{endpoint}"
        logger.info(
            "POST %s  params=%s",
            url,
            _mask(p),
        )

        try:
            resp = self._session.post(
                url,
                data=p,
                timeout=self.TIMEOUT,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except Timeout:
            raise BinanceNetworkError(f"Request timed out: POST {url}")
        except ConnectionError as exc:
            raise BinanceNetworkError(f"Connection error: {exc}")
        except RequestException as exc:
            raise BinanceNetworkError(f"Request failed: {exc}")

        data = self._parse_response(resp)
        logger.info(
            "POST %s  → HTTP %s  orderId=%s  status=%s",
            url,
            resp.status_code,
            data.get("orderId", "N/A"),
            data.get("status", "N/A"),
        )
        return data

    # ── Domain helpers ────────────────────────────────────────────────────────

    def get_account(self) -> dict[str, Any]:
        """Fetch USDT-M futures account info (wallet balances + positions)."""
        return self.get("/fapi/v2/account", signed=True)

    def get_exchange_info(self, symbol: Optional[str] = None) -> dict[str, Any]:
        """Fetch exchange trading rules, optionally filtered by symbol."""
        p: dict[str, Any] = {}
        if symbol:
            p["symbol"] = symbol.upper()
        return self.get("/fapi/v1/exchangeInfo", params=p)


# ── Internal utilities ────────────────────────────────────────────────────────

def _mask(params: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of params with the HMAC signature redacted for safe logging."""
    out = dict(params)
    if "signature" in out:
        out["signature"] = "***REDACTED***"
    return out
