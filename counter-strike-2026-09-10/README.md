# Counter-Strike, one day

Counter-Strike markets that settled on September 10, 2026: match winners, map winners and map spreads from PGL Masters Bucharest and FISSURE Playground.

| | |
|---|---|
| Series | `counter-strike` |
| Markets | 385 |
| Order book and trade rows | 1,278,333 |
| Volume | $3.5M |
| Span | 2026-09-09 17:00 to 2026-09-10 23:49 UTC |
| Size | 26.3 MB |

## Outcomes

| Market | Volume | Settled |
|---|---|---|
| Counter-Strike: 1WIN vs B8 (BO3) - PGL Masters Bucharest: European Qualifier Playoffs | $668K | 1WIN |
| Counter-Strike: Alliance vs TYLOO (BO3) - FISSURE PLAYGROUND Group B | $455K | Alliance |
| Counter-Strike: Back to Back  vs Galorys (BO3) - PGL Masters Bucharest: South American Closed Qualifier Playoffs | $166K | Back to Back  |
| Counter-Strike: PARIVISION vs magic (BO3) - FISSURE PLAYGROUND Group B | $150K | magic |
| Counter-Strike: 9z vs G2 (BO3) - FISSURE PLAYGROUND Group A | $149K | G2 |
| Counter-Strike: BESTIA vs Virtus.pro (BO3) - Thunderpick World Championship Closed Qualifier Group A | $148K | Virtus.pro |
| Counter-Strike: Wildcard vs EYEBALLERS (BO3) - Thunderpick World Championship Closed Qualifier Group B | $139K | Wildcard |
| Counter-Strike: Legacy vs FURIA (BO3) - FISSURE PLAYGROUND Group B | $113K | Legacy |
| Counter-Strike: Sinners vs Nuclear TigeRES (BO3) - 1win Private Club #1: Closed Qualifier Playoffs | $112K | Sinners |
| Counter-Strike: HOTU vs Team Nemesis (BO3) - Thunderpick World Championship Closed Qualifier Group B | $103K | HOTU |
| Counter-Strike: 9z vs G2: Map Handicap: G2 (-1.5) vs 9z (+1.5) | $97K | 9z |
| Counter-Strike: ShindeN vs Turma do Pagode (BO3) - PGL Masters Bucharest: South American Closed Qualifier Playoffs | $82K | ShindeN |

All 385 markets and their outcomes are in `markets.csv`.

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
with open("counter-strike-2026-09-10/markets.csv") as f:
    ids = [row["market_id"] for row in csv.DictReader(f)]
result = sdk.backtest(OpeningFader(), ids, initial_cash=10_000, data_dir="counter-strike-2026-09-10")
print(result.summary())
```

## Load with pandas

```python
import pandas as pd
markets = pd.read_csv("counter-strike-2026-09-10/markets.csv")
events = pd.read_parquet("counter-strike-2026-09-10/history-00501c95-3df5-5bb9-8d0e-7964e181a91a-compact.parquet")
trades = events[events.event_type == "trade"]
books = events[events.event_type == "snapshot"]  # bids and asks are JSON strings
print(len(trades), "trades,", len(books), "books")
```

Every market since March 2026 at full resolution: [marketlens.trade](https://marketlens.trade/?utm_source=github&utm_medium=repo&utm_campaign=polymarket-historical-data).
