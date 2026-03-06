# CLI Reference

Full reference for every BinBot command and option.

---

## Running BinBot

```bash
python cli.py [COMMAND] [OPTIONS]
```

Global help:

```bash
python cli.py --help
```

---

## Commands

| Command | Description |
|---------|-------------|
| [`place`](#place) | Place a futures order |
| [`account`](#account) | Display wallet balances and open positions |
| [`info`](#info) | Show trading rules for a symbol |
| [`interactive`](#interactive) | Launch the interactive order-placement wizard |

---

## place

Place a MARKET, LIMIT, STOP_MARKET, or STOP_LIMIT futures order on Binance Futures Testnet.

```bash
python cli.py place [OPTIONS]
```

### Options

| Option | Short | Type | Required | Default | Description |
|--------|-------|------|----------|---------|-------------|
| `--symbol` | `-s` | TEXT | ✅ | — | Trading pair. Must be a USDT-M perpetual (e.g. `BTCUSDT`, `ETHUSDT`) |
| `--side` | | ENUM | ✅ | — | `BUY` or `SELL` |
| `--type` | `-t` | ENUM | ✅ | — | `MARKET` · `LIMIT` · `STOP_MARKET` · `STOP_LIMIT` |
| `--quantity` | `-q` | FLOAT | ✅ | — | Order quantity in base asset units (e.g. `0.002` BTC) |
| `--price` | `-p` | FLOAT | Conditional | — | Limit price. Required for `LIMIT` and `STOP_LIMIT` |
| `--stop-price` | | FLOAT | Conditional | — | Stop trigger price. Required for `STOP_MARKET` and `STOP_LIMIT` |
| `--tif` | | ENUM | No | `GTC` | Time-in-force: `GTC` · `IOC` · `FOK` · `GTX` |

### Return codes

| Code | Meaning |
|------|---------|
| `0` | Order placed (or validation succeeded) |
| `1` | Error (validation failure, API error, credentials missing) |

### Examples

**Market buy** — fills immediately at the current market price:
```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.002
```

**Limit sell** — rests in the order book at $150,000:
```bash
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.002 --price 150000
```

**Limit buy with IOC** — fill immediately or cancel:
```bash
python cli.py place -s ETHUSDT --side BUY -t LIMIT -q 0.05 -p 2400 --tif IOC
```

**Stop-market sell** — triggers a market sell if BTC drops to $50,000:
```bash
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET \
    --quantity 0.002 --stop-price 50000
```

**Stop-limit sell** — triggers a limit sell at $44,500 when BTC hits $45,000:
```bash
python cli.py place --symbol BTCUSDT --side SELL --type STOP_LIMIT \
    --quantity 0.002 --price 44500 --stop-price 45000
```

**Validation error example** — LIMIT without `--price`:
```bash
python cli.py place --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.002
# ✗  Order Failed
# Price is required for LIMIT and STOP_LIMIT orders.
```

---

### Output

On success, the CLI prints two Rich tables:

1. **Order Request** — shows what was sent (symbol, side, type, quantity, optional price/stop-price)
2. **Order Response** — shows what Binance returned (order ID, status, executed qty, avg fill price)

Status is colour-coded:

| Status | Colour |
|--------|--------|
| `FILLED` | Bold green |
| `NEW` | Bold yellow |
| `PARTIALLY_FILLED` | Bold blue |
| `CANCELED` / `REJECTED` | Bold red |
| `EXPIRED` | Dim |

---

## account

Display futures wallet balances and open positions.

```bash
python cli.py account
```

No options. Prints two tables:

**Wallet Balances** — one row per asset with non-zero balance:

| Column | Description |
|--------|-------------|
| Asset | e.g. `USDT`, `BTC` |
| Wallet Balance | Total balance including locked margin |
| Available | Free margin available for new orders |
| Unrealised PnL | Open position profit or loss |

**Open Positions** — one row per open position:

| Column | Description |
|--------|-------------|
| Symbol | e.g. `BTCUSDT` |
| Side | `LONG` or `SHORT` |
| Size | Position quantity |
| Entry Price | Average entry price |
| Mark Price | Current mark price |
| Unrealised PnL | Current profit or loss |
| Leverage | Leverage multiplier |

If there are no open positions, a notice is shown instead of an empty table.

---

## info

Show exchange trading rules and precision settings for a symbol.

```bash
python cli.py info SYMBOL
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `SYMBOL` | ✅ | Trading pair, e.g. `BTCUSDT` |

### Output

A Rich table with symbol-specific trading rules including:

| Field | Description |
|-------|-------------|
| Price Precision | Decimal places for prices |
| Quantity Precision | Decimal places for quantities |
| Base Asset Precision | Precision of the base asset |
| Min Quantity | Minimum order quantity |
| Max Quantity | Maximum order quantity |
| Step Size | Quantity increment (lot size) |
| Tick Size | Minimum price movement |
| Min Notional | Minimum order value in USD |
| Max Notional | Maximum order value in USD |

> **Tip:** Run `info` before placing orders to check the minimum notional and step size for your chosen symbol.

---

## interactive

Launch the interactive menu-driven order wizard.

```bash
python cli.py interactive
```

No options.

### Flow

```
Main Menu
  [1] Market Order
  [2] Limit Order
  [3] Stop-Market Order
  [4] Stop-Limit Order
  [q] Quit
```

For each order type, you are prompted for the required fields with inline validation — any invalid input is rejected immediately with an explanation, and you are re-prompted without leaving the wizard.

After filling all fields, a confirmation prompt appears:
```
Place this order? [y/N]
```

The wizard loops back to the main menu after each order (success or failure), so you can place multiple orders in one session.

---

## Time-in-Force Values

| Value | Full Name | Behaviour |
|-------|-----------|-----------|
| `GTC` | Good Till Cancelled | Remains open until manually cancelled (default) |
| `IOC` | Immediate or Cancel | Fills as much as possible immediately; remainder cancelled |
| `FOK` | Fill or Kill | Fills entirely at once or is completely cancelled |
| `GTX` | Good Till Crossing | Post-only — cancelled if it would match immediately (maker-only) |

---

## Symbol Format

BinBot only supports **USDT-M perpetual futures** on Binance Futures Testnet. Symbols must:
- End in `USDT`
- Contain 2–10 uppercase alphanumeric characters before `USDT`
- Examples: `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`

Common symbols on testnet: `BTCUSDT`, `ETHUSDT`, `BNBUSDT`, `XRPUSDT`, `SOLUSDT`

---

## Minimum Notional

Binance Futures requires every order's notional value (price × quantity) to be at least **$100 USDT**.

| Symbol | At ~$84,000 | At ~$2,500 | At ~$150 |
|--------|-------------|------------|---------|
| BTCUSDT | `qty ≥ 0.002` | — | — |
| ETHUSDT | — | `qty ≥ 0.04` | — |
| SOLUSDT | — | — | `qty ≥ 0.67` |

Use `python cli.py info SYMBOL` to get the exact minimum notional and step size for any pair.
