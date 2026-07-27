"""Price feed: live fill prices from a free public exchange ticker.

Uses Binance's public REST endpoint (no API key). If Binance is unreachable or
geo-blocked from where the bot runs, a fallback to Coinbase's public spot price
is attempted before giving up.
"""

from __future__ import annotations

import logging
import time
from typing import Protocol

import requests

from .config import Config

logger = logging.getLogger(__name__)

_BINANCE_URL = "https://api.binance.com/api/v3/ticker/price"
_COINBASE_URL = "https://api.coinbase.com/v2/prices/{pair}/spot"


class PriceFeed(Protocol):
    """Anything that can return the current price of the configured symbol."""

    def get_price(self) -> float:  # pragma: no cover - interface
        ...


class BinancePriceFeed:
    """Live price feed using Binance public ticker, with a Coinbase fallback."""

    def __init__(self, config: Config) -> None:
        self.config = config

    def get_price(self) -> float:
        last_exc: Exception | None = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                return self._fetch_binance()
            except Exception as exc:  # noqa: BLE001 - retried below
                last_exc = exc
                logger.warning(
                    "Binance price fetch failed (attempt %d/%d): %s",
                    attempt,
                    self.config.max_retries,
                    exc,
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
        # Convert e.g. ETHUSDT -> ETH-USD (Coinbase uses USD, not USDT).
        pair = self._coinbase_pair(self.config.symbol)
        resp = requests.get(
            _COINBASE_URL.format(pair=pair),
            timeout=self.config.request_timeout,
        )
        resp.raise_for_status()
        return float(resp.json()["data"]["amount"])

    @staticmethod
    def _coinbase_pair(symbol: str) -> str:
        upper = symbol.upper()
        for quote in ("USDT", "USDC", "USD"):
            if upper.endswith(quote):
                base = upper[: -len(quote)]
                return f"{base}-USD"
        return upper
