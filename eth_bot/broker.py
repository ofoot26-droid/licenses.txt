"""Simulated (paper) spot broker with persistence.

Long-only, one open position at a time. All fills are simulated at the price
passed in; a configurable taker fee is deducted on both entry and exit. State is
persisted atomically to JSON after every change, and every fill is appended to a
CSV trade log, so the bot survives restarts and keeps an auditable history.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

from .config import Config

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Position:
    quantity: float          # units of base asset held
    entry_price: float       # average fill price of the open position
    opened_at: str           # ISO-8601 UTC timestamp

    def value(self, price: float) -> float:
        return self.quantity * price

    def unrealized_pl(self, price: float) -> float:
        return (price - self.entry_price) * self.quantity


class PaperBroker:
    """A minimal simulated spot broker.

    ``cash`` is the quote-currency balance (e.g. USDT). ``position`` is the
    single open long position, or ``None`` when flat.
    """

    def __init__(self, config: Config) -> None:
        self.config = config
        self.cash: float = config.starting_cash
        self.position: Optional[Position] = None
        self.realized_pl: float = 0.0
        self.trade_count: int = 0
        self.win_count: int = 0

    # ------------------------------------------------------------------ #
    # Trading
    # ------------------------------------------------------------------ #
    def equity(self, price: float) -> float:
        """Total account value marked at ``price``."""
        pos_value = self.position.value(price) if self.position else 0.0
        return self.cash + pos_value

    def buy(self, price: float) -> Optional[Position]:
        """Open a long position sized at ``position_size_pct`` of equity.

        No-op (returns None) if already in a position or the sizing rounds to
        zero quantity.
        """
        if self.position is not None:
            logger.debug("buy() ignored: already in a position")
            return None
        if price <= 0:
            logger.warning("buy() ignored: non-positive price %s", price)
            return None

        budget = self.equity(price) * self.config.position_size_pct
        budget = min(budget, self.cash)  # cannot spend more cash than we hold
        if budget <= 0:
            logger.debug("buy() ignored: no cash to deploy")
            return None

        fee = budget * self.config.fee_pct
        spend_on_asset = budget - fee
        quantity = spend_on_asset / price
        if quantity <= 0:
            return None

        self.cash -= budget
        self.position = Position(
            quantity=quantity, entry_price=price, opened_at=_utcnow_iso()
        )
        self._log_fill("BUY", quantity, price, fee, realized_pl=0.0)
        logger.info(
            "BUY %.6f @ %.2f (fee %.4f, cash left %.2f)",
            quantity, price, fee, self.cash,
        )
        return self.position

    def sell(self, price: float) -> float:
        """Close the open position at ``price``. Returns realized P&L for the trade."""
        if self.position is None:
            logger.debug("sell() ignored: no open position")
            return 0.0
        if price <= 0:
            logger.warning("sell() ignored: non-positive price %s", price)
            return 0.0

        pos = self.position
        gross = pos.quantity * price
        fee = gross * self.config.fee_pct
        proceeds = gross - fee

        cost_basis = pos.quantity * pos.entry_price
        realized = proceeds - cost_basis

        self.cash += proceeds
        self.realized_pl += realized
        self.trade_count += 1
        if realized > 0:
            self.win_count += 1

        self._log_fill("SELL", pos.quantity, price, fee, realized_pl=realized)
        logger.info(
            "SELL %.6f @ %.2f (fee %.4f, realized %.2f, cash %.2f)",
            pos.quantity, price, fee, realized, self.cash,
        )
        self.position = None
        return realized

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict:
        return {
            "cash": self.cash,
            "position": asdict(self.position) if self.position else None,
            "realized_pl": self.realized_pl,
            "trade_count": self.trade_count,
            "win_count": self.win_count,
            "updated_at": _utcnow_iso(),
        }

    def save(self) -> None:
        """Persist state to JSON atomically (temp file + rename)."""
        path = self.config.state_path
        _ensure_parent_dir(path)
        payload = json.dumps(self.to_dict(), indent=2)
        directory = os.path.dirname(path) or "."
        fd, tmp = tempfile.mkstemp(dir=directory, prefix=".portfolio-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def load(self) -> bool:
        """Restore state from JSON if it exists. Returns True if loaded."""
        path = self.config.state_path
        if not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.cash = float(data.get("cash", self.config.starting_cash))
        self.realized_pl = float(data.get("realized_pl", 0.0))
        self.trade_count = int(data.get("trade_count", 0))
        self.win_count = int(data.get("win_count", 0))
        pos = data.get("position")
        self.position = (
            Position(
                quantity=float(pos["quantity"]),
                entry_price=float(pos["entry_price"]),
                opened_at=str(pos["opened_at"]),
            )
            if pos
            else None
        )
        logger.info("Loaded state: cash=%.2f position=%s", self.cash, self.position)
        return True

    def _log_fill(
        self, side: str, quantity: float, price: float, fee: float, realized_pl: float
    ) -> None:
        path = self.config.trade_log_path
        _ensure_parent_dir(path)
        write_header = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            if write_header:
                writer.writerow(
                    ["time", "side", "quantity", "price", "fee", "realized_pl"]
                )
            writer.writerow(
                [_utcnow_iso(), side, f"{quantity:.8f}", f"{price:.2f}",
                 f"{fee:.6f}", f"{realized_pl:.6f}"]
            )


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
