"""Build the chapters of this repository from the Marketlens API.

Every folder is the output of documented SDK calls (``exports.download_series``
for rolling series, ``exports.download`` per market otherwise), so what you find
here is exactly what ``pip install marketlens`` gives you for the same window.

    export MARKETLENS_API_KEY=mk_...
    python tools/build.py                 # build every chapter in targets.json
    python tools/build.py --chapter fomc-2026-03-18
    python tools/build.py --dry-run       # list the markets, download nothing
    python tools/build.py --index         # refresh archive-index.csv only
    python tools/build.py --render        # rewrite manifest.json and the READMEs

A chapter is whole or absent: the build stops if any market of it is still
building on the server, failed, or was held back by the account's row balance.
Exports charge data rows once per market and account; re-running is free.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pyarrow.parquet as pq

from marketlens import MarketLens
from marketlens._base import _coerce_timestamp
from marketlens.exceptions import ExportNotReadyError

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ROOT / "targets.json"
MANIFEST = ROOT / "manifest.json"
TEMPLATE = ROOT / "tools" / "README.template.md"
INDEX = ROOT / "archive-index.csv"

SITE = "https://marketlens.trade"
UTM = "utm_source=github&utm_medium=repo&utm_campaign=polymarket-historical-data"
CONCURRENCY = 6


def iso(ms: int | None) -> str:
    if ms is None:
        return ""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def day(ms: int | None) -> str:
    return iso(ms)[:10]


def fmt_int(n: int) -> str:
    return f"{n:,}"


def fmt_bytes(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f} GB"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f} MB"
    return f"{n / 1000:.0f} KB"


def fmt_usd(v: float) -> str:
    if v >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v / 1000:.0f}K"
    return f"${v:.0f}"


# --- market selection ---------------------------------------------------------

def select_markets(sdk: MarketLens, chapter: dict) -> list:
    """The markets a chapter covers, as SDK Market objects."""
    if chapter["mode"] == "series_window":
        out = []
        for slug in chapter["series"]:
            out.extend(sdk.series.walk(slug, after=chapter["after"], before=chapter["before"]))
        return out
    if chapter["mode"] == "market_list":
        before = _coerce_timestamp(chapter["resolved_before"]) - 1
        found = sdk.markets.list(
            series_id=chapter["series"], status="resolved",
            resolved_after=chapter["resolved_after"], resolved_before=before,
            limit=2000,
        ).to_list()
        return [m for m in found if m.winning_outcome is not None]
    raise ValueError(f"unknown mode {chapter['mode']!r}")


# --- downloads ----------------------------------------------------------------

def download_reference(sdk: MarketLens, folder: Path, symbol: str, markets: list) -> None:
    """The underlying's Binance trade tape over the chapter's whole span, one
    file. Fetched before the market files so the SDK's own per-window
    reference fetch finds it and leaves it alone."""
    dest = folder / f"reference-{symbol}.parquet"
    if dest.exists():
        return
    opens = [m.open_time for m in markets if m.open_time]
    closes = [m.close_time for m in markets if m.close_time]
    after = min(opens) - 60_000
    before = max(closes)
    sdk._http.download("/reference/trades/export", dest,
                         params={"symbol": symbol, "after": after, "before": before})


def download_chapter(sdk: MarketLens, chapter: dict, folder: Path, markets: list) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    ref = chapter.get("reference")
    if ref:
        download_reference(sdk, folder, ref, markets)

    if chapter["mode"] == "series_window":
        for slug in chapter["series"]:
            r = sdk.exports.download_series(
                slug, after=chapter["after"], before=chapter["before"],
                data_dir=folder, concurrency=CONCURRENCY, progress=False,
            )
            problems = [e.market_id for e in r.pending + r.failed + r.rate_limited]
            if problems:
                sys.exit(f"{chapter['folder']}: {slug} has {len(problems)} markets not delivered "
                         f"(pending {len(r.pending)}, failed {len(r.failed)}, rate limited {len(r.rate_limited)})")
        return

    def one(m):
        dest = folder / f"history-{m.id}-compact.parquet"
        if dest.exists():
            return None
        # The redirect download alone: the SDK's ``exports.download`` would
        # also fetch a reference tape per market, which for a month long
        # market is the whole month of spot trades. The object store stalls
        # now and then, so a 5xx on the file fetch is retried.
        for attempt in range(4):
            try:
                sdk._http.download_via_redirect(f"/markets/{m.id}/export", dest,
                                                  params={"coalesce": "true"})
                return None
            except ExportNotReadyError as exc:
                return f"{m.id}: {exc}"
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500 or attempt == 3:
                    return f"{m.id}: HTTP {exc.response.status_code}"
                dest.unlink(missing_ok=True)
                time.sleep(3 * (attempt + 1))
        return None

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        errors = [e for e in ex.map(one, markets) if e]
    if errors:
        sys.exit(f"{chapter['folder']}: {len(errors)} markets not ready:\n" + "\n".join(errors[:10]))


# --- derived files ------------------------------------------------------------

MARKET_COLUMNS = [
    "market_id", "condition_id", "series", "event", "subtype", "question", "outcomes",
    "winning_outcome", "open_time", "close_time", "resolved_at", "volume_usd",
    "data_start", "data_end", "file",
]


def write_markets_csv(folder: Path, markets: list, series_of: dict) -> None:
    with (folder / "markets.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(MARKET_COLUMNS)
        for m in sorted(markets, key=lambda m: (m.open_time or 0, m.id)):
            w.writerow([
                m.id, m.platform_market_id, series_of.get(m.id, ""), m.event_title or "", m.subtype or "",
                m.question, "|".join(o.name for o in m.outcomes), m.winning_outcome or "",
                iso(m.open_time), iso(m.close_time), iso(m.resolved_at),
                f"{m.volume:.2f}", iso(m.data_start), iso(m.data_end),
                f"history-{m.id}-compact.parquet",
            ])


def _levels(raw) -> list[tuple[float, float]]:
    if not raw:
        return []
    levels = json.loads(raw) if isinstance(raw, str) else raw
    out = []
    for lv in levels:
        if isinstance(lv, dict):
            out.append((float(lv["price"]), float(lv["size"])))
        else:
            out.append((float(lv[0]), float(lv[1])))
    return out


SNAPSHOTS_CSV_MAX_BYTES = 10_000_000
SNAPSHOT_CADENCES_SEC = (0, 300, 900, 3600)


def write_snapshots_csv(folder: Path, markets: list) -> tuple[int, int]:
    """One row per stored book: the top of book and the depth each side,
    read straight off the snapshot rows of every market file. Long lived
    chapters would make this CSV larger than the parquet it summarises, so
    when the full rate file passes SNAPSHOTS_CSV_MAX_BYTES it is rewritten
    at the first cadence (seconds) that fits; the parquet keeps every book.
    Returns (rows, cadence_sec), cadence 0 meaning every stored book."""
    dest = folder / "snapshots.csv"
    for cadence in SNAPSHOT_CADENCES_SEC:
        n = _write_snapshots(dest, folder, markets, cadence)
        if dest.stat().st_size <= SNAPSHOTS_CSV_MAX_BYTES or cadence == SNAPSHOT_CADENCES_SEC[-1]:
            return n, cadence
    return n, cadence  # pragma: no cover


def _write_snapshots(dest: Path, folder: Path, markets: list, cadence_sec: int) -> int:
    n = 0
    bucket_ms = cadence_sec * 1000
    with dest.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["market_id", "time", "t_ms", "best_bid", "best_ask", "midpoint", "spread",
                    "bid_depth", "ask_depth", "bid_levels", "ask_levels"])
        for m in sorted(markets, key=lambda m: (m.open_time or 0, m.id)):
            path = folder / f"history-{m.id}-compact.parquet"
            tbl = pq.read_table(path, columns=["event_type", "t", "bids", "asks"])
            last_bucket = None
            for et, t, bids, asks in zip(*(tbl.column(c).to_pylist() for c in ("event_type", "t", "bids", "asks"))):
                if et != "snapshot":
                    continue
                if bucket_ms:
                    bucket = t // bucket_ms
                    if bucket == last_bucket:
                        continue
                    last_bucket = bucket
                b, a = _levels(bids), _levels(asks)
                bb = max((p for p, _ in b), default=None)
                ba = min((p for p, _ in a), default=None)
                mid = (bb + ba) / 2 if bb is not None and ba is not None else None
                spread = ba - bb if bb is not None and ba is not None else None
                w.writerow([
                    m.id, iso(t), t,
                    "" if bb is None else f"{bb:.4f}", "" if ba is None else f"{ba:.4f}",
                    "" if mid is None else f"{mid:.4f}", "" if spread is None else f"{spread:.4f}",
                    f"{sum(s for _, s in b):.2f}", f"{sum(s for _, s in a):.2f}", len(b), len(a),
                ])
                n += 1
    return n


GAP_MINUTES = 5   # a live market gets a book every 34 s median (p99 83 s); longer silence is a gap


def market_gaps(path: Path) -> list[tuple[int, int]]:
    """Silences longer than GAP_MINUTES between consecutive book snapshots."""
    tbl = pq.read_table(path, columns=["event_type", "t"])
    ts = sorted(t for et, t in zip(tbl.column("event_type").to_pylist(), tbl.column("t").to_pylist())
                if et == "snapshot")
    return [(a, b) for a, b in zip(ts, ts[1:]) if b - a > GAP_MINUTES * 60_000]


def keep_complete(folder: Path, markets: list) -> tuple[list, list]:
    """Only markets recorded without interruption ship. Returns (kept, dropped);
    a dropped market's file is removed from the folder."""
    kept, dropped = [], []
    for m in markets:
        path = folder / f"history-{m.id}-compact.parquet"
        tbl = pq.read_table(path, columns=["event_type"])
        if tbl.num_rows == 0 or market_gaps(path):
            dropped.append(m)
            path.unlink()
        else:
            kept.append(m)
    return kept, dropped


def file_facts(path: Path) -> dict:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    rows = pq.ParquetFile(path).metadata.num_rows if path.suffix == ".parquet" else None
    if rows is None:
        with path.open() as f:
            rows = sum(1 for _ in f) - 1
    return {"file": path.name, "rows": rows, "bytes": path.stat().st_size, "sha256": h.hexdigest()}


def _labelled(m) -> str:
    """A generic question ("O/U 1.5 Rounds") prefixed with its event, the
    event title cut before its first parenthesis."""
    title = (m.event_title or "").split(" (")[0].strip()
    if title and title[:20] not in m.question:
        return f"{title}: {m.question}"
    return m.question


def chapter_facts(chapter: dict, folder: Path, markets: list, series_of: dict, snapshot_cadence_sec: int = 0) -> dict:
    files = sorted(folder.glob("*.parquet")) + sorted(folder.glob("*.csv"))
    facts = [file_facts(p) for p in files]
    history = [f for f in facts if f["file"].startswith("history-")]
    reference = [f for f in facts if f["file"].startswith("reference-")]
    counts: dict[str, int] = {}
    for m in markets:
        counts[m.winning_outcome or "unresolved"] = counts.get(m.winning_outcome or "unresolved", 0) + 1
    data_start = min((m.data_start for m in markets if m.data_start), default=None)
    data_end = max((m.data_end for m in markets if m.data_end), default=None)
    top = sorted(markets, key=lambda m: -(m.volume or 0))[:12]
    return {
        "folder": chapter["folder"],
        "title": chapter["title"],
        "blurb": chapter["blurb"],
        "mode": chapter["mode"],
        "series": chapter["series"] if isinstance(chapter["series"], list) else [chapter["series"]],
        "window": {k: chapter[k] for k in ("after", "before", "resolved_after", "resolved_before") if k in chapter},
        "reference": chapter.get("reference"),
        "note": chapter.get("note"),
        "markets": len(markets),
        "volume_usd": round(sum(m.volume or 0 for m in markets), 2),
        "markets_without_volume": sum(1 for m in markets if not m.volume),
        "rows": sum(f["rows"] for f in history),
        "reference_rows": sum(f["rows"] for f in reference),
        "bytes": sum(f["bytes"] for f in facts),
        "history_bytes": sum(f["bytes"] for f in history),
        "largest_file_bytes": max(f["bytes"] for f in facts),
        "data_start": iso(data_start),
        "data_end": iso(data_end),
        "outcomes": counts,
        "snapshot_cadence_sec": snapshot_cadence_sec,
        "top_markets": [
            {"question": _labelled(m),
             "volume_usd": round(m.volume or 0, 2),
             "winning_outcome": m.winning_outcome, "series": series_of.get(m.id, "")}
            for m in top
        ],
        "files": facts,
    }


# --- readme rendering ---------------------------------------------------------

STRATEGY = '''from marketlens import MarketLens
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

sdk = MarketLens()  # reads MARKETLENS_API_KEY, a free key is enough'''


def replay_snippet(ch: dict) -> str:
    folder = ch["folder"]
    if ch["mode"] == "series_window":
        w = ch["window"]
        return (
            f"{STRATEGY}\n"
            f"result = sdk.backtest(\n"
            f"    OpeningFader(), \"{ch['series'][0]}\", initial_cash=10_000,\n"
            f"    after=\"{w['after']}\", before=\"{w['before']}\",\n"
            f"    data_dir=\"{folder}\",\n"
            f")\n"
            f"print(result.summary())"
        )
    return (
        f"import csv\n"
        f"{STRATEGY}\n"
        f"with open(\"{folder}/markets.csv\") as f:\n"
        f"    ids = [row[\"market_id\"] for row in csv.DictReader(f)]\n"
        f"result = sdk.backtest(OpeningFader(), ids, initial_cash=10_000, data_dir=\"{folder}\")\n"
        f"print(result.summary())"
    )


def pandas_snippet(ch: dict, first_file: str) -> str:
    return (
        "import pandas as pd\n"
        f"markets = pd.read_csv(\"{ch['folder']}/markets.csv\")\n"
        f"events = pd.read_parquet(\"{ch['folder']}/{first_file}\")\n"
        "trades = events[events.event_type == \"trade\"]\n"
        "books = events[events.event_type == \"snapshot\"]  # bids and asks are JSON strings\n"
        "print(len(trades), \"trades,\", len(books), \"books\")"
    )


def render_chapter_readme(ch: dict) -> str:
    series = ", ".join(f"`{s}`" for s in ch["series"])
    first_file = next(f["file"] for f in ch["files"] if f["file"].startswith("history-"))
    lines = [
        f"# {ch['title']}",
        "",
        ch["blurb"],
        "",
        "| | |",
        "|---|---|",
        f"| Series | {series} |",
        f"| Markets | {fmt_int(ch['markets'])} |",
        f"| Order book and trade rows | {fmt_int(ch['rows'])} |",
    ]
    if ch["reference_rows"]:
        lines.append(f"| Binance {ch['reference']} trades | {fmt_int(ch['reference_rows'])} |")
    if ch["volume_usd"]:
        lines.append(f"| Volume | {fmt_usd(ch['volume_usd'])} |")
    lines += [
        f"| Span | {ch['data_start'][:16].replace('T', ' ')} to {ch['data_end'][:16].replace('T', ' ')} UTC |",
        f"| Size | {fmt_bytes(ch['bytes'])} |",
        "",
        "## Outcomes",
        "",
        "| Market | Volume | Settled |",
        "|---|---|---|",
    ]
    for m in ch["top_markets"]:
        lines.append(f"| {m['question']} | {fmt_usd(m['volume_usd']) if m['volume_usd'] else ''} | {m['winning_outcome']} |")
    if ch["markets"] > len(ch["top_markets"]):
        if len(ch["outcomes"]) <= 4:
            outcomes = ", ".join(f"{k} {v}" for k, v in sorted(ch["outcomes"].items(), key=lambda kv: -kv[1]))
            lines += ["", f"All {fmt_int(ch['markets'])} markets and their outcomes are in `markets.csv` ({outcomes})."]
        else:
            lines += ["", f"All {fmt_int(ch['markets'])} markets and their outcomes are in `markets.csv`."]
    lines += [
        "",
        "## Files",
        "",
        "- `history-<market>-compact.parquet`: one file per market with every order book snapshot, price level change and trade (columns in the [root README](../README.md#data-format)).",
    ]
    if ch["reference_rows"]:
        lines.append(f"- `reference-{ch['reference']}.parquet`: Binance {ch['reference']} trades over the same span, read by `ctx.reference_price()` in a replay.")
    cadence = ch["snapshot_cadence_sec"]
    lines += [
        "- `markets.csv`: question, outcomes, winning outcome, open, close and settlement times, volume, per market.",
        "- `snapshots.csv`: best bid, best ask, midpoint, spread and depth per stored order book"
        + (f", sampled every {cadence // 60} minutes per market." if cadence else "."),
        "",
        "## Backtest",
        "",
        "```python",
        replay_snippet(ch),
        "```",
        "",
        "## Load with pandas",
        "",
        "```python",
        pandas_snippet(ch, first_file),
        "```",
        "",
        f"Every market since March 2026 at full resolution: [marketlens.trade]({SITE}/?{UTM}).",
        "",
    ]
    return "\n".join(lines)


def render_root_readme(manifest: dict) -> str:
    t = manifest["totals"]
    rows = []
    for ch in manifest["chapters"]:
        w = ch["window"]
        when = (w.get("after") or w.get("resolved_after"))[:10]
        rows.append(
            f"| [{ch['title']}]({ch['folder']}/) | {', '.join(ch['series'])} | {when} | "
            f"{fmt_int(ch['markets'])} | {fmt_int(ch['rows'])} | {fmt_bytes(ch['bytes'])} |"
        )
    table = "\n".join(rows)
    first = manifest["chapters"][0]
    fomc = next((c for c in manifest["chapters"] if c["folder"].startswith("fomc")), manifest["chapters"][1])
    text = TEMPLATE.read_text()
    subs = {
        "{{CHAPTERS}}": str(t["chapters"]),
        "{{MARKETS}}": fmt_int(t["markets"]),

        "{{ROWS_COMPACT}}": f"{t['rows'] / 1_000_000:.1f} million",
        "{{ROWS_TOTAL_M}}": f"{(t['rows'] + t['reference_rows']) / 1_000_000:.1f}M",
        "{{ROWS}}": fmt_int(t["rows"]),
        "{{BYTES}}": fmt_bytes(t["bytes"]),
        "{{SERIES_COUNT}}": str(t["series_in_index"]),
        "{{GENERATED_ON}}": manifest["generated_at"][:10],
        "{{SDK_VERSION}}": manifest["sdk_version"],
        "{{CHAPTER_TABLE}}": table,
        "{{REPLAY_EXAMPLE}}": replay_snippet(fomc),
        "{{PANDAS_EXAMPLE}}": pandas_snippet(first, next(f["file"] for f in first["files"] if f["file"].startswith("history-"))),
        "{{FIRST_FOLDER}}": first["folder"],
        "{{SITE}}": SITE,
        "{{UTM}}": UTM,
    }
    for k, v in subs.items():
        text = text.replace(k, v)
    return text


# --- archive index ------------------------------------------------------------

def write_index(sdk: MarketLens) -> int:
    rows = list(sdk.series.list(limit=200))
    rows.sort(key=lambda s: (s.category or "", s.platform_series_id))
    with INDEX.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["series", "title", "category", "recurrence", "rolling", "structured_type",
                    "markets", "first_market_close", "last_market_close"])
        for s in rows:
            w.writerow([s.platform_series_id, s.title, s.category or "", s.recurrence or "",
                        "yes" if s.is_rolling else "no", s.structured_type or "",
                        s.market_count, day(s.first_market_close), day(s.last_market_close)])
    return len(rows)


# --- main ---------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chapter", action="append", help="build only this folder (repeatable)")
    ap.add_argument("--dry-run", action="store_true", help="select markets, download nothing")
    ap.add_argument("--index", action="store_true", help="refresh archive-index.csv only")
    ap.add_argument("--render", action="store_true", help="recompute manifest.json and READMEs from the files on disk")
    args = ap.parse_args()

    sdk = MarketLens()
    targets = json.loads(TARGETS.read_text())["chapters"]
    if args.chapter:
        targets = [c for c in targets if c["folder"] in args.chapter]

    if args.index:
        n = write_index(sdk)
        print(f"archive-index.csv: {n} series")
        return

    chapters = []
    for ch in targets:
        folder = ROOT / ch["folder"]
        markets = select_markets(sdk, ch)
        series_of = {}
        if ch["mode"] == "series_window":
            for slug in ch["series"]:
                for m in sdk.series.walk(slug, after=ch["after"], before=ch["before"]):
                    series_of[m.id] = slug
        else:
            series_of = {m.id: ch["series"] for m in markets}
        print(f"{ch['folder']}: {len(markets)} markets selected")
        if args.dry_run:
            continue
        if not args.render:
            download_chapter(sdk, ch, folder, markets)
        # The series export can deliver a market the walk did not list
        # (or the reverse); the files on disk are the truth.
        on_disk = {p.name[len("history-"):-len("-compact.parquet")] for p in folder.glob("history-*-compact.parquet")}
        have = {m.id for m in markets}
        for missing in sorted(on_disk - have):
            m = sdk.markets.get(missing)
            markets.append(m)
            series_of.setdefault(m.id, m.series_id or "")
        markets = [m for m in markets if m.id in on_disk]
        markets, dropped = keep_complete(folder, markets)
        if dropped:
            print(f"{ch['folder']}: {len(dropped)} markets left out (empty or interrupted): "
                  + ", ".join(m.question[:40] for m in dropped[:6]) + (" ..." if len(dropped) > 6 else ""))
        write_markets_csv(folder, markets, series_of)
        n, cadence = write_snapshots_csv(folder, markets)
        print(f"{ch['folder']}: {len(on_disk)} files, {n} snapshot rows at cadence {cadence}s")
        facts = chapter_facts(ch, folder, markets, series_of, cadence)
        (folder / "README.md").write_text(render_chapter_readme(facts))
        print(f"{ch['folder']}: {facts['markets']} markets, {fmt_int(facts['rows'])} rows, "
              f"{fmt_bytes(facts['bytes'])}, largest file {fmt_bytes(facts['largest_file_bytes'])}")
        chapters.append(facts)

    if args.dry_run or not chapters:
        return

    if args.chapter and MANIFEST.exists():
        # Merge a partial build into the existing manifest.
        old = json.loads(MANIFEST.read_text())
        built = {c["folder"]: c for c in chapters}
        chapters = [built.get(c["folder"], c) for c in old["chapters"]] + [
            c for c in chapters if c["folder"] not in {o["folder"] for o in old["chapters"]}
        ]
    order = [c["folder"] for c in json.loads(TARGETS.read_text())["chapters"]]
    chapters.sort(key=lambda c: order.index(c["folder"]) if c["folder"] in order else len(order))

    from marketlens._constants import VERSION
    index_rows = sum(1 for _ in INDEX.open()) - 1 if INDEX.exists() else 0
    manifest = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sdk_version": VERSION,
        "totals": {
            "chapters": len(chapters),
            "markets": sum(c["markets"] for c in chapters),
            "rows": sum(c["rows"] for c in chapters),
            "reference_rows": sum(c["reference_rows"] for c in chapters),
            "bytes": sum(c["bytes"] for c in chapters),
            "series_in_index": index_rows,
        },
        "chapters": chapters,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")
    (ROOT / "README.md").write_text(render_root_readme(manifest))
    t = manifest["totals"]
    print(f"total: {t['chapters']} chapters, {fmt_int(t['markets'])} markets, {fmt_int(t['rows'])} rows, {fmt_bytes(t['bytes'])}")


if __name__ == "__main__":
    main()
