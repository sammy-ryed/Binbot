# API Reference

Complete reference for every public class, method, and exception in the `bot` package.

---

## Table of Contents

- [bot.client](#botclient)
  - [BinanceAPIError](#binanceapierror)
  - [BinanceNetworkError](#binancenetworkerror)
  - [BinanceClient](#binanceclient)
- [bot.validators](#botvalidators)
  - [ValidationError](#validationerror)
  - [validate_symbol](#validate_symbol)
  - [validate_side](#validate_side)
  - [validate_order_type](#validate_order_type)
  - [validate_quantity](#validate_quantity)
  - [validate_price](#validate_price)
  - [validate_stop_price](#validate_stop_price)
  - [validate_time_in_force](#validate_time_in_force)
  - [validate_order_params](#validate_order_params)
- [bot.orders](#botorders)
  - [OrderResult](#orderresult)
  - [OrderManager](#ordermanager)
- [bot.config](#botconfig)
  - [Config](#config)
- [bot.logging_config](#botlogging_config)

---

## bot.client

Transport layer for the Binance Futures USDT-M REST API. Handles HMAC-SHA256 signing, request dispatch, response parsing, and error normalisation.

---

### BinanceAPIError

```python
class BinanceAPIError(Exception)
```

Raised when Binance returns a logical error response — i.e. a JSON body with a negative integer `code` field.

**Constructor**

```python
BinanceAPIError(code: int, message: str)
```

| Attribute | Type | Description |
|-----------|------|-------------|
| `code` | `int` | Binance error code (always negative, e.g. `-4164`) |
| `message` | `str` | Human-readable error message from Binance |

**Example**

```python
try:
    client.post("/fapi/v1/order", params)
except BinanceAPIError as e:
    print(e.code)     # -4164
    print(e.message)  # "Order's notional must be no smaller than 100"
```

---

### BinanceNetworkError

```python
class BinanceNetworkError(Exception)
```

Raised for transport-level failures: connection refused, DNS resolution failure, or request timeout. Wraps `requests.exceptions.ConnectionError`, `Timeout`, and `RequestException`.

---

### BinanceClient

```python
class BinanceClient
```

Thin, authenticated wrapper around the Binance Futures REST API.

**Constructor**

```python
BinanceClient(
    api_key: str,
    api_secret: str,
    base_url: str = "https://testnet.binancefuture.com",
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | — | Binance API key (sent as `X-MBX-APIKEY` header) |
| `api_secret` | `str` | — | Binance API secret (used for HMAC-SHA256 signing) |
| `base_url` | `str` | testnet URL | Base URL for all requests |

**Class attributes**

| Attribute | Value | Description |
|-----------|-------|-------------|
| `RECV_WINDOW` | `5000` | Clock-skew tolerance in milliseconds |
| `TIMEOUT` | `10` | HTTP request timeout in seconds |

---

#### BinanceClient.get

```python
def get(
    endpoint: str,
    params: dict[str, Any] | None = None,
    signed: bool = False,
) -> dict[str, Any]
```

Perform an authenticated (or public) GET request.

| Parameter | Type | Description |
|-----------|------|-------------|
| `endpoint` | `str` | API path, e.g. `"/fapi/v1/exchangeInfo"` |
| `params` | `dict \| None` | Query parameters |
| `signed` | `bool` | If `True`, injects timestamp + signature before sending |

**Returns** — parsed JSON response as a dict.

**Raises** — `BinanceAPIError`, `BinanceNetworkError`

---

#### BinanceClient.post

```python
def post(
    endpoint: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]
```

Perform a signed POST request. Always injects auth (every POST to Binance Futures requires a signature).

| Parameter | Type | Description |
|-----------|------|-------------|
| `endpoint` | `str` | API path, e.g. `"/fapi/v1/order"` |
| `params` | `dict \| None` | Request body parameters |

**Returns** — parsed JSON response as a dict.

**Raises** — `BinanceAPIError`, `BinanceNetworkError`

---

#### BinanceClient.get_account

```python
def get_account() -> dict[str, Any]
```

Fetch futures account information (balances, positions, margin).

**Endpoint** — `GET /fapi/v2/account` (signed)

**Returns** — raw Binance account dict with keys including `assets`, `positions`, `totalWalletBalance`, `totalUnrealizedProfit`.

---

#### BinanceClient.get_exchange_info

```python
def get_exchange_info(symbol: str | None = None) -> dict[str, Any]
```

Fetch exchange trading rules.

**Endpoint** — `GET /fapi/v1/exchangeInfo`

| Parameter | Type | Description |
|-----------|------|-------------|
| `symbol` | `str \| None` | If provided, filters results to that symbol only |

**Returns** — raw Binance exchange info dict with `symbols`, `filters`, precision rules.

---

## bot.validators

Input validation for all order parameters. Every function returns a cleaned/normalised value on success and raises `ValidationError` on failure. Validation always happens **before** any network call.

---

### ValidationError

```python
class ValidationError(ValueError)
```

Raised when a user-supplied order parameter fails validation. Subclasses `ValueError` so it can be caught by either name.

---

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `VALID_SIDES` | `frozenset{"BUY", "SELL"}` | Accepted order sides |
| `VALID_ORDER_TYPES` | `frozenset{"MARKET", "LIMIT", "STOP_MARKET", "STOP_LIMIT"}` | Accepted BinBot order types |
| `VALID_TIME_IN_FORCE` | `frozenset{"GTC", "IOC", "FOK", "GTX"}` | Accepted time-in-force values |

---

### validate_symbol

```python
def validate_symbol(symbol: str) -> str
```

Strips, uppercases, and validates the trading pair against the pattern `^[A-Z0-9]{2,10}USDT$`.

**Returns** — uppercase symbol string (e.g. `"BTCUSDT"`)

**Raises** — `ValidationError` if empty or doesn't match the pattern

```python
validate_symbol("btcusdt")  # → "BTCUSDT"
validate_symbol("BTC")      # → ValidationError: Invalid symbol 'BTC'
```

---

### validate_side

```python
def validate_side(side: str) -> str
```

Strips, uppercases, and validates the order side.

**Returns** — `"BUY"` or `"SELL"`

**Raises** — `ValidationError` for any other value

---

### validate_order_type

```python
def validate_order_type(order_type: str) -> str
```

Strips, uppercases, and validates the order type.

**Returns** — one of `"MARKET"`, `"LIMIT"`, `"STOP_MARKET"`, `"STOP_LIMIT"`

**Raises** — `ValidationError` for any other value

---

### validate_quantity

```python
def validate_quantity(quantity: float | str) -> float
```

Coerces to float and ensures the value is strictly positive.

**Returns** — positive `float`

**Raises** — `ValidationError` if not numeric or ≤ 0

---

### validate_price

```python
def validate_price(
    price: float | str | None,
    *,
    required: bool = False,
) -> float | None
```

Validates an optional or required price.

| Parameter | Description |
|-----------|-------------|
| `price` | Raw price value (can be `None` or empty string) |
| `required` | If `True`, raises if price is absent |

**Returns** — positive `float` or `None`

**Raises** — `ValidationError` if required and missing, or if non-numeric, or if ≤ 0

---

### validate_stop_price

```python
def validate_stop_price(
    stop_price: float | str | None,
    *,
    required: bool = False,
) -> float | None
```

Same semantics as `validate_price` but for the stop trigger price.

---

### validate_time_in_force

```python
def validate_time_in_force(tif: str) -> str
```

Strips, uppercases, and validates the time-in-force value.

**Returns** — one of `"GTC"`, `"IOC"`, `"FOK"`, `"GTX"`

**Raises** — `ValidationError` for any other value

---

### validate_order_params

```python
def validate_order_params(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float | str,
    price: float | str | None = None,
    stop_price: float | str | None = None,
    time_in_force: str = "GTC",
) -> dict
```

Composite validator — validates every field and applies order-type-based requirement rules:

| Order type | `price` required | `stop_price` required |
|------------|------------------|-----------------------|
| `MARKET` | No | No |
| `LIMIT` | **Yes** | No |
| `STOP_MARKET` | No | **Yes** |
| `STOP_LIMIT` | **Yes** | **Yes** |

**Returns** — clean dict with keys: `symbol`, `side`, `order_type`, `quantity`, `price`, `stop_price`, `time_in_force`

**Raises** — `ValidationError` on the first failing field (fast-fail)

---

## bot.orders

Business logic layer. Insulates the CLI from all exceptions; callers only inspect `OrderResult.success`.

---

### OrderResult

```python
@dataclass
class OrderResult
```

Holds the outcome of an order request — successful or otherwise. Never raises.

**Fields**

| Field | Type | Populated when | Description |
|-------|------|----------------|-------------|
| `success` | `bool` | Always | `True` = accepted by Binance |
| `order_id` | `int \| None` | Success | Binance-assigned order ID |
| `symbol` | `str \| None` | Success | Trading pair |
| `side` | `str \| None` | Success | `"BUY"` or `"SELL"` |
| `order_type` | `str \| None` | Success | Order type as returned by Binance |
| `status` | `str \| None` | Success | `FILLED`, `NEW`, `PARTIALLY_FILLED`, etc. |
| `orig_qty` | `str \| None` | Success | Requested quantity |
| `executed_qty` | `str \| None` | Success | Filled quantity |
| `avg_price` | `str \| None` | Success | Average fill price (string from API) |
| `price` | `str \| None` | Success | Limit price (string from API) |
| `stop_price` | `str \| None` | Success | Stop trigger price (string from API) |
| `time_in_force` | `str \| None` | Success | TIF value |
| `client_order_id` | `str \| None` | Success | Client-generated order ID |
| `raw_response` | `dict` | Success | Full raw Binance API response |
| `error_message` | `str \| None` | Failure | Human-readable error description |

**Computed properties**

| Property | Returns | Description |
|----------|---------|-------------|
| `avg_price_float` | `float \| None` | `avg_price` as float; `None` if zero or missing |
| `price_float` | `float \| None` | `price` as float; `None` if zero or missing |

**Factory methods**

```python
@classmethod
def from_response(cls, data: dict[str, Any]) -> OrderResult
```
Build a successful `OrderResult` from a raw Binance API response dict.

```python
@classmethod
def from_error(cls, message: str) -> OrderResult
```
Build a failed `OrderResult` with a human-readable error message.

---

### OrderManager

```python
class OrderManager
```

High-level order placement interface. Validates inputs before touching the network. Wraps every exception into `OrderResult` — **never raises**.

**Constructor**

```python
OrderManager(client: BinanceClient)
```

---

#### OrderManager.place_order

```python
def place_order(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None = None,
    stop_price: float | None = None,
    time_in_force: str = "GTC",
) -> OrderResult
```

Validates all inputs, builds the Binance API payload, submits the order, and returns an `OrderResult`. Never raises.

**Internal type mapping** — `STOP_LIMIT` is transparently converted to Binance's internal type `STOP`.

---

#### OrderManager.place_market_order

```python
def place_market_order(symbol: str, side: str, quantity: float) -> OrderResult
```

Convenience wrapper for `place_order(..., order_type="MARKET")`.

---

#### OrderManager.place_limit_order

```python
def place_limit_order(
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    time_in_force: str = "GTC",
) -> OrderResult
```

Convenience wrapper for `place_order(..., order_type="LIMIT")`.

---

#### OrderManager.place_stop_market_order

```python
def place_stop_market_order(
    symbol: str,
    side: str,
    quantity: float,
    stop_price: float,
) -> OrderResult
```

Convenience wrapper for `place_order(..., order_type="STOP_MARKET")`.

---

#### OrderManager.place_stop_limit_order

```python
def place_stop_limit_order(
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    stop_price: float,
    time_in_force: str = "GTC",
) -> OrderResult
```

Convenience wrapper for `place_order(..., order_type="STOP_LIMIT")`.

---

## bot.config

Credential and configuration loader.

---

### Config

```python
@dataclass
class Config
```

**Fields**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `api_key` | `str` | — | Binance API key |
| `api_secret` | `str` | — | Binance API secret |
| `base_url` | `str` | `"https://testnet.binancefuture.com"` | API base URL |

**Factory method**

```python
@classmethod
def from_env(cls) -> Config
```

Loads the `.env` file from the project root and reads:

| Variable | Required | Default |
|----------|----------|---------|
| `BINANCE_API_KEY` | Yes | — |
| `BINANCE_API_SECRET` | Yes | — |
| `BINANCE_BASE_URL` | No | `https://testnet.binancefuture.com` |

**Raises** — `EnvironmentError` if either required variable is missing or empty.

---

## bot.logging_config

```python
def setup_logging() -> None
```

Configures the root `binbot` logger with two handlers:

| Handler | Level | Destination | Format |
|---------|-------|-------------|--------|
| File | `DEBUG` | `logs/binbot.log` | Timestamped, full detail |
| Console | `WARNING` | stderr | Timestamped, warnings/errors only |

Safe to call multiple times (guards against duplicate handlers). Automatically creates the `logs/` directory if it doesn't exist.

Log format:
```
%(asctime)s | %(levelname)-8s | %(name)-22s | %(message)s
```
