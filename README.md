# ETH Paper-Trading Bot (TradingView signals)

A fully automated **paper**-trading bot for ETH. It polls TradingView's own
technical-analysis consensus (BUY / SELL / NEUTRAL) as its signal, fills
simulated trades at live public-exchange prices, manages risk with
stop-loss / take-profit, and tracks a persisted paper portfolio with P&L
reporting.

> ⚠️ **Paper trading only.** This bot never connects to a brokerage, never
> holds funds, and never places real orders. It simulates an account in a local
> file. Nothing here is financial advice. Signals come from the unofficial
> [`tradingview-ta`](https://pypi.org/project/tradingview-ta/) library, which
> scrapes TradingView's public technical-analysis widget.

## How it works

Each cycle the bot:

1. **Fetches a signal** — TradingView's TA recommendation for the symbol/timeframe
   (`STRONG_BUY`/`BUY` → BUY, `SELL`/`STRONG_SELL` → SELL, `NEUTRAL` → hold).
2. **Fetches a price** — Binance public ticker (`/api/v3/ticker/price`), with an
   automatic fallback to Coinbase spot if Binance is unreachable. No API key.
3. **Decides** an action with risk priority: stop-loss and take-profit always
   override the raw signal.
4. **Executes** the simulated fill on the paper broker (taker fee applied).
5. **Persists** state atomically and appends the fill to a CSV trade log.

Long-only, one open position at a time.

### Decision rules

| State | Condition | Action |
|-------|-----------|--------|
| In position | price ≤ entry × (1 − `stop_loss_pct`) | **SELL** (stop-loss) |
| In position | price ≥ entry × (1 + `take_profit_pct`) | **SELL** (take-profit) |
| In position | signal = SELL | **SELL** |
| Flat | signal = BUY | **BUY** |
| — | otherwise | **HOLD** |

## Install

```bash
pip install -r requirements.txt
```

Requires Python 3.9+.

## Usage

```bash
python -m eth_bot            # run the continuous loop (Ctrl-C to stop cleanly)
python -m eth_bot --once     # run a single cycle, then exit (cron-friendly)
python -m eth_bot status     # print portfolio + performance
```

State is written under `state/` (git-ignored): `portfolio.json`,
`trades.csv`, and `bot.log`. Delete that folder to reset the paper account.

### Run on a schedule (cron)

`--once` is ideal for cron. Example, every 15 minutes:

```cron
*/15 * * * * cd /path/to/repo && /usr/bin/python3 -m eth_bot --once >> state/cron.log 2>&1
```

Or leave `python -m eth_bot` running under a process manager (systemd,
supervisor, `tmux`) for the built-in loop.

## Configuration

Resolution order (later wins): built-in defaults → `config.json` → environment
variables (`ETHBOT_*`).

| Key | Env | Default | Meaning |
|-----|-----|---------|---------|
| `symbol` | `ETHBOT_SYMBOL` | `ETHUSDT` | Exchange symbol for TA + price |
| `exchange` | `ETHBOT_EXCHANGE` | `BINANCE` | TradingView exchange for TA |
| `screener` | `ETHBOT_SCREENER` | `crypto` | TradingView screener |
| `ta_interval` | `ETHBOT_TA_INTERVAL` | `15m` | TA timeframe (`1m`,`5m`,`15m`,`30m`,`1h`,`2h`,`4h`,`1d`,`1W`,`1M`) |
| `poll_seconds` | `ETHBOT_POLL_SECONDS` | `900` | Seconds between cycles (loop mode) |
| `starting_cash` | `ETHBOT_STARTING_CASH` | `10000` | Initial paper cash |
| `position_size_pct` | `ETHBOT_POSITION_SIZE_PCT` | `1.0` | Fraction of equity per entry |
| `fee_pct` | `ETHBOT_FEE_PCT` | `0.001` | Taker fee per fill (0.1%) |
| `stop_loss_pct` | `ETHBOT_STOP_LOSS_PCT` | `0.03` | Stop-loss distance below entry |
| `take_profit_pct` | `ETHBOT_TAKE_PROFIT_PCT` | `0.06` | Take-profit distance above entry |

Example one-off with overrides:

```bash
ETHBOT_TA_INTERVAL=1h ETHBOT_TAKE_PROFIT_PCT=0.08 python -m eth_bot --once
```

## Testing

The core (broker, strategy, cycle) is fully unit-tested offline with fake signal
and price sources — no network required:

```bash
python -m pytest
```

## Networking notes

At runtime the machine running the bot must be able to reach
`api.binance.com` (or `api.coinbase.com`) and TradingView's scanner endpoint.
Binance's public API is geo-restricted in some regions; the bot automatically
falls back to Coinbase spot for the price feed if Binance is blocked.

## Project layout

```
eth_bot/
  config.py     # configuration (defaults + config.json + env)
  signals.py    # TradingView TA signal source
  prices.py     # Binance/Coinbase price feed
  broker.py     # simulated paper broker + persistence
  strategy.py   # decision engine (signal + risk management)
  bot.py        # cycle + continuous loop
  reporting.py  # equity / P&L / win-rate reporting
  __main__.py   # CLI (run / --once / status)
tests/          # offline unit tests
config.json     # sample configuration
```

## Disclaimer

For educational and research purposes only. Paper trading results do not
reflect real trading, which involves slippage, latency, partial fills, funding
costs, and market impact not fully modeled here. Not financial advice. Use at
your own risk.
