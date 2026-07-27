"""Signal source: TradingView technical-analysis consensus.

Wraps the unofficial ``tradingview-ta`` library. The library scrapes the same
BUY / SELL / NEUTRAL recommendation TradingView shows on its charts. On any
failure we log and return NEUTRAL so a transient network blip never crashes the
trading loop.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Protocol

from .config import Config

logger = logging.getLogger(__name__)


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


# Map TradingView's granular recommendation strings to our 3-state signal.
_RECOMMENDATION_MAP = {
    "STRONG_BUY": Signal.BUY,
    "BUY": Signal.BUY,
    "NEUTRAL": Signal.NEUTRAL,
    "SELL": Signal.SELL,
    "STRONG_SELL": Signal.SELL,
}


class SignalSource(Protocol):
    """Anything that can produce a trading signal for the configured symbol."""

    def get_signal(self) -> Signal:  # pragma: no cover - interface
        ...


def _resolve_interval(interval: str):
    """Map a human interval string (e.g. ``15m``) to a tradingview_ta Interval."""
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
            signal = _RECOMMENDATION_MAP.get(recommendation.upper(), Signal.NEUTRAL)
            logger.debug(
                "TradingView recommendation=%s -> signal=%s (summary=%s)",
                recommendation,
                signal.value,
                analysis.summary,
            )
            return signal
        except Exception as exc:  # noqa: BLE001 - never let signals crash the loop
            logger.warning("Failed to fetch TradingView signal, holding: %s", exc)
            return Signal.NEUTRAL
