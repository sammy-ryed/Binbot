"""Input validation for BinBot order parameters.

All public functions return cleaned / normalised values on success and raise
``ValidationError`` (a subclass of ``ValueError``) on failure.
"""

from __future__ import annotations

import re
from typing import Optional

# ── Exception ─────────────────────────────────────────────────────────────────

class ValidationError(ValueError):
    """Raised when a user-supplied order parameter fails validation."""


# ── Constants ─────────────────────────────────────────────────────────────────

VALID_SIDES: frozenset[str] = frozenset({"BUY", "SELL"})

# Friendly names exposed in the CLI (STOP_LIMIT maps to Binance API type STOP)
VALID_ORDER_TYPES: frozenset[str] = frozenset(
    {"MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT"}
)

# Binance USDT-M pairs always end in USDT (e.g. BTCUSDT, ETHUSDT, SOLUSDT)
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,10}USDT$")

VALID_TIME_IN_FORCE: frozenset[str] = frozenset({"GTC", "IOC", "FOK", "GTX"})


# ── Individual field validators ───────────────────────────────────────────────

def validate_symbol(symbol: str) -> str:
    """Return the upper-cased symbol or raise ValidationError."""
    cleaned = symbol.strip().upper()
    if not cleaned:
        raise ValidationError("Symbol cannot be empty.")
    if not _SYMBOL_RE.match(cleaned):
        raise ValidationError(
            f"Invalid symbol '{cleaned}'. "
            "Expected format: <BASE>USDT  (e.g. BTCUSDT, ETHUSDT, SOLUSDT)."
        )
    return cleaned


def validate_side(side: str) -> str:
    """Return 'BUY' or 'SELL', or raise ValidationError."""
    cleaned = side.strip().upper()
    if cleaned not in VALID_SIDES:
        raise ValidationError(
            f"Invalid side '{cleaned}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return cleaned


def validate_order_type(order_type: str) -> str:
    """Return the normalised order type string, or raise ValidationError."""
    cleaned = order_type.strip().upper()
    if cleaned not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{cleaned}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return cleaned


def validate_quantity(quantity: float | str) -> float:
    """Return a positive float quantity, or raise ValidationError."""
    try:
        qty = float(quantity)
    except (ValueError, TypeError):
        raise ValidationError(f"Quantity must be a number, got: '{quantity}'.")
    if qty <= 0:
        raise ValidationError(
            f"Quantity must be greater than zero, got: {qty}."
        )
    return qty


def validate_price(
    price: float | str | None,
    *,
    required: bool = False,
) -> Optional[float]:
    """Return a positive float price, None if omitted, or raise ValidationError."""
    if price is None or str(price).strip() == "":
        if required:
            raise ValidationError(
                "Price is required for LIMIT and STOP_LIMIT orders."
            )
        return None

    try:
        p = float(price)
    except (ValueError, TypeError):
        raise ValidationError(f"Price must be a number, got: '{price}'.")
    if p <= 0:
        raise ValidationError(f"Price must be greater than zero, got: {p}.")
    return p


def validate_stop_price(
    stop_price: float | str | None,
    *,
    required: bool = False,
) -> Optional[float]:
    """Return a positive float stop price, None if omitted, or raise ValidationError."""
    if stop_price is None or str(stop_price).strip() == "":
        if required:
            raise ValidationError(
                "Stop price is required for STOP_MARKET and STOP_LIMIT orders."
            )
        return None

    try:
        sp = float(stop_price)
    except (ValueError, TypeError):
        raise ValidationError(
            f"Stop price must be a number, got: '{stop_price}'."
        )
    if sp <= 0:
        raise ValidationError(
            f"Stop price must be greater than zero, got: {sp}."
        )
    return sp


def validate_time_in_force(tif: str) -> str:
    """Return the normalised timeInForce value, or raise ValidationError."""
    cleaned = tif.strip().upper()
    if cleaned not in VALID_TIME_IN_FORCE:
        raise ValidationError(
            f"Invalid timeInForce '{cleaned}'. "
            f"Must be one of: {', '.join(sorted(VALID_TIME_IN_FORCE))}."
        )
    return cleaned


# ── Composite validator ───────────────────────────────────────────────────────

def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float | str,
    price: float | str | None = None,
    stop_price: float | str | None = None,
    time_in_force: str = "GTC",
) -> dict:
    """Validate all order parameters together and return a clean dict.

    Returns a dict with keys:
        symbol, side, order_type, quantity, price, stop_price, time_in_force

    Raises:
        ValidationError: on the first failing field.
    """
    ot = validate_order_type(order_type)

    needs_price = ot in {"LIMIT", "STOP_LIMIT"}
    needs_stop = ot in {"STOP_MARKET", "STOP_LIMIT"}

    return {
        "symbol": validate_symbol(symbol),
        "side": validate_side(side),
        "order_type": ot,
        "quantity": validate_quantity(quantity),
        "price": validate_price(price, required=needs_price),
        "stop_price": validate_stop_price(stop_price, required=needs_stop),
        "time_in_force": validate_time_in_force(time_in_force),
    }
