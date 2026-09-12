"""Replay the UFC 330 chapter with the Marketlens SDK.

    pip install marketlens
    export MARKETLENS_API_KEY=mk_...   # a free key is enough
    python examples/replay_ufc.py

The order book rows come from the folder; the API is asked only for market
metadata, which costs no data rows.
"""
import csv
from pathlib import Path

from marketlens import MarketLens
from marketlens.backtest import Strategy

FOLDER = Path(__file__).resolve().parents[1] / "ufc-330-2026-08-16"


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


with (FOLDER / "markets.csv").open() as f:
    ids = [row["market_id"] for row in csv.DictReader(f)]

sdk = MarketLens()
result = sdk.backtest(OpeningFader(), ids, initial_cash=10_000, data_dir=str(FOLDER))
print(result.summary())
