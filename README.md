# BinBot

> **BinBot** is a production-quality Python trading bot for the **Binance Futures Testnet (USDT-M Perpetuals)**.  
> Features a clean CLI, structured logging, robust input validation, and support for four order types.

---

## Features

| Feature | Detail |
|---|---|
| **Order types** | MARKET, LIMIT, STOP_MARKET *(bonus)*, STOP_LIMIT *(bonus)* |
| **Sides** | BUY and SELL |
| **CLI** | Typer + Rich — coloured output, tables, spinners, interactive wizard |
| **Logging** | Structured file log (`logs/binbot.log`) — every request & response captured |
| **Validation** | All inputs validated before the network is touched |
| **Error handling** | API errors, network failures, and bad input all handled gracefully |
| **Config** | Credentials loaded from a `.env` file — never hard-coded |

---

## Project Structure

```
Binbot/
├── bot/
│   ├── __init__.py          # package metadata
│   ├── client.py            # Binance REST API client (signing, GET/POST)
│   ├── config.py            # .env credential loader
│   ├── logging_config.py    # file + console logging setup
│   ├── orders.py            # OrderManager + OrderResult dataclass
│   └── validators.py        # per-field and composite input validators
├── logs/
│   └── binbot.log           # created automatically on first run
├── cli.py                   # CLI entry point (Typer)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup

### 1. Prerequisites

- Python **3.10+**
- A free [Binance Futures Testnet](https://testnet.binancefuture.com) account

### 2. Get Testnet API Keys

1. Go to <https://testnet.binancefuture.com>  
2. Log in → **API Management** → **Create API**  
3. Copy your **API Key** and **Secret Key**

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Credentials

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and fill in your keys:

```dotenv
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_BASE_URL=https://testnet.binancefuture.com
```

---

## Usage

All commands are run from the project root:

```bash
python cli.py <command> [options]
```

Run `python cli.py --help` at any time for a full reference.

---

### Place a Market Order

```bash
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### Place a Limit Order

```bash
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 95000
```

### Place a Stop-Market Order *(bonus)*

```bash
python cli.py place --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.001 --stop-price 45000
```

### Place a Stop-Limit Order *(bonus)*

```bash
python cli.py place --symbol BTCUSDT --side SELL --type STOP_LIMIT --quantity 0.001 --price 44500 --stop-price 45000
```

### Check Account Balance & Positions

```bash
python cli.py account
```

### View Symbol Trading Rules

```bash
python cli.py info BTCUSDT
```

### Interactive Wizard Mode *(bonus)*

```bash
python cli.py interactive
```

Launches a menu-driven wizard that walks you through order placement step-by-step, with input validation and a confirmation prompt before submitting.

---

## CLI Options Reference

### `place` command

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--symbol` | `-s` | ✅ | Trading pair (e.g. `BTCUSDT`) |
| `--side` | | ✅ | `BUY` or `SELL` |
| `--type` | `-t` | ✅ | `MARKET` \| `LIMIT` \| `STOP_MARKET` \| `STOP_LIMIT` |
| `--quantity` | `-q` | ✅ | Quantity in base asset units |
| `--price` | `-p` | LIMIT / STOP_LIMIT | Limit price |
| `--stop-price` | | STOP_MARKET / STOP_LIMIT | Stop trigger price |
| `--tif` | | | Time-in-force: `GTC` (default) \| `IOC` \| `FOK` |

---

## Logging

Every run appends to `logs/binbot.log`.  
The log captures:

- **INFO** — every order request with full parameters, every successful API response  
- **WARNING** — validation failures (bad inputs caught before hitting the network)  
- **ERROR** — API errors (invalid symbol, insufficient margin, etc.) and network failures  
- **DEBUG** — raw HTTP requests and responses for deep troubleshooting  

Example log lines:

```
2026-03-06 12:00:01 | INFO     | binbot.orders         | Placing order → MARKET BUY BTCUSDT qty=0.001
2026-03-06 12:00:01 | INFO     | binbot.client         | POST https://testnet.binancefuture.com/fapi/v1/order  params={...}
2026-03-06 12:00:02 | INFO     | binbot.client         | POST https://testnet.binancefuture.com/fapi/v1/order  → HTTP 200  orderId=123456  status=FILLED
2026-03-06 12:00:02 | INFO     | binbot.orders         | Order accepted ✓  orderId=123456  status=FILLED  executedQty=0.001  avgPrice=84320.5
```

---

## Assumptions & Design Notes

1. **Testnet only** — the base URL defaults to `https://testnet.binancefuture.com`. Change `BINANCE_BASE_URL` in `.env` to switch to mainnet (use real money at your own risk).
2. **STOP_LIMIT mapping** — Binance Futures uses the API type `STOP` for stop-limit orders. BinBot accepts the more intuitive name `STOP_LIMIT` and maps it internally.
3. **Quantity precision** — quantities are sent as-is. If the exchange rejects an order due to precision, check `python cli.py info BTCUSDT` for the allowed step size.
4. **Hedge mode** — BinBot places orders in the default one-way position mode. Hedge mode (`positionSide=LONG/SHORT`) is not currently supported.
5. **Credentials security** — API keys are read from environment variables and are **never** logged or printed.

---

## Sample Output

```
╭──────────────────────────────────────────────────────╮
│  ██████╗ ██╗███╗   ██╗██████╗  ██████╗ ████████╗     │
│  ██╔══██╗██║████╗  ██║██╔══██╗██╔═══██╗╚══██╔══╝     │
│  ██████╔╝██║██╔██╗ ██║██████╔╝██║   ██║   ██║        │
│  ██╔══██╗██║██║╚██╗██║██╔══██╗██║   ██║   ██║        │
│  ██████╔╝██║██║ ╚████║██████╔╝╚██████╔╝   ██║        │
│  ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝    ╚═╝        │
│                                                       │
│  Binance Futures Testnet  •  USDT-M Perpetuals  v1.0  │
╰──────────────────────────────────────────────────────╯

╭─── Order Request ──────╮    ╭─── Order Response ─────╮
│ Symbol    BTCUSDT       │    │ Order ID   123456789    │
│ Side      BUY           │    │ Symbol     BTCUSDT      │
│ Type      MARKET        │    │ Side       BUY          │
│ Quantity  0.001         │    │ Status     FILLED       │
╰─────────────────────────╯    │ Orig Qty   0.001        │
                               │ Executed   0.001        │
                               │ Avg Price  $84,320.50   │
                               ╰─────────────────────────╯
 ✓  Order placed successfully!
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP client for Binance REST API |
| `typer[all]` | CLI framework |
| `rich` | Terminal formatting, tables, panels |
| `python-dotenv` | `.env` file loading |
