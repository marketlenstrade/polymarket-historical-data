# UFC 330

UFC 330 (Makhachev vs Machado Garry, August 15, 2026): fight winners, method of victory and round totals across the card.

| | |
|---|---|
| Series | `ufc` |
| Markets | 69 |
| Order book and trade rows | 118,566 |
| Volume | $3.5M |
| Span | 2026-08-15 21:00 to 2026-08-16 05:07 UTC |
| Size | 5.2 MB |

## Outcomes

| Market | Volume | Settled |
|---|---|---|
| UFC 330: Islam Makhachev vs. Ian Machado Garry (Welterweight, Main Card) | $2.3M | Islam Makhachev |
| UFC 330: Jalin Turner vs. Kauê Fernandes (Lightweight, Prelims) | $362K | Jalin Turner |
| UFC 330: Mackenzie Dern vs. Gillian Robertson (Women's Strawweight, Main Card) | $181K | Mackenzie Dern |
| UFC 330: Eric McConico vs. Donte Johnson (Middleweight, Early Prelims) | $152K | Donte Johnson |
| UFC 330: Edson Barboza vs. Esteban Ribovics: O/U 1.5 Rounds | $123K | Under |
| UFC 330: Charles Johnson vs. Eduardo Chapolin (Catchweight, Prelims) | $82K | Charles Johnson |
| UFC 330: Chidi Njokuani vs. Joel Álvarez (Welterweight, Prelims) | $62K | Chidi Njokuani |
| UFC 330: Chidi Njokuani vs. Joel Álvarez: O/U 1.5 Rounds | $42K | Over |
| UFC 330: Islam Makhachev vs. Ian Machado Garry: Will Islam Makhachev win by KO or TKO? | $38K | No |
| UFC 330: Dustin Stoltzfus vs. Mansur Abdul-Malik (Middleweight, Prelims) | $35K | Dustin Stoltzfus |
| UFC 330: Islam Makhachev vs. Ian Machado Garry: Will the fight be won by submission? | $33K | No |
| UFC 330: Islam Makhachev vs. Ian Machado Garry: Fight to Go the Distance? | $31K | Yes |

All 69 markets and their outcomes are in `markets.csv`.

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
with open("ufc-330-2026-08-16/markets.csv") as f:
    ids = [row["market_id"] for row in csv.DictReader(f)]
result = sdk.backtest(OpeningFader(), ids, initial_cash=10_000, data_dir="ufc-330-2026-08-16")
print(result.summary())
```

## Load with pandas

```python
import pandas as pd
markets = pd.read_csv("ufc-330-2026-08-16/markets.csv")
events = pd.read_parquet("ufc-330-2026-08-16/history-081c22e1-d521-5a76-82d9-466945085201-compact.parquet")
trades = events[events.event_type == "trade"]
books = events[events.event_type == "snapshot"]  # bids and asks are JSON strings
print(len(trades), "trades,", len(books), "books")
```

Every market since March 2026 at full resolution: [marketlens.trade](https://marketlens.trade/?utm_source=github&utm_medium=repo&utm_campaign=polymarket-historical-data).
