"""Tests for the PaperBroker: fills, fee math, and persistence."""

from __future__ import annotations

import csv
from dataclasses import replace

from eth_bot.broker import PaperBroker


def test_buy_deploys_full_equity_no_fee(config):
    broker = PaperBroker(config)
    broker.buy(2000.0)
    assert broker.position is not None
    # Zero fee, 100% sizing: 10000 / 2000 = 5 ETH, cash drained.
    assert broker.position.quantity == 5.0
    assert broker.position.entry_price == 2000.0
    assert broker.cash == 0.0


def test_buy_applies_fee(config):
    cfg = replace(config, fee_pct=0.001)
    broker = PaperBroker(cfg)
    broker.buy(2000.0)
    # Budget 10000, fee 10, 9990 buys 4.995 ETH.
    assert broker.position.quantity == 9990.0 / 2000.0
    assert broker.cash == 0.0


def test_buy_is_noop_when_already_in_position(config):
    broker = PaperBroker(config)
    broker.buy(2000.0)
    qty = broker.position.quantity
    broker.buy(2500.0)  # ignored
    assert broker.position.quantity == qty


def test_sell_realizes_profit(config):
    broker = PaperBroker(config)
    broker.buy(2000.0)          # 5 ETH
    realized = broker.sell(2200.0)
    assert realized == 5.0 * (2200.0 - 2000.0)  # 1000
    assert broker.position is None
    assert broker.cash == 11_000.0
    assert broker.realized_pl == 1000.0
    assert broker.trade_count == 1
    assert broker.win_count == 1


def test_sell_realizes_loss(config):
    broker = PaperBroker(config)
    broker.buy(2000.0)
    realized = broker.sell(1800.0)
    assert realized == -1000.0
    assert broker.win_count == 0
    assert broker.trade_count == 1


def test_sell_without_position_is_noop(config):
    broker = PaperBroker(config)
    assert broker.sell(2000.0) == 0.0
    assert broker.trade_count == 0


def test_equity_marks_open_position(config):
    broker = PaperBroker(config)
    broker.buy(2000.0)  # 5 ETH, cash 0
    assert broker.equity(2500.0) == 5.0 * 2500.0


def test_persistence_round_trip(config):
    broker = PaperBroker(config)
    broker.buy(2000.0)
    broker.save()

    restored = PaperBroker(config)
    assert restored.load() is True
    assert restored.cash == broker.cash
    assert restored.position is not None
    assert restored.position.quantity == broker.position.quantity
    assert restored.position.entry_price == 2000.0


def test_load_returns_false_when_no_state(config):
    broker = PaperBroker(config)
    assert broker.load() is False


def test_trade_log_written(config):
    broker = PaperBroker(config)
    broker.buy(2000.0)
    broker.sell(2200.0)
    with open(config.trade_log_path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    assert rows[0] == ["time", "side", "quantity", "price", "fee", "realized_pl"]
    assert rows[1][1] == "BUY"
    assert rows[2][1] == "SELL"
