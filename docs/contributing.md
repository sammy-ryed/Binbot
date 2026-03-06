# Contributing

Guidelines for contributing to BinBot.

---

## Project Goals

BinBot is a focused, production-quality example of a Binance Futures trading bot. Contributions should maintain:

- **Clean layering** — CLI, business logic, and transport stay separate
- **Test coverage** — new code should come with tests; the bar is currently 132 tests
- **Security** — credentials must never appear in logs, output, or committed files
- **Simplicity** — prefer clear, direct code over clever abstractions

---

## Getting Started

### 1. Fork and clone

```bash
git clone https://github.com/<your-username>/binbot.git
cd binbot
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install all dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up credentials

```bash
copy .env.example .env    # Windows
cp .env.example .env      # macOS / Linux
# Fill in your Binance Testnet API key and secret
```

### 5. Run the test suite to confirm everything works

```bash
python -m pytest --no-cov -v
# Expected: 132 passed
```

---

## Development Workflow

1. Create a branch:
   ```bash
   git checkout -b feature/my-feature
   ```

2. Make your changes

3. Write tests for your changes in the appropriate `tests/test_*.py` file

4. Run the full test suite:
   ```bash
   python -m pytest
   ```

5. Check for errors:
   ```bash
   python -m py_compile bot/*.py cli.py
   ```

6. Commit and push:
   ```bash
   git add .
   git commit -m "feat: describe your change"
   git push origin feature/my-feature
   ```

7. Open a pull request

---

## Adding a New Order Type

1. Add the type name to `VALID_ORDER_TYPES` in `bot/validators.py`
2. Add required-field logic in `validate_order_params()` in `bot/validators.py`
3. Add an entry to `_API_TYPE_MAP` in `bot/orders.py` if the Binance API type name differs
4. Add payload-building logic in `OrderManager.place_order()` in `bot/orders.py`
5. Add a convenience method (e.g. `place_trailing_stop_order()`) in `OrderManager`
6. Add the type to the `OrderType` enum in `cli.py`
7. Write tests in `tests/test_validators.py` and `tests/test_order_manager.py`

---

## Adding a New CLI Command

1. Define a new function decorated with `@app.command()` in `cli.py`
2. Use `_build_client()` or `_build_manager()` to get the required dependency
3. Use Rich (`console.print`, `Table`, `Panel`) for output — do not use `print()`
4. Exit with `raise typer.Exit(code=1)` on error, let the function return normally on success
5. Add tests in `tests/test_cli.py` using `typer.testing.CliRunner`

---

## Code Style

- Follow existing code patterns — consistency over personal preference
- Type hints on all function signatures
- Docstrings on public classes and methods
- Maximum line length: 100 characters
- No bare `except:` clauses — always catch a specific exception type

---

## Test Guidelines

- **Zero real network calls** — mock all HTTP with `unittest.mock.patch`
- Test both success and failure paths for every function
- Use `pytest.raises(ExceptionType)` for exception assertions
- Name tests descriptively: `test_validate_symbol_accepts_valid_pair`, `test_validate_symbol_rejects_missing_usdt_suffix`

---

## Commit Message Format

Use conventional commits:

```
feat: add trailing stop order type
fix: handle empty symbol string in validator
docs: add ETHUSDT example to CLI reference
test: add missing coverage for validate_stop_price
refactor: extract payload-building into helper
```

---

## Reporting Issues

Please include:
- Python version (`python --version`)
- The exact command you ran
- The full error output
- Contents of your `.env` (with values redacted)
