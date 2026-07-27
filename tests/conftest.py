"""Shared test fixtures and fakes (no network)."""

from __future__ import annotations

import pytest

from eth_bot.config import Config
from eth_bot.signals import Signal


@pytest.fixture
def config(tmp_path) -> Config:
    """A Config that writes all state under a temporary directory."""
    return Config(
        starting_cash=10_000.0,
        position_size_pct=1.0,
        fee_pct=0.0,  # zero fees by default for clean arithmetic in tests
        stop_loss_pct=0.03,
        take_profit_pct=0.06,
        state_path=str(tmp_path / "portfolio.json"),
        trade_log_path=str(tmp_path / "trades.csv"),
        log_path=str(tmp_path / "bot.log"),
    )


class FakeSignalSource:
    """Returns a scripted sequence of signals, repeating the last one."""

    def __init__(self, signals):
        self._signals = list(signals)
        self._i = 0

    def get_signal(self) -> Signal:
        sig = self._signals[min(self._i, len(self._signals) - 1)]
        self._i += 1
        return sig


class FakePriceFeed:
    """Returns a scripted sequence of prices, repeating the last one."""

    def __init__(self, prices):
        self._prices = list(prices)
        self._i = 0

    def get_price(self) -> float:
        price = self._prices[min(self._i, len(self._prices) - 1)]
        self._i += 1
        return price
