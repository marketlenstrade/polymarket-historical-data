# World Cup final day

World Cup markets that settled on the day of the final (Spain vs Argentina, July 19, 2026): winner, exact score, totals, corners, halves and player props.

| | |
|---|---|
| Series | `soccer-fifwc` |
| Markets | 558 |
| Order book and trade rows | 1,813,340 |
| Volume | $140.9M |
| Span | 2026-07-18 21:00 to 2026-07-19 22:54 UTC |
| Size | 35.6 MB |

## Outcomes

| Market | Volume | Settled |
|---|---|---|
| Spain vs. Argentina - More Markets: Spain vs. Argentina: Team to Advance | $15.0M | Spain |
| Spain vs. Argentina - Exact Score: Exact Score: Spain 2 - 3 Argentina? | $13.2M | No |
| Spain vs. Argentina - Exact Score: Exact Score: Spain 3 - 3 Argentina? | $7.1M | No |
| France vs. England: Will France win on 2026-07-18? | $7.0M | No |
| Spain vs. Argentina: Will Argentina win on 2026-07-19? | $6.3M | No |
| France vs. England - More Markets: France vs. England: Team to Win | $6.0M | England |
| Spain vs. Argentina: Will Spain win on 2026-07-19? | $5.5M | No |
| Spain vs. Argentina - Exact Score: Exact Score: Spain 3 - 2 Argentina? | $4.2M | No |
| Spain vs. Argentina - More Markets: Spain vs. Argentina: O/U 2.5 | $3.4M | Under |
| Spain vs. Argentina - More Markets: Spread: Spain (-1.5) | $3.2M | Argentina |
| Spain vs. Argentina - Exact Score: Exact Score: Spain 2 - 2 Argentina? | $2.8M | No |
| Spain vs. Argentina - Exact Score: Exact Score: Spain 1 - 3 Argentina? | $2.8M | No |

All 558 markets and their outcomes are in `markets.csv`.

## Files

- `history-<market>-compact.parquet`: one file per market with every order book snapshot, price level change and trade (columns in the [root README](../README.md#data-format)).
- `markets.csv`: question, outcomes, winning outcome, open, close and settlement times, volume, per market.
- `snapshots.csv`: best bid, best ask, midpoint, spread and depth per stored order book.

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
with open("world-cup-final-2026-07-19/markets.csv") as f:
    ids = [row["market_id"] for row in csv.DictReader(f)]
result = sdk.backtest(OpeningFader(), ids, initial_cash=10_000, data_dir="world-cup-final-2026-07-19")
print(result.summary())
```

## Load with pandas

```python
import pandas as pd
markets = pd.read_csv("world-cup-final-2026-07-19/markets.csv")
events = pd.read_parquet("world-cup-final-2026-07-19/history-0001cbf5-1e18-5ee3-ad21-0b2072303f98-compact.parquet")
trades = events[events.event_type == "trade"]
books = events[events.event_type == "snapshot"]  # bids and asks are JSON strings
print(len(trades), "trades,", len(books), "books")
```

Every market since March 2026 at full resolution: [marketlens.trade](https://marketlens.trade/?utm_source=github&utm_medium=repo&utm_campaign=polymarket-historical-data).
