"""Logging configuration for BinBot.

Sets up a 'binbot' logger that writes:
  - DEBUG and above  → logs/binbot.log   (structured, timestamped)
  - WARNING and above → stderr console   (concise, human-readable)
"""

import logging
from pathlib import Path

LOGS_DIR = Path(__file__).resolve().parent.parent / "logs"

LOG_FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-22s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_level: str = "DEBUG") -> logging.Logger:
    """Configure and return the root 'binbot' logger.

    Safe to call multiple times — subsequent calls are no-ops.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("binbot")
    if logger.handlers:
        return logger  # Already initialised — skip

    logger.setLevel(logging.DEBUG)

    # ── File handler: full detail (DEBUG+) ───────────────────────────────────
    file_handler = logging.FileHandler(LOGS_DIR / "binbot.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(fmt=LOG_FILE_FORMAT, datefmt=LOG_DATE_FORMAT)
    )
    logger.addHandler(file_handler)

    # ── Console handler: warnings and above only ─────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(console_handler)

    return logger
