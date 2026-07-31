"""Dual-source symbol search: local top250_tickers.json + Yahoo Finance."""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from typing import Any

import yfinance as yf

from config import TICKERS_FILE

# PyInstaller frozen mode: data files may live in sys._MEIPASS (extracted to temp),
# not next to the .exe. Resolve to the actual runtime location.
if getattr(sys, "frozen", False):
    _bundled = Path(getattr(sys, "_MEIPASS", "")) / "top250_tickers.json"
    TICKERS_FILE = _bundled if _bundled.exists() else TICKERS_FILE

_lock = threading.Lock()
_local_tickers: list[dict] | None = None


def _load_local() -> list[dict]:
    global _local_tickers
    with _lock:
        if _local_tickers is not None:
            return _local_tickers
        try:
            with open(TICKERS_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            rows = raw.get("tickers", raw) if isinstance(raw, dict) else raw
            items = []
            seen = set()
            for row in rows:
                if isinstance(row, (list, tuple)) and len(row) >= 2:
                    # [display, ticker, name]
                    ticker = str(row[1]).strip()
                    name = str(row[2] if len(row) > 2 else row[0]).strip()
                    display = str(row[0]).strip()
                elif isinstance(row, dict):
                    ticker = str(row.get("ticker") or row.get("symbol") or "").strip()
                    name = str(row.get("name") or row.get("shortname") or ticker).strip()
                    display = f"{name} - {ticker}"
                else:
                    continue
                if not ticker or ticker.upper() in seen:
                    continue
                seen.add(ticker.upper())
                items.append({
                    "ticker": ticker,
                    "name": name,
                    "display": display or f"{name} - {ticker}",
                    "search_text": f"{ticker} {name} {display}".lower(),
                })
            _local_tickers = items
        except Exception as e:
            print(f"[search] failed to load local index: {e}")
            _local_tickers = []
        return _local_tickers


def search_local(query: str, limit: int = 20) -> list[dict]:
    q = (query or "").strip().lower()
    if len(q) < 2:
        return []
    items = _load_local()
    # Prefer ticker prefix matches, then name contains
    prefix, contains = [], []
    for it in items:
        t = it["ticker"].lower()
        st = it["search_text"]
        if t.startswith(q) or it["name"].lower().startswith(q):
            prefix.append(it)
        elif q in st:
            contains.append(it)
        if len(prefix) >= limit:
            break
    results = prefix + contains
    return [
        {"ticker": r["ticker"], "name": r["name"], "display": r["display"], "source": "local"}
        for r in results[:limit]
    ]


def search_yahoo(query: str, limit: int = 15) -> list[dict]:
    q = (query or "").strip()
    if len(q) < 2:
        return []
    results = []
    seen = set()
    try:
        s = yf.Search(q, max_results=limit)
        quotes = getattr(s, "quotes", None) or []
        for item in quotes:
            symbol = item.get("symbol") or ""
            if not symbol or symbol.upper() in seen:
                continue
            seen.add(symbol.upper())
            name = (
                item.get("longname")
                or item.get("shortname")
                or item.get("name")
                or symbol
            )
            results.append({
                "ticker": symbol,
                "name": name,
                "display": f"{name} - {symbol}",
                "source": "yahoo",
                "exchange": item.get("exchDisp") or item.get("exchange") or "",
                "type": item.get("typeDisp") or item.get("quoteType") or "",
            })
    except Exception as e:
        print(f"[search] yahoo failed: {e}")
    return results[:limit]


def search_all(query: str, local_limit: int = 20, yahoo_limit: int = 12) -> dict[str, Any]:
    q = (query or "").strip()
    if len(q) < 2:
        return {"local": [], "yahoo": [], "query": q}
    local = search_local(q, local_limit)
    yahoo = search_yahoo(q, yahoo_limit)
    # de-dupe yahoo against local tickers already shown
    local_set = {r["ticker"].upper() for r in local}
    yahoo = [r for r in yahoo if r["ticker"].upper() not in local_set]
    return {"local": local, "yahoo": yahoo, "query": q}


# Warm up local index at import (non-fatal)
try:
    _load_local()
except Exception:
    pass
