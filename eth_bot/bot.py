"""Bot orchestration: one cycle and the continuous run loop.

Dependencies (signal source, price feed, broker) are injected so the core logic
is fully testable offline with fakes.
"""

from __future__ import annotations

import logging
import signal as signal_module
import time
from dataclasses import dataclass
from typing import Optional

from .config import Config
from .signals import Signal, SignalSource, TradingViewSignalSource
from .prices import PriceFeed, BinancePriceFeed
from .broker import PaperBroker
from .strategy import Action, decide

logger = logging.getLogger(__name__)


@dataclass
class CycleResult:
    price: float
    signal: Signal
    action: Action
    equity: float


class TradingBot:
    def __init__(
        self,
        config: Config,
        signal_source: Optional[SignalSource] = None,
        price_feed: Optional[PriceFeed] = None,
        broker: Optional[PaperBroker] = None,
    ) -> None:
        self.config = config
        self.signal_source = signal_source or TradingViewSignalSource(config)
        self.price_feed = price_feed or BinancePriceFeed(config)
        self.broker = broker or PaperBroker(config)
        self._stop = False

    def run_cycle(self) -> CycleResult:
        """Fetch inputs, decide, execute, persist, and log one iteration."""
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
            price,
            sig.value,
            action.value,
            equity,
            self.broker.cash,
            "yes" if self.broker.position else "no",
        )
        return CycleResult(price=price, signal=sig, action=action, equity=equity)

    def run(self) -> None:
        """Run cycles forever, sleeping ``poll_seconds`` between them.

        Handles SIGINT/SIGTERM by finishing gracefully and saving state.
        """
        self._install_signal_handlers()
        logger.info(
            "Starting bot: symbol=%s interval=%s poll=%ds",
            self.config.symbol,
            self.config.ta_interval,
            self.config.poll_seconds,
        )
        while not self._stop:
            try:
                self.run_cycle()
            except Exception as exc:  # noqa: BLE001 - keep the loop alive
                logger.exception("Cycle failed, will retry next interval: %s", exc)

            # Sleep in short slices so shutdown is responsive.
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
            # Not on the main thread (e.g. under some test runners) - skip.
            logger.debug("Could not install signal handlers (non-main thread)")
