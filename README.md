# Polymarket Historical Data

Free Polymarket historical data: order books, trades and outcomes for 2,278 markets across 7 events, 17.3 million rows in Parquet with CSV summaries. Each folder is one event with the markets that traded in it, from the first recorded order book to settlement, in the format the [Marketlens](https://marketlens.trade/?utm_source=github&utm_medium=repo&utm_campaign=polymarket-historical-data) SDK reads, so a folder can be backtested offline with `pip install marketlens`.

Polymarket's API returns the order book as it is now, not as it was. Marketlens has recorded every order book update on Polymarket since March 1, 2026; this repository is a sample of that archive.

## Events

| Event | Series | Date | Markets | Rows | Size |
|---|---|---|---|---|---|
| [Bitcoin up or down, one day at three cadences](bitcoin-5m-15m-hourly-2026-06-15/) | btc-up-or-down-5m, btc-up-or-down-15m, btc-up-or-down-hourly | 2026-06-15 | 408 | 12,641,833 | 111.2 MB |
| [MLB, one full day](mlb-2026-07-05/) | mlb | 2026-07-05 | 814 | 994,332 | 19.7 MB |
| [World Cup final day](world-cup-final-2026-07-19/) | soccer-fifwc | 2026-07-19 | 558 | 1,813,340 | 35.6 MB |
| [UFC 330](ufc-330-2026-08-16/) | ufc | 2026-08-16 | 69 | 118,566 | 5.2 MB |
| [Counter-Strike, one day](counter-strike-2026-09-10/) | counter-strike | 2026-09-10 | 385 | 1,278,333 | 26.3 MB |
| [New York daily temperature, three days](nyc-weather-2026-07-16/) | nyc-daily-weather | 2026-07-16 | 33 | 319,831 | 22.4 MB |
| [Apple weekly price buckets](apple-weekly-2026-06-12/) | aapl-neg-risk-weekly | 2026-06-12 | 11 | 151,639 | 10.9 MB |

## Download

```bash
git clone --depth 1 https://github.com/marketlenstrade/polymarket-historical-data.git
```

Single files load straight from the raw URL:

```python
import pandas as pd
url = "https://raw.githubusercontent.com/marketlenstrade/polymarket-historical-data/main/bitcoin-5m-15m-hourly-2026-06-15/markets.csv"
markets = pd.read_csv(url)
```

## Backtest with the Marketlens SDK

A free API key from [marketlens.trade](https://marketlens.trade/?utm_source=github&utm_medium=repo&utm_campaign=polymarket-historical-data) is enough: the SDK reads the order book rows from the folder and asks the API only for market metadata, which is not metered.

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

## Data format

Each `history-<market>-compact.parquet` holds one market's history on a single time base:

| Column | Type | Meaning |
|---|---|---|
| `event_type` | string | `snapshot` (full book), `delta` (one price level changed), `trade` |
| `t` | int64 | Milliseconds since the epoch, UTC |
| `price`, `size` | float64 | The level that changed or the fill; `size` 0 removes a level |
| `side` | string | `BUY` (bid side) or `SELL` (ask side) |
| `trade_id` | string | Trades only |
| `is_reseed` | bool | Snapshot taken after a reconnect |
| `bids`, `asks` | string | JSON list of `{"price", "size"}` levels, best first, snapshots only |

To rebuild the book at any time, take the last snapshot at or before it and apply the deltas that follow in order. This is the trade aligned compact variant: the book is exact at every trade and every snapshot, and level changes between trades are folded together. Every folder also has `markets.csv` (question, outcomes, winning outcome, times, volume) and `snapshots.csv` (best bid, best ask, midpoint, spread, depth per stored book). Crypto folders carry `reference-BTC.parquet`, the Binance trade tape over the same span.

```python
import pandas as pd
markets = pd.read_csv("bitcoin-5m-15m-hourly-2026-06-15/markets.csv")
events = pd.read_parquet("bitcoin-5m-15m-hourly-2026-06-15/history-00f5adf5-00f0-5e5a-b58f-7c750b5479c0-compact.parquet")
trades = events[events.event_type == "trade"]
books = events[events.event_type == "snapshot"]  # bids and asks are JSON strings
print(len(trades), "trades,", len(books), "books")
```

## Full archive

[`archive-index.csv`](archive-index.csv) lists the 924 recurring series Marketlens collects: crypto up or down markets at every cadence, sports leagues, esports, weather cities, equities, commodities and economic releases, plus the large one-off events. The full archive is available through the [Marketlens API](https://marketlens.trade/?utm_source=github&utm_medium=repo&utm_campaign=polymarket-historical-data), with Parquet exports by series and time window, candles, order book metrics and the backtest engine. A free key covers 25 million rows a day.

More samples: [Bitcoin 5 minute L2 depth, one day](https://huggingface.co/datasets/marketlens/polymarket-btc-5m-l2-depth), [the 2026 World Cup final](https://huggingface.co/datasets/marketlens/polymarket-world-cup-final-2026) and [every resolved market with its outcome](https://huggingface.co/datasets/marketlens/polymarket-resolved-markets) on Hugging Face.

## FAQ

**Does Polymarket provide historical data?** Not for the order book. The Gamma and CLOB APIs return live markets and the current book, and the prices history endpoint returns a sampled price line. Order book history exists only where it was recorded while the market was live.

**Is the data available as CSV?** Yes: `markets.csv` and `snapshots.csv` in every folder. The Parquet files open with pandas, DuckDB, Polars or R.

**Can I backtest Polymarket strategies on this?** Yes. Pass a folder as `data_dir` to `client.backtest` and the engine replays the books tick by tick with simulated fills, queue position, latency and fees. Each folder's README has the exact call.

## License

Data is released under [CC BY 4.0](LICENSE); attribute as "Marketlens, https://marketlens.trade". Citation details are in [`CITATION.cff`](CITATION.cff). Built with [`tools/build.py`](tools/build.py) from [`targets.json`](targets.json) using SDK 1.8.3.
