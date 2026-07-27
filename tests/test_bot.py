"""End-to-end cycle tests using fake signal and price sources (no network)."""

from __future__ import annotations

from eth_bot.broker import PaperBroker
from eth_bot.bot import TradingBot
from eth_bot.signals import Signal
from eth_bot.strategy import Action

from .conftest import FakeSignalSource, FakePriceFeed


def _bot(config, signals, prices):
    broker = PaperBroker(config)
    return TradingBot(
        config,
        signal_source=FakeSignalSource(signals),
        price_feed=FakePriceFeed(prices),
        broker=broker,
    )


def test_full_buy_then_take_profit(config):
    # BUY at 2000, then price rallies past the 6% take-profit target.
    bot = _bot(config, [Signal.BUY, Signal.NEUTRAL], [2000.0, 2200.0])

    r1 = bot.run_cycle()
    assert r1.action is Action.BUY
    assert bot.broker.position is not None

    r2 = bot.run_cycle()
    assert r2.action is Action.SELL          # take-profit
    assert bot.broker.position is None
    assert bot.broker.realized_pl > 0
    assert bot.broker.trade_count == 1


def test_full_buy_then_stop_loss(config):
    bot = _bot(config, [Signal.BUY, Signal.BUY], [2000.0, 1900.0])
    bot.run_cycle()                          # BUY @ 2000
    r2 = bot.run_cycle()                     # 1900 breaches 3% stop -> SELL
    assert r2.action is Action.SELL
    assert bot.broker.realized_pl < 0


def test_neutral_signal_does_nothing(config):
    bot = _bot(config, [Signal.NEUTRAL], [2000.0])
    r = bot.run_cycle()
    assert r.action is Action.HOLD
    assert bot.broker.position is None
    assert bot.broker.cash == config.starting_cash


def test_sell_signal_closes_position(config):
    bot = _bot(config, [Signal.BUY, Signal.SELL], [2000.0, 2050.0])
    bot.run_cycle()
    r2 = bot.run_cycle()
    assert r2.action is Action.SELL
    assert bot.broker.position is None


def test_cycle_persists_state(config):
    bot = _bot(config, [Signal.BUY], [2000.0])
    bot.run_cycle()
    reloaded = PaperBroker(config)
    assert reloaded.load() is True
    assert reloaded.position is not None


def test_equity_reported_in_cycle_result(config):
    bot = _bot(config, [Signal.NEUTRAL], [2000.0])
    r = bot.run_cycle()
    assert r.equity == config.starting_cash
    assert r.price == 2000.0
    assert r.signal is Signal.NEUTRAL
