"""BinBot CLI — entry point.

Commands
--------
  place        Place a futures order (MARKET / LIMIT / STOP_MARKET / STOP_LIMIT)
  account      Show wallet balances and open positions
  info         Show trading rules for a symbol
  interactive  Interactive wizard-style order placement
"""

from __future__ import annotations

import sys
from enum import Enum
from typing import Optional

import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, Prompt
from rich.table import Table
from rich.text import Text

from bot.client import BinanceAPIError, BinanceClient, BinanceNetworkError
from bot.config import Config
from bot.logging_config import setup_logging
from bot.orders import OrderManager, OrderResult
from bot.validators import ValidationError

# ── Typer app ─────────────────────────────────────────────────────────────────

app = typer.Typer(
    name="binbot",
    help="[bold cyan]BinBot[/bold cyan] — Binance Futures Testnet Trading Bot (USDT-M)",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True, style="bold red")


# ── Enums for CLI options ─────────────────────────────────────────────────────

class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    STOP_LIMIT = "STOP_LIMIT"


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _print_banner() -> None:
    lines = [
        " ██████╗ ██╗███╗   ██╗██████╗  ██████╗ ████████╗",
        " ██╔══██╗██║████╗  ██║██╔══██╗██╔═══██╗╚══██╔══╝",
        " ██████╔╝██║██╔██╗ ██║██████╔╝██║   ██║   ██║   ",
        " ██╔══██╗██║██║╚██╗██║██╔══██╗██║   ██║   ██║   ",
        " ██████╔╝██║██║ ╚████║██████╔╝╚██████╔╝   ██║   ",
        " ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝    ╚═╝   ",
    ]
    art = "\n".join(f"[bold cyan]{line}[/bold cyan]" for line in lines)
    subtitle = "\n[dim]  Binance Futures Testnet  •  USDT-M Perpetuals  •  v1.0.0[/dim]"
    console.print(
        Panel(
            art + subtitle,
            border_style="cyan",
            padding=(0, 2),
        )
    )
    console.print()


def _build_manager() -> OrderManager:
    """Load config and return an OrderManager; exits on misconfiguration."""
    try:
        cfg = Config.from_env()
    except EnvironmentError as exc:
        err_console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(code=1)

    client = BinanceClient(cfg.api_key, cfg.api_secret, cfg.base_url)
    return OrderManager(client)


def _build_client() -> BinanceClient:
    try:
        cfg = Config.from_env()
    except EnvironmentError as exc:
        err_console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(code=1)
    return BinanceClient(cfg.api_key, cfg.api_secret, cfg.base_url)


# ── Display components ────────────────────────────────────────────────────────

def _fmt_side(side: str) -> str:
    return f"[bold green]{side}[/bold green]" if side == "BUY" else f"[bold red]{side}[/bold red]"


def _fmt_status(status: Optional[str]) -> str:
    if not status:
        return "[dim]—[/dim]"
    colours = {
        "FILLED": "bold green",
        "NEW": "bold yellow",
        "PARTIALLY_FILLED": "bold blue",
        "CANCELED": "bold red",
        "REJECTED": "bold red",
        "EXPIRED": "dim",
    }
    color = colours.get(status, "white")
    return f"[{color}]{status}[/{color}]"


def _print_order_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
) -> None:
    tbl = Table(
        title="  Order Request  ",
        title_style="bold yellow",
        box=box.ROUNDED,
        show_header=False,
        padding=(0, 1),
    )
    tbl.add_column("Field", style="dim", width=14)
    tbl.add_column("Value", style="bold")

    tbl.add_row("Symbol", f"[cyan]{symbol}[/cyan]")
    tbl.add_row("Side", _fmt_side(side))
    tbl.add_row("Order Type", order_type)
    tbl.add_row("Quantity", str(quantity))
    if price is not None:
        tbl.add_row("Price", f"${price:,.4f}")
    if stop_price is not None:
        tbl.add_row("Stop Price", f"${stop_price:,.4f}")

    console.print(tbl)
    console.print()


def _print_order_result(result: OrderResult) -> None:
    if not result.success:
        console.print(
            Panel(
                f"[bold]{result.error_message}[/bold]",
                title="[bold red] ✗  Order Failed [/bold red]",
                border_style="red",
                padding=(1, 2),
            )
        )
        return

    tbl = Table(
        title="  Order Response  ",
        title_style="bold green",
        box=box.ROUNDED,
        show_header=False,
        padding=(0, 1),
    )
    tbl.add_column("Field", style="dim", width=16)
    tbl.add_column("Value", style="bold")

    tbl.add_row("Order ID", str(result.order_id))
    tbl.add_row("Symbol", f"[cyan]{result.symbol}[/cyan]")
    tbl.add_row("Side", _fmt_side(result.side or ""))
    tbl.add_row("Type", result.order_type or "—")
    tbl.add_row("Status", _fmt_status(result.status))
    tbl.add_row("Orig Qty", result.orig_qty or "—")
    tbl.add_row("Executed Qty", result.executed_qty or "—")

    effective_price = result.avg_price_float or result.price_float
    if effective_price:
        label = "Avg Price" if result.avg_price_float else "Price"
        tbl.add_row(label, f"${effective_price:,.4f}")

    if result.client_order_id:
        tbl.add_row("Client Order ID", result.client_order_id)

    console.print(tbl)
    console.print()
    console.print("[bold green] ✓  Order placed successfully![/bold green]")
    console.print()


# ── Commands ──────────────────────────────────────────────────────────────────

@app.command("place", help="Place a MARKET, LIMIT, STOP_MARKET, or STOP_LIMIT order.")
def place(
    symbol: str = typer.Option(
        ..., "--symbol", "-s",
        help="Trading pair symbol  (e.g. BTCUSDT)",
        show_default=False,
    ),
    side: Side = typer.Option(
        ..., "--side",
        help="Order side: BUY or SELL",
        show_default=False,
    ),
    order_type: OrderType = typer.Option(
        ..., "--type", "-t",
        help="Order type: MARKET | LIMIT | STOP_MARKET | STOP_LIMIT",
        show_default=False,
    ),
    quantity: float = typer.Option(
        ..., "--quantity", "-q",
        help="Order quantity in base asset units (e.g. 0.001 for BTC)",
        show_default=False,
    ),
    price: Optional[float] = typer.Option(
        None, "--price", "-p",
        help="Limit price — required for LIMIT and STOP_LIMIT orders",
    ),
    stop_price: Optional[float] = typer.Option(
        None, "--stop-price",
        help="Stop trigger price — required for STOP_MARKET and STOP_LIMIT orders",
    ),
    time_in_force: str = typer.Option(
        "GTC", "--tif",
        help="Time-in-force: GTC | IOC | FOK  (LIMIT orders only)",
    ),
) -> None:
    setup_logging()
    _print_banner()

    _print_order_request(
        symbol, side.value, order_type.value, quantity, price, stop_price
    )

    manager = _build_manager()

    with console.status("[bold yellow]Placing order…[/bold yellow]", spinner="dots"):
        result = manager.place_order(
            symbol=symbol,
            side=side.value,
            order_type=order_type.value,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            time_in_force=time_in_force,
        )

    _print_order_result(result)

    if not result.success:
        raise typer.Exit(code=1)


@app.command("account", help="Display wallet balances and open futures positions.")
def account() -> None:
    setup_logging()
    _print_banner()

    client = _build_client()

    with console.status("[bold yellow]Fetching account data…[/bold yellow]", spinner="dots"):
        try:
            data = client.get_account()
        except (BinanceAPIError, BinanceNetworkError) as exc:
            err_console.print(f"[bold red]Error:[/bold red] {exc}")
            raise typer.Exit(code=1)

    # ── Asset balances ────────────────────────────────────────────────────────
    assets = [a for a in data.get("assets", []) if float(a.get("walletBalance", 0)) > 0]

    if assets:
        at = Table(
            title="  Wallet Balances  ",
            title_style="bold cyan",
            box=box.ROUNDED,
            padding=(0, 1),
        )
        at.add_column("Asset", style="cyan bold")
        at.add_column("Wallet Balance", justify="right")
        at.add_column("Available Balance", justify="right")
        at.add_column("Unrealized PnL", justify="right")

        for a in assets:
            pnl = float(a.get("unrealizedProfit", 0))
            pnl_color = "green" if pnl >= 0 else "red"
            at.add_row(
                a["asset"],
                f"{float(a['walletBalance']):.4f}",
                f"{float(a['availableBalance']):.4f}",
                f"[{pnl_color}]{pnl:+.4f}[/{pnl_color}]",
            )
        console.print(at)
    else:
        console.print("[dim]  No asset balances found.[/dim]")

    console.print()

    # ── Open positions ────────────────────────────────────────────────────────
    positions = [
        p for p in data.get("positions", [])
        if float(p.get("positionAmt", 0)) != 0
    ]

    if positions:
        pt = Table(
            title="  Open Positions  ",
            title_style="bold yellow",
            box=box.ROUNDED,
            padding=(0, 1),
        )
        pt.add_column("Symbol", style="cyan")
        pt.add_column("Side", justify="center")
        pt.add_column("Size", justify="right")
        pt.add_column("Entry Price", justify="right")
        pt.add_column("Mark Price", justify="right")
        pt.add_column("Unrealized PnL", justify="right")
        pt.add_column("Leverage", justify="center")

        for p in positions:
            amt = float(p.get("positionAmt", 0))
            side_label = "LONG" if amt > 0 else "SHORT"
            side_color = "green" if amt > 0 else "red"
            pnl = float(p.get("unrealizedProfit", 0))
            pnl_color = "green" if pnl >= 0 else "red"

            pt.add_row(
                p["symbol"],
                f"[{side_color}]{side_label}[/{side_color}]",
                f"{abs(amt):.4f}",
                f"${float(p.get('entryPrice', 0)):,.2f}",
                f"${float(p.get('markPrice', 0)):,.2f}",
                f"[{pnl_color}]{pnl:+.4f}[/{pnl_color}]",
                f"{p.get('leverage', '—')}x",
            )
        console.print(pt)
    else:
        console.print("[dim]  No open positions.[/dim]")

    console.print()


@app.command("info", help="Show trading rules and precision for a symbol.")
def info(
    symbol: str = typer.Argument(..., help="Symbol to look up (e.g. BTCUSDT)"),
) -> None:
    setup_logging()
    _print_banner()

    client = _build_client()

    with console.status(f"[bold yellow]Fetching info for {symbol.upper()}…[/bold yellow]", spinner="dots"):
        try:
            data = client.get_exchange_info(symbol=symbol)
        except (BinanceAPIError, BinanceNetworkError) as exc:
            err_console.print(f"[bold red]Error:[/bold red] {exc}")
            raise typer.Exit(code=1)

    sym_data = next(
        (s for s in data.get("symbols", []) if s["symbol"] == symbol.upper()),
        None,
    )
    if not sym_data:
        err_console.print(f"Symbol '[bold]{symbol.upper()}[/bold]' not found on this exchange.")
        raise typer.Exit(code=1)

    tbl = Table(
        title=f"  {symbol.upper()} Trading Rules  ",
        title_style="bold cyan",
        box=box.ROUNDED,
        show_header=False,
        padding=(0, 1),
    )
    tbl.add_column("Field", style="dim", width=22)
    tbl.add_column("Value", style="bold")

    tbl.add_row("Symbol", f"[cyan]{sym_data['symbol']}[/cyan]")
    tbl.add_row("Status", sym_data.get("status", "—"))
    tbl.add_row("Base Asset", sym_data.get("baseAsset", "—"))
    tbl.add_row("Quote Asset", sym_data.get("quoteAsset", "—"))
    tbl.add_row("Margin Asset", sym_data.get("marginAsset", "—"))
    tbl.add_row("Contract Type", sym_data.get("contractType", "—"))
    tbl.add_row("Price Precision", str(sym_data.get("pricePrecision", "—")))
    tbl.add_row("Qty Precision", str(sym_data.get("quantityPrecision", "—")))

    # Extract min notional and lot size from filters
    for f in sym_data.get("filters", []):
        ft = f.get("filterType", "")
        if ft == "LOT_SIZE":
            tbl.add_row("Min Qty", f.get("minQty", "—"))
            tbl.add_row("Max Qty", f.get("maxQty", "—"))
            tbl.add_row("Step Size", f.get("stepSize", "—"))
        elif ft == "MIN_NOTIONAL":
            tbl.add_row("Min Notional", f"${float(f.get('notional', 0)):,.2f}")
        elif ft == "PRICE_FILTER":
            tbl.add_row("Min Price", f.get("minPrice", "—"))
            tbl.add_row("Tick Size", f.get("tickSize", "—"))

    console.print(tbl)
    console.print()


@app.command("interactive", help="Launch the interactive order-placement wizard.")
def interactive() -> None:
    setup_logging()
    _print_banner()

    manager = _build_manager()

    console.print(
        Panel(
            "[bold]Welcome to the [cyan]BinBot[/cyan] Interactive Wizard[/bold]\n"
            "[dim]Place orders step-by-step with guided prompts.[/dim]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    _ORDER_MENU = {
        "1": ("MARKET",     "Market Order"),
        "2": ("LIMIT",      "Limit Order"),
        "3": ("STOP_MARKET","Stop-Market Order"),
        "4": ("STOP_LIMIT", "Stop-Limit Order"),
    }

    while True:
        console.rule("[bold cyan]Main Menu[/bold cyan]")
        console.print()
        console.print("  [cyan bold][1][/cyan bold]  Place Market Order")
        console.print("  [cyan bold][2][/cyan bold]  Place Limit Order")
        console.print("  [cyan bold][3][/cyan bold]  Place Stop-Market Order  [dim](bonus)[/dim]")
        console.print("  [cyan bold][4][/cyan bold]  Place Stop-Limit Order   [dim](bonus)[/dim]")
        console.print("  [cyan bold][5][/cyan bold]  View Account Balance")
        console.print("  [cyan bold][0][/cyan bold]  Exit")
        console.print()

        choice = Prompt.ask(
            "[bold yellow]Enter choice[/bold yellow]",
            choices=["0", "1", "2", "3", "4", "5"],
            default="0",
        )

        if choice == "0":
            console.print()
            console.print(
                Panel(
                    "[bold cyan]Thanks for using BinBot. Happy trading! 🚀[/bold cyan]",
                    border_style="cyan",
                    padding=(0, 2),
                )
            )
            break

        if choice == "5":
            account()
            continue

        order_type, label = _ORDER_MENU[choice]
        console.print()
        console.rule(f"[bold yellow]{label}[/bold yellow]")
        console.print()

        try:
            # Collect inputs with validation loop
            symbol = _prompt_until_valid(
                "Symbol [dim](e.g. BTCUSDT)[/dim]",
                default="BTCUSDT",
                transform=str.upper,
                validator=lambda v: v.endswith("USDT") and len(v) >= 5,
                err_msg="Must end with USDT and be at least 5 characters.",
            )

            side = Prompt.ask(
                "[bold]Side[/bold]",
                choices=["BUY", "SELL"],
            ).upper()

            quantity = _prompt_float("Quantity [dim](base asset)[/dim]")

            price: Optional[float] = None
            stop_price: Optional[float] = None

            if order_type in ("LIMIT", "STOP_LIMIT"):
                price = _prompt_float("Limit Price")

            if order_type in ("STOP_MARKET", "STOP_LIMIT"):
                stop_price = _prompt_float("Stop Price")

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Cancelled.[/dim]")
            continue

        console.print()
        _print_order_request(symbol, side, order_type, quantity, price, stop_price)

        try:
            confirmed = Confirm.ask("[bold yellow]Confirm and submit order?[/bold yellow]", default=False)
        except (KeyboardInterrupt, EOFError):
            confirmed = False

        if not confirmed:
            console.print("[dim]  Order cancelled.[/dim]\n")
            continue

        with console.status("[bold yellow]Placing order…[/bold yellow]", spinner="dots"):
            result = manager.place_order(
                symbol=symbol,
                side=side,
                order_type=order_type,
                quantity=quantity,
                price=price,
                stop_price=stop_price,
            )

        _print_order_result(result)


# ── Interactive input helpers ─────────────────────────────────────────────────

def _prompt_float(label: str) -> float:
    """Prompt for a float, retrying on invalid input."""
    while True:
        raw = Prompt.ask(f"[bold]{label}[/bold]")
        try:
            value = float(raw)
            if value > 0:
                return value
            console.print("[red]  Value must be greater than zero. Try again.[/red]")
        except ValueError:
            console.print("[red]  Please enter a valid number. Try again.[/red]")


def _prompt_until_valid(
    label: str,
    *,
    default: str = "",
    transform=str,
    validator=None,
    err_msg: str = "Invalid input.",
) -> str:
    """Generic prompt with optional transform and validator, retrying on failure."""
    while True:
        raw = Prompt.ask(f"[bold]{label}[/bold]", default=default)
        value = transform(raw.strip())
        if validator is None or validator(value):
            return value
        console.print(f"[red]  {err_msg} Try again.[/red]")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
