# Documentation

Welcome to the BinBot documentation.

---

## Guides

| Document | Description |
|----------|-------------|
| [Configuration](configuration.md) | Environment variables, `.env` setup, testnet vs mainnet, logging settings |
| [CLI Reference](cli_reference.md) | Every command, option, and example for `cli.py` |
| [API Reference](api_reference.md) | Full reference for every public class and method in `bot/` |
| [Architecture](architecture.md) | Layer diagram, data flow walkthroughs, error handling strategy, security model |
| [Contributing](contributing.md) | Dev setup, workflow, adding order types, adding CLI commands, test guidelines |

---

## Quick Links

- [Place an order → CLI Reference: place](cli_reference.md#place)
- [All environment variables → Configuration](configuration.md#environment-variables)
- [OrderManager API → API Reference: OrderManager](api_reference.md#ordermanager)
- [How signing works → Architecture: Layer 1](architecture.md#layer-1--transport-botclientpy)
- [Why orders never raise → Architecture: Layer 2](architecture.md#layer-2--business-logic-botorderspy)
- [Run the tests → Contributing](contributing.md#5-run-the-test-suite-to-confirm-everything-works)
