"""Read one chapter with pandas only, no SDK and no key.

    pip install pandas pyarrow
    python examples/read_with_pandas.py
"""
import json
from pathlib import Path

import pandas as pd

FOLDER = Path(__file__).resolve().parents[1] / "ufc-330-2026-08-16"

markets = pd.read_csv(FOLDER / "markets.csv")
print(markets[["question", "winning_outcome", "volume_usd"]])

# The largest market of the chapter, every event on one time base.
top = markets.sort_values("volume_usd", ascending=False).iloc[0]
events = pd.read_parquet(FOLDER / top["file"])
events["time"] = pd.to_datetime(events["t"], unit="ms", utc=True)

trades = events[events.event_type == "trade"]
print(f"\n{top['question']}\n{len(trades):,} trades, "
      f"{len(events[events.event_type == 'delta']):,} level changes, "
      f"{len(events[events.event_type == 'snapshot']):,} full books")

# The last two sided book before settlement: bids and asks are JSON strings
# of levels, best first, and the final snapshots of a settled market are empty.
books = events[events.event_type == "snapshot"]
last = books[(books.bids != "[]") & (books.asks != "[]")].iloc[-1]
bids = json.loads(last["bids"])
asks = json.loads(last["asks"])
print(f"\nBook at {last['time']}: best bid {bids[0]['price']} x {bids[0]['size']}, "
      f"best ask {asks[0]['price']} x {asks[0]['size']}, {len(bids)} bid and {len(asks)} ask levels")

# Hourly volume weighted price from the tape.
vwap = (trades.assign(notional=trades.price * trades.size)
        .set_index("time").resample("1h")
        .agg(notional=("notional", "sum"), size=("size", "sum")))
vwap = (vwap["notional"] / vwap["size"]).dropna()
print("\nHourly VWAP, last 10 hours before settlement:")
print(vwap.tail(10).round(3))
