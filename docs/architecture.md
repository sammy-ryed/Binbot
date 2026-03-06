# Architecture

Deep dive into BinBot's structure, data flow, and key design decisions.

---

## Overview

BinBot is a **3-layer CLI application**:

```
CLI (cli.py)
    │  user interaction — Typer + Rich
    │
    ▼
OrderManager (bot/orders.py)
    │  business logic — validate, build payload, return result
    │
    ▼
BinanceClient (bot/client.py)
    │  transport — HMAC-SHA256 signing, HTTP, response parsing
    │
    ▼
Binance Futures Testnet REST API
```

Each layer has a single responsibility and does not leak its concerns upward.

---

## File Structure

```
Binbot/
├── bot/                         ← The reusable library
│   ├── __init__.py              # Package metadata and __version__
│   ├── client.py                # REST transport: sign, send, parse
│   ├── config.py                # .env credential loading
│   ├── logging_config.py        # Dual-handler structured logging
│   ├── orders.py                # Business logic + OrderResult dataclass
│   └── validators.py            # Per-field and composite input validation
│
├── cli.py                       ← Entry point (Typer + Rich)
│
├── tests/                       ← pytest test suite
│   ├── test_validators.py       # 47 tests
│   ├── test_orders_result.py    # 18 tests
│   ├── test_client.py           # 14 tests
│   ├── test_order_manager.py    # 20 tests
│   └── test_cli.py              # 13 tests  →  132 total
│
├── logs/
│   └── binbot.log               # Auto-created on first run
│
├── docs/                        ← You are here
├── .env                         # Credentials (gitignored)
├── .env.example                 # Template for new developers
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## Layer Details

### Layer 1 — Transport (`bot/client.py`)

`BinanceClient` is the only layer that speaks HTTP. It knows nothing about order types or business rules.

**Responsibilities:**
- Appending the `X-MBX-APIKEY` header to every request (via `requests.Session`)
- Computing HMAC-SHA256 signatures for authenticated endpoints
- Injecting `timestamp` and `recvWindow` into signed requests
- Dispatching GET and POST requests with a 10-second timeout
- Parsing responses and raising typed exceptions

**Signing flow:**

```
params dict
    │
    ├─ add timestamp (current epoch ms)
    ├─ add recvWindow (5000 ms)
    ├─ URL-encode the full dict
    ├─ HMAC-SHA256 with api_secret as key
    └─ append signature= to params
```

The secret never leaves memory and is never written to logs (the signature is replaced with `***REDACTED***`).

**Exception hierarchy:**

```
Exception
├─ BinanceAPIError(code, message)   # Binance returned {"code": <neg>, "msg": ...}
└─ BinanceNetworkError              # Timeout, DNS failure, connection refused
```

---

### Layer 2 — Business Logic (`bot/orders.py`)

`OrderManager` is the only layer that knows about order types and what fields are required for each.

**Responsibilities:**
- Delegating all validation to `bot/validators.py`
- Mapping BinBot's friendly type names to Binance API type names (`STOP_LIMIT` → `STOP`)
- Building the exact payload Binance expects
- Calling `BinanceClient.post()`
- Catching every exception and converting it to an `OrderResult`

**The never-raises contract:**

```python
result = manager.place_order(...)   # NEVER raises
if result.success:
    print(result.order_id)
else:
    print(result.error_message)
```

This means the CLI layer is 100% free of `try/except` for order placement.

**`OrderResult` is a dataclass, not a dict:**  
Fields are typed, IDE-autocompleted, and documented. The `raw_response` field preserves the full original Binance response for debugging.

---

### Layer 3 — CLI (`cli.py`)

The CLI layer handles only user interaction — it does not validate, sign, or parse anything itself.

**Responsibilities:**
- Defining Typer commands and options
- Building `OrderManager` / `BinanceClient` from config
- Calling business logic methods
- Rendering results with Rich (tables, panels, colours)
- Mapping exit codes: `0` = success, `1` = any error

**Interactive wizard:**  
`interactive` uses loops and Rich's `Prompt` / `Confirm` classes to build a guided experience. Validation inside the wizard is performed by the same `bot/validators.py` functions — no duplicated logic.

---

## Data Flow: Placing a Market Order

```
User runs:
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.002

1.  cli.py:place()
        Typer parses args → calls _build_manager() → calls manager.place_order(...)

2.  OrderManager.place_order()
        Calls validate_order_params() → returns clean dict  ← ValidationError possible here

3.  validate_order_params()
        validate_symbol("BTCUSDT")    → "BTCUSDT"
        validate_side("BUY")          → "BUY"
        validate_order_type("MARKET") → "MARKET"
        validate_quantity(0.002)      → 0.002
        validate_price(None)          → None   (not required for MARKET)
        validate_stop_price(None)     → None   (not required for MARKET)
        validate_time_in_force("GTC") → "GTC"

4.  OrderManager.place_order() (continued)
        Builds payload:
          {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET", "quantity": 0.002}
        Calls client.post("/fapi/v1/order", payload)

5.  BinanceClient.post()
        _inject_auth(payload) → adds timestamp, recvWindow, signature
        session.post(url, data=signed_payload, timeout=10)
        _parse_response(response) → returns dict or raises BinanceAPIError

6.  OrderManager.place_order() (continued)
        Receives dict → OrderResult.from_response(data)
        Returns OrderResult(success=True, order_id=..., status="FILLED", ...)

7.  cli.py:place() (continued)
        _print_order_request(...)   ← shows what was sent
        _print_order_result(result) ← shows FILLED result in green table
        sys.exit(0)
```

---

## Data Flow: Validation Failure

```
User runs:
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.002
(missing --price)

1.  cli.py:place() → manager.place_order(price=None)

2.  validate_order_params()
        validate_price(None, required=True)
        raises ValidationError("Price is required for LIMIT and STOP_LIMIT orders.")

3.  OrderManager.place_order()
        except ValidationError: logger.warning(...)
        return OrderResult.from_error("Price is required...")
        ← NO network call was made

4.  cli.py:place()
        _print_order_result(result)  ← red error panel
        sys.exit(1)
```

---

## Error Handling Strategy

| Error type | Where caught | How surfaced |
|------------|-------------|--------------|
| Missing `.env` credentials | `Config.from_env()` | `EnvironmentError` → CLI prints message → exit 1 |
| Invalid symbol / side / type | `validate_*()` in `validators.py` | `ValidationError` → `OrderResult.from_error()` |
| Missing required price/stop | `validate_order_params()` | Same as above |
| Binance API error (e.g. min notional) | `BinanceClient._parse_response()` | `BinanceAPIError` → `OrderResult.from_error()` |
| Network failure / timeout | `BinanceClient.post()` | `BinanceNetworkError` → `OrderResult.from_error()` |

The pattern: **errors become data** as soon as they reach `OrderManager`. Above that, there are no exceptions.

---

## Dependency Graph

```
cli.py
  └─ bot.orders       (OrderManager, OrderResult)
       ├─ bot.client  (BinanceClient, exceptions)
       └─ bot.validators (ValidationError, validate_order_params)
  └─ bot.client       (direct, for account/info commands)
  └─ bot.config       (Config.from_env)
  └─ bot.logging_config (setup_logging)

Tests (no production imports of test tools):
  test_*.py
    └─ unittest.mock  (patch, MagicMock — zero real HTTP)
```

---

## Security Considerations

1. **Credentials in `.env` only** — `Config.from_env()` reads from `os.getenv`. The `.env` file is gitignored and is never imported or read elsewhere.
2. **API key in session header** — stored in `requests.Session.headers`, never in URLs or query params.
3. **Signature redacted in logs** — `_mask(params)` replaces the 64-char hex signature with `***REDACTED***` before any log statement.
4. **No secrets printed to stdout** — the CLI only prints order results and exchange data.
5. **Testnet by default** — the default `BINANCE_BASE_URL` points to `testnet.binancefuture.com`. A mainnet URL must be explicitly configured.

---

## Testing Architecture

All 132 tests run with **zero real network calls** using `unittest.mock.patch`.

| Strategy | Where used |
|----------|-----------|
| `patch("requests.Session.post")` | `test_client.py` — mocks HTTP at the session level |
| `patch("bot.client.BinanceClient")` | `test_order_manager.py` — mocks the whole client |
| `patch("cli._build_manager")` | `test_cli.py` — mocks the manager returned to CLI commands |
| No mocking | `test_validators.py`, `test_orders_result.py` — pure functions, no I/O |

This approach means:
- Tests run offline, instantly, and deterministically
- No test API keys are required
- The test suite can run in CI without secrets
