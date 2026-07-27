"""Performance reporting for the paper portfolio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .config import Config
from .broker import PaperBroker


@dataclass
class Performance:
    cash: float
    starting_cash: float
    position_qty: float
    position_entry: float
    price: Optional[float]
    equity: float
    realized_pl: float
    unrealized_pl: float
    total_pl: float
    total_return_pct: float
    trade_count: int
    win_count: int
    win_rate_pct: float


def compute_performance(
    broker: PaperBroker, config: Config, price: Optional[float]
) -> Performance:
    pos = broker.position
    mark = price if price is not None else (pos.entry_price if pos else 0.0)

    unrealized = pos.unrealized_pl(mark) if pos else 0.0
    equity = broker.cash + (pos.value(mark) if pos else 0.0)
    total_pl = broker.realized_pl + unrealized
    start = config.starting_cash or 1.0
    win_rate = (broker.win_count / broker.trade_count * 100.0) if broker.trade_count else 0.0

    return Performance(
        cash=broker.cash,
        starting_cash=config.starting_cash,
        position_qty=pos.quantity if pos else 0.0,
        position_entry=pos.entry_price if pos else 0.0,
        price=price,
        equity=equity,
        realized_pl=broker.realized_pl,
        unrealized_pl=unrealized,
        total_pl=total_pl,
        total_return_pct=(equity - config.starting_cash) / start * 100.0,
        trade_count=broker.trade_count,
        win_count=broker.win_count,
        win_rate_pct=win_rate,
    )


def format_status(perf: Performance, config: Config) -> str:
    price_str = f"{perf.price:,.2f}" if perf.price is not None else "n/a (offline)"
    pos_line = (
        f"{perf.position_qty:.6f} @ {perf.position_entry:,.2f}"
        if perf.position_qty
        else "flat"
    )
    lines = [
        "=" * 44,
        f" {config.symbol} paper portfolio",
        "=" * 44,
        f" Current price   : {price_str}",
        f" Cash            : {perf.cash:,.2f}",
        f" Open position   : {pos_line}",
        f" Equity          : {perf.equity:,.2f}",
        "-" * 44,
        f" Realized P&L    : {perf.realized_pl:,.2f}",
        f" Unrealized P&L  : {perf.unrealized_pl:,.2f}",
        f" Total P&L       : {perf.total_pl:,.2f}",
        f" Total return    : {perf.total_return_pct:+.2f}%",
        "-" * 44,
        f" Closed trades   : {perf.trade_count}",
        f" Wins            : {perf.win_count}",
        f" Win rate        : {perf.win_rate_pct:.1f}%",
        "=" * 44,
    ]
    return "\n".join(lines)
