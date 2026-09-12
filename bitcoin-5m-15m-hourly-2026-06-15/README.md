# Bitcoin up or down, one day at three cadences

Every 5 minute, 15 minute and hourly Bitcoin up or down market of June 15, 2026 (UTC), with the Binance BTC trade tape of the day in reference-BTC.parquet.

| | |
|---|---|
| Series | `btc-up-or-down-5m`, `btc-up-or-down-15m`, `btc-up-or-down-hourly` |
| Markets | 408 |
| Order book and trade rows | 12,641,833 |
| Binance BTC trades | 810,680 |
| Volume | $61K |
| Span | 2026-06-15 00:00 to 2026-06-16 00:07 UTC |
| Size | 111.2 MB |

## Outcomes

| Market | Volume | Settled |
|---|---|---|
| Bitcoin Up or Down - June 15, 9:15AM-9:30AM ET | $4K | Up |
| Bitcoin Up or Down - June 15, 12:15AM-12:30AM ET | $4K | Up |
| Bitcoin Up or Down - June 15, 9:45AM-10:00AM ET | $4K | Down |
| Bitcoin Up or Down - June 15, 2:45AM-3:00AM ET | $4K | Up |
| Bitcoin Up or Down - June 15, 3:00AM-3:15AM ET | $4K | Up |
| Bitcoin Up or Down - June 15, 7:15AM-7:30AM ET | $4K | Up |
| Bitcoin Up or Down - June 15, 1:45AM-2:00AM ET | $4K | Up |
| Bitcoin Up or Down - June 15, 4:30AM-4:45AM ET | $4K | Up |
| Bitcoin Up or Down - June 15, 6:15AM-6:30AM ET | $3K | Down |
| Bitcoin Up or Down - June 15, 8:40AM-8:45AM ET | $688 | Up |
| Bitcoin Up or Down - June 15, 10:30AM-10:35AM ET | $610 | Down |
| Bitcoin Up or Down - June 15, 9:20AM-9:25AM ET | $562 | Up |

All 408 markets and their outcomes are in `markets.csv` (Up 205, Down 203).

## Files

- `history-<market>-compact.parquet`: one file per market with every order book snapshot, price level change and trade (columns in the [root README](../README.md#data-format)).
- `reference-BTC.parquet`: Binance BTC trades over the same span, read by `ctx.reference_price()` in a replay.
- `markets.csv`: question, outcomes, winning outcome, open, close and settlement times, volume, per market.
- `snapshots.csv`: best bid, best ask, midpoint, spread and depth per stored order book.

## Backtest

```python
from marketlens import MarketLens
from marketlens.backtest import Strategy

class OpeningFader(Strategy):
    def on_market_start(self, ctx, market, book):
        self._entered = False

    def on_book(self, ctx, market, book):
        if self._entered:
            return
        if book.midpoint < 0.50:
            ctx.buy_yes(size=200)
        else:
            ctx.buy_no(size=200)
        self._entered = True

sdk = MarketLens()  # reads MARKETLENS_API_KEY, a free key is enough
result = sdk.backtest(
    OpeningFader(), "btc-up-or-down-5m", initial_cash=10_000,
    after="2026-06-15T00:00:00Z", before="2026-06-16T00:00:00Z",
    data_dir="bitcoin-5m-15m-hourly-2026-06-15",
)
print(result.summary())
```

## Load with pandas

```python
import pandas as pd
markets = pd.read_csv("bitcoin-5m-15m-hourly-2026-06-15/markets.csv")
events = pd.read_parquet("bitcoin-5m-15m-hourly-2026-06-15/history-00f5adf5-00f0-5e5a-b58f-7c750b5479c0-compact.parquet")
trades = events[events.event_type == "trade"]
books = events[events.event_type == "snapshot"]  # bids and asks are JSON strings
print(len(trades), "trades,", len(books), "books")
```

Every market since March 2026 at full resolution: [marketlens.trade](https://marketlens.trade/?utm_source=github&utm_medium=repo&utm_campaign=polymarket-historical-data).
