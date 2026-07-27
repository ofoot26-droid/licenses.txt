"""Decision engine: combine the TradingView signal with risk management.

Pure function, no I/O — trivially unit-testable. Rules are evaluated in strict
priority order so that risk exits (stop-loss / take-profit) always win over the
raw signal.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from .config import Config
from .broker import Position
from .signals import Signal


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


def decide(
    signal: Signal,
    price: float,
    position: Optional[Position],
    config: Config,
) -> Action:
    """Return the action to take this cycle.

    Priority:
      1. In a position and stop-loss breached -> SELL
      2. In a position and take-profit reached -> SELL
      3. In a position and signal is SELL -> SELL
      4. Flat and signal is BUY -> BUY
      5. Otherwise -> HOLD
    """
    if position is not None:
        stop_price = position.entry_price * (1.0 - config.stop_loss_pct)
        take_price = position.entry_price * (1.0 + config.take_profit_pct)
        if price <= stop_price:
            return Action.SELL
        if price >= take_price:
            return Action.SELL
        if signal is Signal.SELL:
            return Action.SELL
        return Action.HOLD

    # Flat
    if signal is Signal.BUY:
        return Action.BUY
    return Action.HOLD
