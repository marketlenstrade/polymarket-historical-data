# New York daily temperature, three days

The New York daily high temperature buckets for July 16, 17 and 18, 2026: eleven markets per day, one per temperature band.

| | |
|---|---|
| Series | `nyc-daily-weather` |
| Markets | 33 |
| Order book and trade rows | 319,831 |
| Span | 2026-07-14 02:07 to 2026-07-18 05:19 UTC |
| Size | 22.4 MB |

## Outcomes

| Market | Volume | Settled |
|---|---|---|
| Highest temperature in NYC on July 17?: Will the highest temperature in New York City be between 98-99°F on July 17? |  | No |
| Highest temperature in NYC on July 17?: Will the highest temperature in New York City be 100°F or higher on July 17? |  | No |
| Highest temperature in NYC on July 17?: Will the highest temperature in New York City be between 82-83°F on July 17? |  | No |
| Highest temperature in NYC on July 17?: Will the highest temperature in New York City be between 84-85°F on July 17? |  | No |
| Highest temperature in NYC on July 17?: Will the highest temperature in New York City be between 88-89°F on July 17? |  | No |
| Highest temperature in NYC on July 17?: Will the highest temperature in New York City be 81°F or below on July 17? |  | No |
| Highest temperature in NYC on July 17?: Will the highest temperature in New York City be between 96-97°F on July 17? |  | No |
| Highest temperature in NYC on July 17?: Will the highest temperature in New York City be between 94-95°F on July 17? |  | No |
| Highest temperature in NYC on July 17?: Will the highest temperature in New York City be between 92-93°F on July 17? |  | No |
| Highest temperature in NYC on July 17?: Will the highest temperature in New York City be between 86-87°F on July 17? |  | Yes |
| Highest temperature in NYC on July 17?: Will the highest temperature in New York City be between 90-91°F on July 17? |  | No |
| Highest temperature in NYC on July 16?: Will the highest temperature in New York City be between 98-99°F on July 16? |  | No |

All 33 markets and their outcomes are in `markets.csv` (No 30, Yes 3).

## Files

- `history-<market>-compact.parquet`: one file per market with every order book snapshot, price level change and trade (columns in the [root README](../README.md#data-format)).
- `markets.csv`: question, outcomes, winning outcome, open, close and settlement times, volume, per market.
- `snapshots.csv`: best bid, best ask, midpoint, spread and depth per stored order book, sampled every 5 minutes per market.

## Backtest

```python
import csv
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
with open("nyc-weather-2026-07-16/markets.csv") as f:
    ids = [row["market_id"] for row in csv.DictReader(f)]
result = sdk.backtest(OpeningFader(), ids, initial_cash=10_000, data_dir="nyc-weather-2026-07-16")
print(result.summary())
```

## Load with pandas

```python
import pandas as pd
markets = pd.read_csv("nyc-weather-2026-07-16/markets.csv")
events = pd.read_parquet("nyc-weather-2026-07-16/history-01a77489-79e6-55b6-95f0-a47778dd0bcf-compact.parquet")
trades = events[events.event_type == "trade"]
books = events[events.event_type == "snapshot"]  # bids and asks are JSON strings
print(len(trades), "trades,", len(books), "books")
```

Every market since March 2026 at full resolution: [marketlens.trade](https://marketlens.trade/?utm_source=github&utm_medium=repo&utm_campaign=polymarket-historical-data).
