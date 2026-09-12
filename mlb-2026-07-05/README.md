# MLB, one full day

Every MLB market that settled on July 5, 2026: moneylines, run lines, totals and first five innings for the full slate.

| | |
|---|---|
| Series | `mlb` |
| Markets | 814 |
| Order book and trade rows | 994,332 |
| Volume | $2.8M |
| Span | 2026-07-04 23:10 to 2026-07-05 23:50 UTC |
| Size | 19.7 MB |

## Outcomes

| Market | Volume | Settled |
|---|---|---|
| Tampa Bay Rays vs. Houston Astros | $316K | Houston Astros |
| Miami Marlins vs. Athletics | $289K | Miami Marlins |
| Baltimore Orioles vs. Cincinnati Reds | $181K | Baltimore Orioles |
| San Francisco Giants vs. Colorado Rockies: O/U 12.5 | $152K | Over |
| New York Mets vs. Atlanta Braves | $107K | New York Mets |
| Boston Red Sox vs. Los Angeles Angels | $95K | Boston Red Sox |
| Boston Red Sox vs. Los Angeles Angels: Spread: Boston Red Sox (-1.5) | $88K | Boston Red Sox |
| New York Mets vs. Atlanta Braves | $84K | Atlanta Braves |
| San Francisco Giants vs. Colorado Rockies | $75K | Colorado Rockies |
| Tampa Bay Rays vs. Houston Astros | $73K | Houston Astros |
| Minnesota Twins vs. New York Yankees: O/U 8.5 | $72K | Under |
| Chicago White Sox vs. Cleveland Guardians | $72K | Chicago White Sox |

All 814 markets and their outcomes are in `markets.csv`.

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
with open("mlb-2026-07-05/markets.csv") as f:
    ids = [row["market_id"] for row in csv.DictReader(f)]
result = sdk.backtest(OpeningFader(), ids, initial_cash=10_000, data_dir="mlb-2026-07-05")
print(result.summary())
```

## Load with pandas

```python
import pandas as pd
markets = pd.read_csv("mlb-2026-07-05/markets.csv")
events = pd.read_parquet("mlb-2026-07-05/history-005980df-3a4b-5463-a4d7-6c0eb6905666-compact.parquet")
trades = events[events.event_type == "trade"]
books = events[events.event_type == "snapshot"]  # bids and asks are JSON strings
print(len(trades), "trades,", len(books), "books")
```

Every market since March 2026 at full resolution: [marketlens.trade](https://marketlens.trade/?utm_source=github&utm_medium=repo&utm_campaign=polymarket-historical-data).
