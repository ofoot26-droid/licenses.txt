#!/usr/bin/env python3
"""ETH paper-trading bot (single-file edition), driven by TradingView signals.

Fully automated PAPER trading for ETH:
  * Signals  : TradingView's technical-analysis consensus (BUY/SELL/NEUTRAL),
               via the unofficial `tradingview-ta` library. No account needed.
  * Prices   : live Binance public ticker, with automatic Coinbase fallback.
               No API key needed.
  * Trading  : simulated (paper) long-only spot account, one position at a time,
               with taker fees, stop-loss / take-profit, JSON state + CSV log.

This is a self-contained copy of the modular `eth_bot/` package, merged into one
file for easy download and running. Behavior and config are identical.

------------------------------------------------------------------------------
INSTALL
    pip install tradingview-ta requests

RUN
    python eth_trading_bot.py            # continuous loop (Ctrl-C to stop)
    python eth_trading_bot.py --once     # a single cycle, then exit (cron)
    python eth_trading_bot.py status     # print portfolio + performance

CONFIG (later overrides earlier): built-in defaults -> config.json (same dir)
    -> environment variables prefixed ETHBOT_ (e.g. ETHBOT_TA_INTERVAL=1h).
State is written under ./state/ (portfolio.json, trades.csv, bot.log).
------------------------------------------------------------------------------

DISCLAIMER: Paper trading only. No real orders, no real funds. Not financial
advice. TradingView data comes from an unofficial scraper library. Use at your
own risk.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import signal as signal_module
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, fields, replace  # noqa: F401
from datetime import datetime, timezone
from enum import Enum
from logging.handlers import RotatingFileHandler
from typing import Any, Optional, Protocol

import requests

__version__ = "0.1.0"
logger = logging.getLogger("eth_bot")


# =========================================================================== #
# Config
# =========================================================================== #
@dataclass
class Config:
    # Market / instrument
    symbol: str = "ETHUSDT"          # exchange symbol used for TA + price feed
    exchange: str = "BINANCE"        # TradingView exchange for TA lookup
    screener: str = "crypto"         # TradingView screener
    ta_interval: str = "15m"         # 1m,5m,15m,30m,1h,2h,4h,1d,1W,1M

    # Loop
    poll_seconds: int = 900          # seconds between cycles in continuous mode

    # Account / sizing
    starting_cash: float = 10_000.0  # initial paper cash balance (quote currency)
    position_size_pct: float = 1.0   # fraction of equity to deploy per entry (0-1)
    fee_pct: float = 0.001           # taker fee applied to every fill (0.1%)

    # Risk management
    stop_loss_pct: float = 0.03      # exit if price falls this fraction below entry
    take_profit_pct: float = 0.06    # exit if price rises this fraction above entry

    # Persistence / logging
    state_path: str = "state/portfolio.json"
    trade_log_path: str = "state/trades.csv"
    log_path: str = "state/bot.log"

    # Networking
    request_timeout: float = 10.0
    max_retries: int = 3

    @classmethod
    def load(cls, config_file: Optional[str] = "config.json") -> "Config":
        """Build a Config from defaults, an optional JSON file, then env vars."""
        values: dict[str, Any] = asdict(cls())

        if config_file and os.path.exists(config_file):
            with open(config_file, "r", encoding="utf-8") as fh:
                file_values = json.load(fh)
            for key, val in file_values.items():
                if key in values:
                    values[key] = val

        type_by_name = {f.name: f.type for f in fields(cls)}
        for f in fields(cls):
            env_key = "ETHBOT_" + f.name.upper()
            if env_key in os.environ:
                values[f.name] = _coerce(os.environ[env_key], type_by_name[f.name])

        return cls(**values)


def _coerce(raw: str, type_hint: Any) -> Any:
    hint = str(type_hint)
    if "int" in hint:
        return int(raw)
    if "float" in hint:
        return float(raw)
    if "bool" in hint:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return raw


# =========================================================================== #
# Signals (TradingView TA)
# =========================================================================== #
class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


_RECOMMENDATION_MAP = {
    "STRONG_BUY": Signal.BUY,
    "BUY": Signal.BUY,
    "NEUTRAL": Signal.NEUTRAL,
    "SELL": Signal.SELL,
    "STRONG_SELL": Signal.SELL,
}


class SignalSource(Protocol):
    def get_signal(self) -> Signal:  # pragma: no cover - interface
        ...


def _resolve_interval(interval: str):
    from tradingview_ta import Interval

    mapping = {
        "1m": Interval.INTERVAL_1_MINUTE,
        "5m": Interval.INTERVAL_5_MINUTES,
        "15m": Interval.INTERVAL_15_MINUTES,
        "30m": Interval.INTERVAL_30_MINUTES,
        "1h": Interval.INTERVAL_1_HOUR,
        "2h": Interval.INTERVAL_2_HOURS,
        "4h": Interval.INTERVAL_4_HOURS,
        "1d": Interval.INTERVAL_1_DAY,
        "1W": Interval.INTERVAL_1_WEEK,
        "1M": Interval.INTERVAL_1_MONTH,
    }
    if interval not in mapping:
        raise ValueError(
            f"Unsupported ta_interval {interval!r}; valid: {sorted(mapping)}"
        )
    return mapping[interval]


class TradingViewSignalSource:
    """Live signal source backed by TradingView TA."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._interval = _resolve_interval(config.ta_interval)

    def get_signal(self) -> Signal:
        from tradingview_ta import TA_Handler

        try:
            handler = TA_Handler(
                symbol=self.config.symbol,
                screener=self.config.screener,
                exchange=self.config.exchange,
                interval=self._interval,
                timeout=self.config.request_timeout,
            )
            analysis = handler.get_analysis()
            recommendation = str(analysis.summary.get("RECOMMENDATION", "NEUTRAL"))
            sig = _RECOMMENDATION_MAP.get(recommendation.upper(), Signal.NEUTRAL)
            logger.debug("TradingView %s -> %s", recommendation, sig.value)
            return sig
        except Exception as exc:  # noqa: BLE001 - never crash the loop on signals
            logger.warning("Failed to fetch TradingView signal, holding: %s", exc)
            return Signal.NEUTRAL


# =========================================================================== #
# Price feed (Binance -> Coinbase fallback)
# =========================================================================== #
_BINANCE_URL = "https://api.binance.com/api/v3/ticker/price"
_COINBASE_URL = "https://api.coinbase.com/v2/prices/{pair}/spot"


class PriceFeed(Protocol):
    def get_price(self) -> float:  # pragma: no cover - interface
        ...


class BinancePriceFeed:
    """Live price feed using Binance public ticker, with a Coinbase fallback."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def get_price(self) -> float:
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                return self._fetch_binance()
            except Exception as exc:  # noqa: BLE001 - retried below
                last_exc = exc
                logger.warning(
                    "Binance price fetch failed (attempt %d/%d): %s",
                    attempt, self.config.max_retries, exc,
                )
                time.sleep(min(2 ** (attempt - 1), 8))

        logger.warning("Falling back to Coinbase spot price")
        try:
            return self._fetch_coinbase()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"Unable to fetch price for {self.config.symbol}: "
                f"binance_error={last_exc!r} coinbase_error={exc!r}"
            ) from exc

    def _fetch_binance(self) -> float:
        resp = requests.get(
            _BINANCE_URL,
            params={"symbol": self.config.symbol},
            timeout=self.config.request_timeout,
        )
        resp.raise_for_status()
        return float(resp.json()["price"])

    def _fetch_coinbase(self) -> float:
        pair = self._coinbase_pair(self.config.symbol)
        resp = requests.get(
            _COINBASE_URL.format(pair=pair), timeout=self.config.request_timeout
        )
        resp.raise_for_status()
        return float(resp.json()["data"]["amount"])

    @staticmethod
    def _coinbase_pair(symbol: str) -> str:
        upper = symbol.upper()
        for quote in ("USDT", "USDC", "USD"):
            if upper.endswith(quote):
                return f"{upper[:-len(quote)]}-USD"
        return upper


# =========================================================================== #
# Paper broker
# =========================================================================== #
def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Position:
    quantity: float
    entry_price: float
    opened_at: str

    def value(self, price: float) -> float:
        return self.quantity * price

    def unrealized_pl(self, price: float) -> float:
        return (price - self.entry_price) * self.quantity


class PaperBroker:
    """A minimal simulated spot broker (long-only, one position at a time)."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.cash: float = config.starting_cash
        self.position: Optional[Position] = None
        self.realized_pl: float = 0.0
        self.trade_count: int = 0
        self.win_count: int = 0

    def equity(self, price: float) -> float:
        pos_value = self.position.value(price) if self.position else 0.0
        return self.cash + pos_value

    def buy(self, price: float) -> Optional[Position]:
        if self.position is not None:
            logger.debug("buy() ignored: already in a position")
            return None
        if price <= 0:
            logger.warning("buy() ignored: non-positive price %s", price)
            return None

        budget = self.equity(price) * self.config.position_size_pct
        budget = min(budget, self.cash)
        if budget <= 0:
            logger.debug("buy() ignored: no cash to deploy")
            return None

        fee = budget * self.config.fee_pct
        quantity = (budget - fee) / price
        if quantity <= 0:
            return None

        self.cash -= budget
        self.position = Position(
            quantity=quantity, entry_price=price, opened_at=_utcnow_iso()
        )
        self._log_fill("BUY", quantity, price, fee, realized_pl=0.0)
        logger.info("BUY %.6f @ %.2f (fee %.4f, cash left %.2f)",
                    quantity, price, fee, self.cash)
        return self.position

    def sell(self, price: float) -> float:
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
        realized = proceeds - pos.quantity * pos.entry_price

        self.cash += proceeds
        self.realized_pl += realized
        self.trade_count += 1
        if realized > 0:
            self.win_count += 1

        self._log_fill("SELL", pos.quantity, price, fee, realized_pl=realized)
        logger.info("SELL %.6f @ %.2f (fee %.4f, realized %.2f, cash %.2f)",
                    pos.quantity, price, fee, realized, self.cash)
        self.position = None
        return realized

    # ---- persistence ----
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
            if pos else None
        )
        logger.info("Loaded state: cash=%.2f position=%s", self.cash, self.position)
        return True

    def _log_fill(self, side, quantity, price, fee, realized_pl) -> None:
        path = self.config.trade_log_path
        _ensure_parent_dir(path)
        write_header = not os.path.exists(path)
        with open(path, "a", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            if write_header:
                writer.writerow(["time", "side", "quantity", "price", "fee", "realized_pl"])
            writer.writerow([_utcnow_iso(), side, f"{quantity:.8f}", f"{price:.2f}",
                             f"{fee:.6f}", f"{realized_pl:.6f}"])


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


# =========================================================================== #
# Strategy (decision engine)
# =========================================================================== #
class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


def decide(signal: Signal, price: float, position: Optional[Position],
           config: Config) -> Action:
    """Decide the action this cycle. Risk exits override the raw signal.

    Priority:
      1. In position and stop-loss breached -> SELL
      2. In position and take-profit reached -> SELL
      3. In position and signal is SELL -> SELL
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

    if signal is Signal.BUY:
        return Action.BUY
    return Action.HOLD


# =========================================================================== #
# Bot orchestration
# =========================================================================== #
@dataclass
class CycleResult:
    price: float
    signal: Signal
    action: Action
    equity: float


class TradingBot:
    def __init__(self, config: Config,
                 signal_source: Optional[SignalSource] = None,
                 price_feed: Optional[PriceFeed] = None,
                 broker: Optional[PaperBroker] = None) -> None:
        self.config = config
        self.signal_source = signal_source or TradingViewSignalSource(config)
        self.price_feed = price_feed or BinancePriceFeed(config)
        self.broker = broker or PaperBroker(config)
        self._stop = False

    def run_cycle(self) -> CycleResult:
        price = self.price_feed.get_price()
        sig = self.signal_source.get_signal()
        action = decide(sig, price, self.broker.position, self.config)

        if action is Action.BUY:
            self.broker.buy(price)
        elif action is Action.SELL:
            self.broker.sell(price)

        self.broker.save()
        equity = self.broker.equity(price)
        logger.info(
            "cycle | price=%.2f signal=%s action=%s equity=%.2f cash=%.2f pos=%s",
            price, sig.value, action.value, equity, self.broker.cash,
            "yes" if self.broker.position else "no",
        )
        return CycleResult(price=price, signal=sig, action=action, equity=equity)

    def run(self) -> None:
        self._install_signal_handlers()
        logger.info("Starting bot: symbol=%s interval=%s poll=%ds",
                    self.config.symbol, self.config.ta_interval,
                    self.config.poll_seconds)
        while not self._stop:
            try:
                self.run_cycle()
            except Exception as exc:  # noqa: BLE001 - keep the loop alive
                logger.exception("Cycle failed, will retry next interval: %s", exc)

            slept = 0.0
            while slept < self.config.poll_seconds and not self._stop:
                nap = min(1.0, self.config.poll_seconds - slept)
                time.sleep(nap)
                slept += nap

        self.broker.save()
        logger.info("Bot stopped cleanly; state saved.")

    def _install_signal_handlers(self) -> None:
        def handler(signum, _frame):
            logger.info("Received signal %s, shutting down...", signum)
            self._stop = True

        try:
            signal_module.signal(signal_module.SIGINT, handler)
            signal_module.signal(signal_module.SIGTERM, handler)
        except ValueError:
            logger.debug("Could not install signal handlers (non-main thread)")


# =========================================================================== #
# Reporting
# =========================================================================== #
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


def compute_performance(broker: PaperBroker, config: Config,
                        price: Optional[float]) -> Performance:
    pos = broker.position
    mark = price if price is not None else (pos.entry_price if pos else 0.0)
    unrealized = pos.unrealized_pl(mark) if pos else 0.0
    equity = broker.cash + (pos.value(mark) if pos else 0.0)
    total_pl = broker.realized_pl + unrealized
    start = config.starting_cash or 1.0
    win_rate = (broker.win_count / broker.trade_count * 100.0) if broker.trade_count else 0.0
    return Performance(
        cash=broker.cash, starting_cash=config.starting_cash,
        position_qty=pos.quantity if pos else 0.0,
        position_entry=pos.entry_price if pos else 0.0,
        price=price, equity=equity, realized_pl=broker.realized_pl,
        unrealized_pl=unrealized, total_pl=total_pl,
        total_return_pct=(equity - config.starting_cash) / start * 100.0,
        trade_count=broker.trade_count, win_count=broker.win_count,
        win_rate_pct=win_rate,
    )


def format_status(perf: Performance, config: Config) -> str:
    price_str = f"{perf.price:,.2f}" if perf.price is not None else "n/a (offline)"
    pos_line = (f"{perf.position_qty:.6f} @ {perf.position_entry:,.2f}"
                if perf.position_qty else "flat")
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


# =========================================================================== #
# CLI
# =========================================================================== #
def _setup_logging(config: Config) -> None:
    _ensure_parent_dir(config.log_path)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.append(RotatingFileHandler(
            config.log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"))
    except OSError:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        handlers=handlers, force=True,
    )


def _cmd_status(config: Config) -> int:
    broker = PaperBroker(config)
    broker.load()
    price = None
    try:
        price = BinancePriceFeed(config).get_price()
    except Exception as exc:  # noqa: BLE001 - status works offline too
        logger.warning("Could not fetch price: %s", exc)
    print(format_status(compute_performance(broker, config, price), config))
    return 0


def _cmd_run(config: Config, once: bool) -> int:
    broker = PaperBroker(config)
    broker.load()
    bot = TradingBot(config, broker=broker)
    if once:
        bot.run_cycle()
    else:
        bot.run()
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="eth_trading_bot",
        description="Automated ETH paper-trading bot (TradingView signals)",
    )
    parser.add_argument("command", nargs="?", default="run",
                        choices=["run", "status"],
                        help="run the bot (default) or print portfolio status")
    parser.add_argument("--once", action="store_true",
                        help="run a single cycle and exit (only valid with 'run')")
    parser.add_argument("--config", default="config.json",
                        help="path to a JSON config file (default: config.json)")
    args = parser.parse_args(argv)

    config = Config.load(args.config)
    _setup_logging(config)

    if args.command == "status":
        return _cmd_status(config)
    return _cmd_run(config, once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
