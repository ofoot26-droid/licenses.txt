"""Tests for the decision engine (signal + risk management)."""

from __future__ import annotations

from datetime import datetime, timezone

from eth_bot.broker import Position
from eth_bot.signals import Signal
from eth_bot.strategy import Action, decide


def _pos(entry: float) -> Position:
    return Position(quantity=1.0, entry_price=entry, opened_at=datetime.now(timezone.utc).isoformat())


def test_buy_when_flat_and_signal_buy(config):
    assert decide(Signal.BUY, 2000.0, None, config) is Action.BUY


def test_hold_when_flat_and_signal_neutral(config):
    assert decide(Signal.NEUTRAL, 2000.0, None, config) is Action.HOLD


def test_hold_when_flat_and_signal_sell(config):
    assert decide(Signal.SELL, 2000.0, None, config) is Action.HOLD


def test_sell_when_in_position_and_signal_sell(config):
    assert decide(Signal.SELL, 2000.0, _pos(2000.0), config) is Action.SELL


def test_hold_when_in_position_and_signal_buy(config):
    # Already long; a BUY signal within risk bounds means hold.
    assert decide(Signal.BUY, 2010.0, _pos(2000.0), config) is Action.HOLD


def test_stop_loss_triggers_sell_over_buy_signal(config):
    # entry 2000, stop at 3% -> 1940. Price 1930 breaches even with BUY signal.
    assert decide(Signal.BUY, 1930.0, _pos(2000.0), config) is Action.SELL


def test_stop_loss_boundary_inclusive(config):
    # Exactly at the stop price should trigger.
    assert decide(Signal.NEUTRAL, 1940.0, _pos(2000.0), config) is Action.SELL


def test_take_profit_triggers_sell(config):
    # entry 2000, take at 6% -> 2120. Price 2130 hits target.
    assert decide(Signal.NEUTRAL, 2130.0, _pos(2000.0), config) is Action.SELL


def test_take_profit_boundary_inclusive(config):
    assert decide(Signal.BUY, 2120.0, _pos(2000.0), config) is Action.SELL


def test_hold_when_in_position_within_bounds_and_neutral(config):
    assert decide(Signal.NEUTRAL, 2050.0, _pos(2000.0), config) is Action.HOLD
