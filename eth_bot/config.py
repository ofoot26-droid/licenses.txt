"""Bot configuration.

Resolution order (later wins): dataclass defaults -> ``config.json`` (if present)
-> environment variables prefixed with ``ETHBOT_``.

Examples::

    ETHBOT_TA_INTERVAL=1h ETHBOT_POLL_SECONDS=300 python -m eth_bot --once
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass
class Config:
    # Market / instrument
    symbol: str = "ETHUSDT"          # exchange symbol used for TA + price feed
    exchange: str = "BINANCE"        # TradingView exchange for TA lookup
    screener: str = "crypto"         # TradingView screener
    ta_interval: str = "15m"         # TA timeframe: 1m,5m,15m,30m,1h,2h,4h,1d,1W,1M

    # Loop
    poll_seconds: int = 900          # seconds between cycles in continuous mode

    # Account / sizing
    starting_cash: float = 10_000.0  # initial paper cash balance (quote currency)
    position_size_pct: float = 1.0   # fraction of equity to deploy per entry (0-1)
    fee_pct: float = 0.001           # taker fee applied to every fill (0.001 = 0.1%)

    # Risk management
    stop_loss_pct: float = 0.03      # exit if price falls this fraction below entry
    take_profit_pct: float = 0.06    # exit if price rises this fraction above entry

    # Persistence / logging
    state_path: str = "state/portfolio.json"
    trade_log_path: str = "state/trades.csv"
    log_path: str = "state/bot.log"

    # Networking
    request_timeout: float = 10.0    # seconds
    max_retries: int = 3

    @classmethod
    def load(cls, config_file: str | None = "config.json") -> "Config":
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
    """Coerce an environment string into the field's declared type."""
    hint = str(type_hint)
    if "int" in hint:
        return int(raw)
    if "float" in hint:
        return float(raw)
    if "bool" in hint:
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return raw
