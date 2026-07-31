"""Local JSON persistence for watchlist state."""
from __future__ import annotations

import atexit
import copy
import json
import threading
from datetime import datetime
from typing import Any

from config import DATA_FILE, DEFAULT_SETTINGS, DEFAULT_WATCHLIST_NAME, DEFAULT_INDICES

_lock = threading.RLock()
_state: dict[str, Any] | None = None


def _normalize_item(item: Any) -> dict:
    """Normalize legacy list [name, ticker, ...] to dict."""
    if isinstance(item, dict):
        return {
            "name": item.get("name") or item.get("ticker") or "",
            "ticker": item.get("ticker") or "",
        }
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        # formats: [name, ticker, ...] or [display, ticker, name]
        a, b = item[0], item[1]
        # if second looks like ticker
        if isinstance(b, str) and (b.isupper() or b.startswith("^") or "." in b):
            return {"name": str(a).split(" - ")[0].strip() or str(a), "ticker": str(b)}
        return {"name": str(b), "ticker": str(a)}
    return {"name": str(item), "ticker": str(item)}


def _normalize_state(raw: dict) -> dict:
    state = copy.deepcopy(DEFAULT_SETTINGS)
    if not raw:
        return state

    watchlists = raw.get("watchlists") or {}
    norm_wls: dict[str, list] = {}
    for name, items in watchlists.items():
        norm_wls[name] = [_normalize_item(it) for it in (items or [])]

    if not norm_wls:
        norm_wls = copy.deepcopy(DEFAULT_SETTINGS["watchlists"])

    state["watchlists"] = norm_wls
    state["active_wl"] = raw.get("active_wl") or next(iter(norm_wls.keys()))
    if state["active_wl"] not in norm_wls:
        state["active_wl"] = next(iter(norm_wls.keys()))

    state["lang"] = raw.get("lang") or "zh-TW"
    if state["lang"] not in ("zh-TW", "zh-CN", "en"):
        state["lang"] = "zh-TW"

    state["theme"] = raw.get("theme") or "dark"
    state["font_family"] = raw.get("font_family") or DEFAULT_SETTINGS["font_family"]
    state["font_size"] = int(raw.get("font_size") or 14)
    state["zoom"] = float(raw.get("zoom") or 100)
    state["auto_refresh"] = int(raw.get("auto_refresh") or 0)
    state["alerts"] = raw.get("alerts") or []
    state["last_updated"] = raw.get("last_updated")
    return state


def load() -> dict:
    global _state
    with _lock:
        if _state is not None:
            return _state
        if DATA_FILE.exists():
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                _state = _normalize_state(raw)
            except Exception:
                _state = copy.deepcopy(DEFAULT_SETTINGS)
        else:
            _state = copy.deepcopy(DEFAULT_SETTINGS)
            save()
        return _state


def save(state: dict | None = None) -> None:
    global _state
    with _lock:
        if state is not None:
            _state = state
        if _state is None:
            return
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[storage] save failed: {e}")


def get_state() -> dict:
    return load()


def update_state(**kwargs) -> dict:
    with _lock:
        state = load()
        state.update(kwargs)
        save(state)
        return state


def active_items() -> list[dict]:
    state = load()
    wl = state.get("active_wl")
    return list(state.get("watchlists", {}).get(wl, []))


def set_active_items(items: list[dict]) -> dict:
    with _lock:
        state = load()
        wl = state["active_wl"]
        state["watchlists"][wl] = items
        save(state)
        return state


def add_item(name: str, ticker: str) -> tuple[bool, str]:
    ticker = (ticker or "").strip()
    name = (name or ticker).strip()
    if not ticker:
        return False, "empty ticker"
    with _lock:
        state = load()
        wl = state["active_wl"]
        items = state["watchlists"].setdefault(wl, [])
        for it in items:
            if it["ticker"].upper() == ticker.upper():
                return False, "already_in"
        items.append({"name": name, "ticker": ticker})
        save(state)
        return True, "add_success"


def remove_item(ticker: str) -> bool:
    with _lock:
        state = load()
        wl = state["active_wl"]
        items = state["watchlists"].get(wl, [])
        new_items = [it for it in items if it["ticker"].upper() != ticker.upper()]
        if len(new_items) == len(items):
            return False
        state["watchlists"][wl] = new_items
        save(state)
        return True


def move_item(ticker: str, direction: str) -> bool:
    with _lock:
        state = load()
        wl = state["active_wl"]
        items = state["watchlists"].get(wl, [])
        idx = next((i for i, it in enumerate(items) if it["ticker"].upper() == ticker.upper()), None)
        if idx is None:
            return False
        if direction == "up" and idx > 0:
            items[idx - 1], items[idx] = items[idx], items[idx - 1]
        elif direction == "down" and idx < len(items) - 1:
            items[idx + 1], items[idx] = items[idx], items[idx + 1]
        else:
            return False
        save(state)
        return True


def add_watchlist(name: str) -> tuple[bool, str, str | None]:
    """Create a new (empty) watchlist and switch to it.
    Returns (ok, msg, name). Rejects blank/duplicate names."""
    name = (name or "").strip()
    if not name:
        return False, "wl_empty_name", None
    with _lock:
        state = load()
        wls = state.setdefault("watchlists", {})
        if name in wls:
            return False, "wl_exists", None
        wls[name] = []
        state["active_wl"] = name
        save(state)
        return True, "wl_created", name


def delete_watchlist(name: str) -> tuple[bool, str, str | None, int]:
    """Delete a watchlist and all items it contains.
    Returns (ok, msg, fallback_active_wl, items_destroyed_count).
    Safety: refuses to delete the last remaining watchlist (you'd then have
    nothing to switch to); refuses to delete the reserved default name? no —
    any named watchlist is deletable, as long as at least one survives.
    """
    name = (name or "").strip()
    if not name:
        return False, "wl_empty_name", None, 0
    with _lock:
        state = load()
        wls = state.setdefault("watchlists", {})
        if name not in wls:
            return False, "wl_not_found", None, 0
        if len(wls) <= 1:
            # Never leave the user with zero watchlists.
            return False, "wl_last_one", None, 0
        destroyed = len(wls[name])  # count before delete, for the warning echo
        del wls[name]
        # Switch to a surviving watchlist (deterministic: first remaining key)
        new_active = next(iter(wls.keys()))
        state["active_wl"] = new_active
        save(state)
        return True, "wl_deleted", new_active, destroyed


def set_last_updated(ts: str | None = None) -> str:
    ts = ts or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    update_state(last_updated=ts)
    return ts


def ensure_default_watchlist_if_empty() -> None:
    """If no watchlists, seed default 14 indices."""
    state = load()
    if not state.get("watchlists"):
        update_state(
            watchlists={
                DEFAULT_WATCHLIST_NAME: [
                    {"name": i["name"], "ticker": i["ticker"]} for i in DEFAULT_INDICES
                ]
            },
            active_wl=DEFAULT_WATCHLIST_NAME,
        )


# Force save on process exit
atexit.register(lambda: save())
