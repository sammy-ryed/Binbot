"""Order placement logic for BinBot.

Provides:
  - ``OrderResult``   — structured dataclass for API responses
  - ``OrderManager``  — high-level interface with convenience methods
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from .client import BinanceAPIError, BinanceClient, BinanceNetworkError
from .validators import ValidationError, validate_order_params

logger = logging.getLogger("binbot.orders")

# Friendly type names → Binance API type values
# (Binance uses "STOP" for what is commonly called a stop-limit order)
_API_TYPE_MAP: dict[str, str] = {
    "STOP_LIMIT": "STOP",
}


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class OrderResult:
    """Holds the outcome of an order request — successful or not."""

    success: bool

    # Populated on success
    order_id: Optional[int] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    order_type: Optional[str] = None
    status: Optional[str] = None
    orig_qty: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    price: Optional[str] = None
    stop_price: Optional[str] = None
    time_in_force: Optional[str] = None
    client_order_id: Optional[str] = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    # Populated on failure
    error_message: Optional[str] = None

    # ── Factories ────────────────────────────────────────────────────────────

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> "OrderResult":
        """Build a successful OrderResult from a raw Binance API response dict."""
        return cls(
            success=True,
            order_id=data.get("orderId"),
            symbol=data.get("symbol"),
            side=data.get("side"),
            order_type=data.get("origType") or data.get("type"),
            status=data.get("status"),
            orig_qty=data.get("origQty"),
            executed_qty=data.get("executedQty"),
            avg_price=data.get("avgPrice"),
            price=data.get("price"),
            stop_price=data.get("stopPrice"),
            time_in_force=data.get("timeInForce"),
            client_order_id=data.get("clientOrderId"),
            raw_response=data,
        )

    @classmethod
    def from_error(cls, message: str) -> "OrderResult":
        """Build a failed OrderResult with a human-readable error message."""
        return cls(success=False, error_message=message)

    # ── Display helpers ───────────────────────────────────────────────────────

    @property
    def avg_price_float(self) -> Optional[float]:
        try:
            v = float(self.avg_price or 0)
            return v if v > 0 else None
        except ValueError:
            return None

    @property
    def price_float(self) -> Optional[float]:
        try:
            v = float(self.price or 0)
            return v if v > 0 else None
        except ValueError:
            return None


# ── OrderManager ──────────────────────────────────────────────────────────────

class OrderManager:
    """High-level order placement interface.

    Validates all inputs before touching the network and wraps every API /
    network exception into an ``OrderResult`` so callers never need try/except.
    """

    def __init__(self, client: BinanceClient) -> None:
        self._client = client

    # ── Core method ──────────────────────────────────────────────────────────

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "GTC",
    ) -> OrderResult:
        """Validate inputs and place any supported order type.

        Returns an ``OrderResult`` — never raises.
        """
        # Step 1: validate
        try:
            params = validate_order_params(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
                time_in_force=time_in_force,
            )
        except ValidationError as exc:
            logger.warning("Validation failed: %s", exc)
            return OrderResult.from_error(str(exc))

        # Step 2: build API payload
        api_type = _API_TYPE_MAP.get(params["order_type"], params["order_type"])

        payload: dict[str, Any] = {
            "symbol": params["symbol"],
            "side": params["side"],
            "type": api_type,
            "quantity": params["quantity"],
        }

        if api_type == "LIMIT":
            payload["price"] = params["price"]
            payload["timeInForce"] = params["time_in_force"]

        elif api_type == "STOP_MARKET":
            payload["stopPrice"] = params["stop_price"]

        elif api_type == "STOP":  # STOP_LIMIT
            payload["price"] = params["price"]
            payload["stopPrice"] = params["stop_price"]
            payload["timeInForce"] = params["time_in_force"]

        # Step 3: log intent
        log_ctx = (
            f"{params['order_type']} {params['side']} {params['symbol']} "
            f"qty={params['quantity']}"
        )
        if params.get("price"):
            log_ctx += f"  price={params['price']}"
        if params.get("stop_price"):
            log_ctx += f"  stopPrice={params['stop_price']}"
        logger.info("Placing order → %s", log_ctx)

        # Step 4: send to API
        try:
            response = self._client.post("/fapi/v1/order", params=payload)
        except BinanceAPIError as exc:
            logger.error("API error while placing order: %s", exc)
            return OrderResult.from_error(str(exc))
        except BinanceNetworkError as exc:
            logger.error("Network error while placing order: %s", exc)
            return OrderResult.from_error(str(exc))

        result = OrderResult.from_response(response)
        logger.info(
            "Order accepted ✓  orderId=%s  status=%s  executedQty=%s  avgPrice=%s",
            result.order_id,
            result.status,
            result.executed_qty,
            result.avg_price,
        )
        return result

    # ── Convenience helpers ───────────────────────────────────────────────────

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
    ) -> OrderResult:
        """Place a MARKET order."""
        return self.place_order(symbol, side, "MARKET", quantity)

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = "GTC",
    ) -> OrderResult:
        """Place a LIMIT order."""
        return self.place_order(
            symbol, side, "LIMIT", quantity,
            price=price, time_in_force=time_in_force,
        )

    def place_stop_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
    ) -> OrderResult:
        """Place a STOP_MARKET order (bonus order type)."""
        return self.place_order(
            symbol, side, "STOP_MARKET", quantity, stop_price=stop_price
        )

    def place_stop_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_price: float,
        time_in_force: str = "GTC",
    ) -> OrderResult:
        """Place a STOP_LIMIT (Binance 'STOP') order (bonus order type)."""
        return self.place_order(
            symbol, side, "STOP_LIMIT", quantity,
            price=price, stop_price=stop_price, time_in_force=time_in_force,
        )
