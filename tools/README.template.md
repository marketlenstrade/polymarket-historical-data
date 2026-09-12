# Polymarket Historical Data

Free Polymarket historical data: order books, trades and outcomes for {{MARKETS}} markets across {{CHAPTERS}} events, {{ROWS_COMPACT}} rows in Parquet with CSV summaries. Each folder is one event with the markets that traded in it, from the first recorded order book to settlement, in the format the [Marketlens](https://marketlens.trade/?{{UTM}}) SDK reads, so a folder can be backtested offline with `pip install marketlens`.

Polymarket's API returns the order book as it is now, not as it was. Marketlens has recorded every order book update on Polymarket since March 1, 2026; this repository is a sample of that archive.

## Events

| Event | Series | Date | Markets | Rows | Size |
|---|---|---|---|---|---|
{{CHAPTER_TABLE}}

## Download

```bash
git clone --depth 1 https://github.com/marketlenstrade/polymarket-historical-data.git
```

Single files load straight from the raw URL:

```python
import pandas as pd
url = "https://raw.githubusercontent.com/marketlenstrade/polymarket-historical-data/main/{{FIRST_FOLDER}}/markets.csv"
markets = pd.read_csv(url)
```

## Backtest with the Marketlens SDK

A free API key from [marketlens.trade](https://marketlens.trade/?{{UTM}}) is enough: the SDK reads the order book rows from the folder and asks the API only for market metadata, which is not metered.

```python
{{REPLAY_EXAMPLE}}
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
{{PANDAS_EXAMPLE}}
```

## Full archive

[`archive-index.csv`](archive-index.csv) lists the {{SERIES_COUNT}} recurring series Marketlens collects: crypto up or down markets at every cadence, sports leagues, esports, weather cities, equities, commodities and economic releases, plus the large one-off events. The full archive is available through the [Marketlens API](https://marketlens.trade/?{{UTM}}), with Parquet exports by series and time window, candles, order book metrics and the backtest engine. A free key covers 25 million rows a day.

More samples: [Bitcoin 5 minute L2 depth, one day](https://huggingface.co/datasets/marketlens/polymarket-btc-5m-l2-depth), [the 2026 World Cup final](https://huggingface.co/datasets/marketlens/polymarket-world-cup-final-2026) and [every resolved market with its outcome](https://huggingface.co/datasets/marketlens/polymarket-resolved-markets) on Hugging Face.

## FAQ

**Does Polymarket provide historical data?** Not for the order book. The Gamma and CLOB APIs return live markets and the current book, and the prices history endpoint returns a sampled price line. Order book history exists only where it was recorded while the market was live.

**Is the data available as CSV?** Yes: `markets.csv` and `snapshots.csv` in every folder. The Parquet files open with pandas, DuckDB, Polars or R.

**Can I backtest Polymarket strategies on this?** Yes. Pass a folder as `data_dir` to `client.backtest` and the engine replays the books tick by tick with simulated fills, queue position, latency and fees. Each folder's README has the exact call.

## License

Data is released under [CC BY 4.0](LICENSE); attribute as "Marketlens, https://marketlens.trade". Citation details are in [`CITATION.cff`](CITATION.cff). Built with [`tools/build.py`](tools/build.py) from [`targets.json`](targets.json) using SDK {{SDK_VERSION}}.
