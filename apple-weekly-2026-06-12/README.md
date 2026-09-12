# Apple weekly price buckets

One week of the Apple closing price buckets (week ending June 12, 2026), one market per price band.

| | |
|---|---|
| Series | `aapl-neg-risk-weekly` |
| Markets | 11 |
| Order book and trade rows | 151,639 |
| Span | 2026-06-05 22:11 to 2026-06-12 20:10 UTC |
| Size | 10.9 MB |

## Outcomes

| Market | Volume | Settled |
|---|---|---|
| Will Apple (AAPL) close at $330-$335 on the final day of trading of the week of Jun 8 – Jun 12? |  | No |
| Will Apple (AAPL) close at >$335 on the final day of trading of the week of Jun 8 – Jun 12? |  | No |
| Will Apple (AAPL) close at $315-$320 on the final day of trading of the week of Jun 8 – Jun 12? |  | No |
| Will Apple (AAPL) close at $300-$305 on the final day of trading of the week of Jun 8 – Jun 12? |  | No |
| Will Apple (AAPL) close at $295-$300 on the final day of trading of the week of Jun 8 – Jun 12? |  | No |
| Will Apple (AAPL) close at $320-$325 on the final day of trading of the week of Jun 8 – Jun 12? |  | No |
| Will Apple (AAPL) close at $310-$315 on the final day of trading of the week of Jun 8 – Jun 12? |  | No |
| Will Apple (AAPL) close at $325-$330 on the final day of trading of the week of Jun 8 – Jun 12? |  | No |
| Will Apple (AAPL) close at $305-$310 on the final day of trading of the week of Jun 8 – Jun 12? |  | No |
| Will Apple (AAPL) close at <$290 on the final day of trading of the week of Jun 8 – Jun 12? |  | No |
| Will Apple (AAPL) close at $290-$295 on the final day of trading of the week of Jun 8 – Jun 12? |  | Yes |

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
with open("apple-weekly-2026-06-12/markets.csv") as f:
    ids = [row["market_id"] for row in csv.DictReader(f)]
result = sdk.backtest(OpeningFader(), ids, initial_cash=10_000, data_dir="apple-weekly-2026-06-12")
print(result.summary())
```

## Load with pandas

```python
import pandas as pd
markets = pd.read_csv("apple-weekly-2026-06-12/markets.csv")
events = pd.read_parquet("apple-weekly-2026-06-12/history-44492cfd-eff0-55fb-91ab-839ad2874001-compact.parquet")
trades = events[events.event_type == "trade"]
books = events[events.event_type == "snapshot"]  # bids and asks are JSON strings
print(len(trades), "trades,", len(books), "books")
```

Every market since March 2026 at full resolution: [marketlens.trade](https://marketlens.trade/?utm_source=github&utm_medium=repo&utm_campaign=polymarket-historical-data).
