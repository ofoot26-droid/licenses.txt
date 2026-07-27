"""CLI entrypoint.

    python -m eth_bot            # run the continuous trading loop
    python -m eth_bot --once     # run exactly one cycle, then exit (cron-friendly)
    python -m eth_bot status     # print portfolio + performance and exit
"""

from __future__ import annotations

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler

from .config import Config
from .broker import PaperBroker
from .bot import TradingBot
from .prices import BinancePriceFeed
from .reporting import compute_performance, format_status
from .broker import _ensure_parent_dir


def _setup_logging(config: Config) -> None:
    _ensure_parent_dir(config.log_path)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    try:
        handlers.append(
            RotatingFileHandler(
                config.log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
            )
        )
    except OSError:
        pass  # stdout logging is enough if the file can't be opened
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
        handlers=handlers,
        force=True,
    )


def _cmd_status(config: Config) -> int:
    broker = PaperBroker(config)
    broker.load()
    price = None
    try:
        price = BinancePriceFeed(config).get_price()
    except Exception as exc:  # noqa: BLE001 - status works offline too
        logging.getLogger(__name__).warning("Could not fetch price: %s", exc)
    perf = compute_performance(broker, config, price)
    print(format_status(perf, config))
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="eth_bot", description="Automated ETH paper-trading bot (TradingView signals)"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="run",
        choices=["run", "status"],
        help="run the bot (default) or print portfolio status",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="run a single cycle and exit (only valid with 'run')",
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="path to a JSON config file (default: config.json)",
    )
    args = parser.parse_args(argv)

    config = Config.load(args.config)
    _setup_logging(config)

    if args.command == "status":
        return _cmd_status(config)
    return _cmd_run(config, once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
