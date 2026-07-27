"""Fully automated ETH paper-trading bot driven by TradingView signals.

Paper trading only. Nothing in this package touches real funds or places real
orders. Signals come from TradingView's technical-analysis consensus (via the
unofficial ``tradingview-ta`` library) and fills are simulated at live public
exchange ticker prices.
"""

__version__ = "0.1.0"

from .config import Config
from .signals import Signal, SignalSource, TradingViewSignalSource
from .prices import PriceFeed, BinancePriceFeed
from .broker import PaperBroker, Position
from .strategy import Action, decide
from .bot import TradingBot

__all__ = [
    "Config",
    "Signal",
    "SignalSource",
    "TradingViewSignalSource",
    "PriceFeed",
    "BinancePriceFeed",
    "PaperBroker",
    "Position",
    "Action",
    "decide",
    "TradingBot",
]
