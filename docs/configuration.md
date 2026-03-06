# Configuration Reference

Everything you need to know about configuring BinBot.

---

## Environment Variables

BinBot is configured entirely through environment variables, loaded from a `.env` file in the project root.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BINANCE_API_KEY` | ✅ Yes | — | Your Binance API key |
| `BINANCE_API_SECRET` | ✅ Yes | — | Your Binance API secret |
| `BINANCE_BASE_URL` | No | `https://testnet.binancefuture.com` | API base URL |

---

## Setup

### Step 1 — Copy the template

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

### Step 2 — Get testnet credentials

1. Go to [testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Log in (create a free account if needed)
3. Navigate to **API Management** → **Create API**
4. Copy the **API Key** and **Secret Key** — the secret is only shown once

### Step 3 — Fill in your `.env`

```dotenv
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_BASE_URL=https://testnet.binancefuture.com
```

---

## Switching Between Testnet and Mainnet

> ⚠️ **Warning:** Trading on mainnet uses real money. Proceed with extreme caution.

To use mainnet, set:

```dotenv
BINANCE_BASE_URL=https://fapi.binance.com
```

You will also need to replace your testnet API key and secret with mainnet credentials generated at [binance.com/en/my/settings/api-management](https://www.binance.com/en/my/settings/api-management).

---

## .env.example

The `.env.example` file ships with the repository as a template:

```dotenv
# Copy this file to .env and fill in your credentials
# NEVER commit your actual .env file to version control

BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
BINANCE_BASE_URL=https://testnet.binancefuture.com
```

---

## Security

- `.env` is listed in `.gitignore` — it will never be committed to version control
- Credentials are loaded into memory by `Config.from_env()` and stored only in the `requests.Session` headers
- API keys are **never** written to log files
- HMAC signatures are replaced with `***REDACTED***` in all log output

---

## Error: Missing Credentials

If `BINANCE_API_KEY` or `BINANCE_API_SECRET` are missing or empty, you will see:

```
Configuration error: Missing required environment variable(s): BINANCE_API_KEY.
Copy .env.example → .env and fill in your Binance Testnet credentials.
```

**Common causes:**
- `.env` file doesn't exist (copy from `.env.example`)
- Variable name has a typo (check exact spelling)
- Value is missing or left as the placeholder text

---

## Logging Configuration

Logging is configured in `bot/logging_config.py`. The defaults are:

| Setting | Value |
|---------|-------|
| Log file path | `logs/binbot.log` (relative to project root) |
| File log level | `DEBUG` (everything) |
| Console log level | `WARNING` (warnings and errors only) |
| Log format | `%(asctime)s \| %(levelname)-8s \| %(name)-22s \| %(message)s` |

The `logs/` directory and `binbot.log` file are created automatically on first run.

---

## pytest Configuration

Defined in `pytest.ini` at the project root:

```ini
[pytest]
testpaths = tests
addopts = -v --tb=short --no-header --cov=bot --cov-report=term-missing --cov-report=html:htmlcov
```

| Setting | Value | Effect |
|---------|-------|--------|
| `testpaths` | `tests` | Only looks in the `tests/` directory |
| `-v` | verbose | Shows each test name and result |
| `--tb=short` | short tracebacks | Compact failure output |
| `--cov=bot` | coverage for `bot/` | Tracks which lines in `bot/` are exercised |
| `--cov-report=term-missing` | terminal report | Shows uncovered line numbers inline |
| `--cov-report=html:htmlcov` | HTML report | Generates `htmlcov/index.html` |

To run tests without coverage (faster):

```bash
python -m pytest --no-cov -v
```
