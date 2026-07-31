"""
Global Watchlist Manager — FastHTML + yfinance desktop web app.
Run: python main.py
"""
from __future__ import annotations

import json
from datetime import datetime

from fasthtml.common import (
    H1, H2, H3, A, Button, Div, Form, Input, Label, Link, Option, Script,
    Select, Span, Style, Table, Tbody, Td, Th, Thead, Tr, Ul, Li,
    fast_app, serve, JSONResponse,
)

import storage
from config import AUTO_REFRESH_OPTIONS, BASE_DIR, ZOOM_OPTIONS
from i18n import all_keys, t
from market import (
    fetch_quote,
    fetch_quotes,
    format_quote_row,
    get_chart_data,
    get_fundamentals,
)
from news import get_stock_news
from search_svc import search_all

# ── App bootstrap ─────────────────────────────────────────────────
storage.ensure_default_watchlist_if_empty()
storage.load()

app, rt = fast_app(
    pico=False,
    htmlkw={"lang": "zh-Hant"},
    hdrs=(
        Link(rel="icon", type="image/x-icon", href="/favicon.ico"),
        Link(rel="stylesheet", href="/static/styles.css"),
        Script(
            src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"
        ),
        Script(src="/static/app.js", defer=True),
    ),
    static_path=str(BASE_DIR),
)


def _lang() -> str:
    return storage.get_state().get("lang") or "zh-TW"


def _theme_class(theme: str) -> str:
    if theme == "light":
        return "theme-light"
    if theme == "dark":
        return "theme-dark"
    if theme == "frost":
        return "theme-frost"
    if theme == "purple":
        return "theme-purple"
    if theme == "cyan":
        return "theme-cyan"
    if theme == "smokeblue":
        return "theme-smokeblue"
    if theme == "smoke":
        return "theme-smoke"
    return "theme-system"


def _settings_payload() -> dict:
    s = storage.get_state()
    return {
        "lang": s.get("lang", "zh-TW"),
        "theme": s.get("theme", "purple"),
        "font_family": s.get("font_family", "system-ui, sans-serif"),
        "font_size": s.get("font_size", 14),
        "zoom": s.get("zoom", 100),
        "auto_refresh": s.get("auto_refresh", 0),
        "active_wl": s.get("active_wl"),
        "watchlist_names": list(s.get("watchlists", {}).keys()),
        "last_updated": s.get("last_updated"),
        "i18n": all_keys(s.get("lang", "zh-TW")),
        "alerts": s.get("alerts") or [],
    }


# ── Pages ─────────────────────────────────────────────────────────

@rt("/")
def home():
    state = storage.get_state()
    lang = state.get("lang", "zh-TW")
    theme = state.get("theme", "purple")
    font = state.get("font_family", "Microsoft JhengHei, system-ui, sans-serif")
    fsize = state.get("font_size", 14)
    zoom = state.get("zoom", 100)
    last = state.get("last_updated") or t(lang, "never")
    auto = int(state.get("auto_refresh") or 0)
    i18n_json = json.dumps(all_keys(lang), ensure_ascii=False)
    settings_json = json.dumps(_settings_payload(), ensure_ascii=False)

    root_style = (
        f"--font-family:{font};--font-size:{fsize}px;--zoom:{zoom}%;"
    )

    # Initial quotes
    items = storage.active_items()
    quotes = [format_quote_row(q) for q in fetch_quotes(items)]
    if quotes:
        storage.set_last_updated()
        last = storage.get_state().get("last_updated") or last

    return (
        Style(f""":root{{{root_style}}} body{{zoom:var(--zoom);}}"""),
        Div(
            # Delay disclaimer banner
            Div(t(lang, "alert_banner"), cls="alert-banner", id="delay-banner"),
            # Header toolbar
            Div(
                H1(t(lang, "app_title"), id="app-title"),
                Div(
                    Div(
                        Input(
                            type="text",
                            id="search-input",
                            cls="search-input",
                            placeholder=t(lang, "search_placeholder"),
                            autocomplete="off",
                            spellcheck="false",
                        ),
                        Div(id="sr", cls=""),
                        cls="search-box",
                    ),
                    Select(
                        *[
                            Option(
                                name,
                                value=name,
                                selected="selected" if name == state.get("active_wl") else None,
                            )
                            for name in state.get("watchlists", {}).keys()
                        ],
                        id="wl-select",
                        title=t(lang, "watchlist"),
                    ),
                    Button(t(lang, "wl_add"), id="btn-add-wl", cls="small", title=t(lang, "wl_add")),
                    Button(t(lang, "wl_del"), id="btn-del-wl", cls="small danger-icon", title=t(lang, "wl_del")),
                    Button(t(lang, "refresh_page"), id="btn-refresh-page", cls="small"),
                    Button(t(lang, "refresh_all"), id="btn-refresh-all", cls="small accent"),
                    Select(
                        Option(t(lang, "pause"), value="0", selected="selected" if auto == 0 else None),
                        Option(t(lang, "min_5"), value="5", selected="selected" if auto == 5 else None),
                        Option(t(lang, "min_15"), value="15", selected="selected" if auto == 15 else None),
                        Option(t(lang, "min_60"), value="60", selected="selected" if auto == 60 else None),
                        id="auto-refresh",
                        title=t(lang, "auto_refresh"),
                    ),
                    Button(t(lang, "price_alerts"), id="btn-alerts", cls="small"),
                    Button(t(lang, "settings"), id="btn-settings", cls="small"),
                    Span(
                        Span(t(lang, "last_updated") + ": ", id="lbl-updated"),
                        Span(last, id="last-updated", cls="time-tag"),
                        cls="time-wrap",
                    ),
                    cls="toolbar",
                ),
                cls="wl-header",
            ),
            # Table
            Div(
                Table(
                    Thead(
                        Tr(
                            Th(t(lang, "name"), id="th-name"),
                            Th(t(lang, "ticker"), id="th-ticker"),
                            Th(t(lang, "price"), id="th-price"),
                            Th(t(lang, "change"), id="th-change"),
                            Th(t(lang, "change_pct"), id="th-pct"),
                            Th(t(lang, "volume"), id="th-vol"),
                            Th(t(lang, "actions"), id="th-act"),
                        )
                    ),
                    Tbody(id="wl-body", *_quote_rows(quotes, lang)),
                    cls="wl-table",
                    id="wl-table",
                ),
                cls="table-wrap",
            ),
            Div(
                "yfWatchlist · FastHTML + yfinance · Data for reference only",
                cls="footer",
            ),
            # Browse modal
            Div(
                Div(
                    Div(
                        H2("—", id="detail-title"),
                        Button("✕", id="btn-close-detail", cls="small"),
                        cls="modal-header",
                    ),
                    Div(
                        Button(t(lang, "tab_info"), id="tab-info", cls="tab-btn active", data_tab="info"),
                        Button(t(lang, "tab_chart"), id="tab-chart", cls="tab-btn", data_tab="chart"),
                        Button(t(lang, "tab_news"), id="tab-news", cls="tab-btn", data_tab="news"),
                        cls="tabs",
                        id="detail-tabs",
                    ),
                    Div(id="tab-pane-info", cls="tab-content active"),
                    Div(
                        Div(
                            Button(t(lang, "day_k"), id="btn-day", cls="small active", data_period="day"),
                            Button(t(lang, "week_k"), id="btn-week", cls="small", data_period="week"),
                            Button(t(lang, "month_k"), id="btn-month", cls="small", data_period="month"),
                            Button("KDJ", id="btn-kd", cls="small accent", data_indicator="kd"),
                            Button("MACD", id="btn-macd", cls="small", data_indicator="macd"),
                            cls="chart-toolbar",
                        ),
                        Div(id="chart-info-bar", cls="chart-info-bar"),
                        Div(
                            Div(id="chart_kline", cls="chart-box"),
                            Div(id="chart_volume", cls="chart-box"),
                            Div(id="chart_kdj", cls="chart-box"),
                            cls="chart-wrapper",
                        ),
                        id="tab-pane-chart",
                        cls="tab-content",
                    ),
                    Div(id="tab-pane-news", cls="tab-content"),
                    cls="modal modal-wide",
                ),
                id="detail-modal",
                cls="modal-overlay",
            ),
            # Settings modal
            Div(
                Div(
                    Div(
                        H2(t(lang, "settings"), id="settings-title"),
                        Button("✕", id="btn-close-settings", cls="small"),
                        cls="modal-header",
                    ),
                    Div(
                        Div(
                            Label(t(lang, "language"), fr="set-lang", id="lbl-lang"),
                            Select(
                                Option("繁體中文", value="zh-TW", selected="selected" if lang == "zh-TW" else None),
                                Option("简体中文", value="zh-CN", selected="selected" if lang == "zh-CN" else None),
                                Option("English", value="en", selected="selected" if lang == "en" else None),
                                id="set-lang",
                            ),
                            cls="set-row",
                        ),
                        Div(
                            Label(t(lang, "theme"), fr="set-theme", id="lbl-theme"),
                            Select(
                                Option(t(lang, "theme_system"), value="system", selected="selected" if theme == "system" else None),
                                Option(t(lang, "theme_light"), value="light", selected="selected" if theme == "light" else None),
                                Option(t(lang, "theme_dark"), value="dark", selected="selected" if theme == "dark" else None),
                                Option("冰藍透玻璃 Frost", value="frost", selected="selected" if theme == "frost" else None),
                                Option("霧紫透玻璃 Purple", value="purple", selected="selected" if theme == "purple" else None),
                                Option("青綠透玻璃 Cyan", value="cyan", selected="selected" if theme == "cyan" else None),
                                Option("煙藍透玻璃 Blue", value="smokeblue", selected="selected" if theme == "smokeblue" else None),
                                Option("煙灰綠透玻璃 Smoke", value="smoke", selected="selected" if theme == "smoke" else None),
                                id="set-theme",
                            ),
                            cls="set-row",
                        ),
                        Div(
                            Label(t(lang, "font_family"), fr="set-font", id="lbl-font"),
                            Select(id="set-font"),
                            cls="set-row",
                        ),
                        Div(
                            Label(t(lang, "font_size"), fr="set-fsize", id="lbl-fsize"),
                            Input(type="number", id="set-fsize", value=str(fsize), min="10", max="28", step="1"),
                            cls="set-row",
                        ),
                        Div(
                            Label(t(lang, "zoom"), fr="set-zoom", id="lbl-zoom"),
                            Select(
                                *[
                                    Option(f"{z}%", value=str(z), selected="selected" if float(zoom) == float(z) else None)
                                    for z in ZOOM_OPTIONS
                                ],
                                id="set-zoom",
                            ),
                            cls="set-row",
                        ),
                        Div(
                            Label(t(lang, "auto_refresh"), fr="set-auto", id="lbl-auto"),
                            Select(
                                Option(t(lang, "pause"), value="0", selected="selected" if auto == 0 else None),
                                Option(t(lang, "min_5"), value="5", selected="selected" if auto == 5 else None),
                                Option(t(lang, "min_15"), value="15", selected="selected" if auto == 15 else None),
                                Option(t(lang, "min_60"), value="60", selected="selected" if auto == 60 else None),
                                id="set-auto",
                            ),
                            cls="set-row",
                        ),
                        Button(t(lang, "save"), id="btn-save-settings", cls="accent"),
                        cls="set-grid",
                        id="settings-body",
                    ),
                    cls="modal small-modal",
                ),
                id="settings-modal",
                cls="modal-overlay",
            ),
            # Alerts modal
            Div(
                Div(
                    Div(
                        H2(t(lang, "price_alerts"), id="alerts-title"),
                        Button("✕", id="btn-close-alerts", cls="small"),
                        cls="modal-header",
                    ),
                    Div(
                        Div(
                            Input(type="text", id="alert-ticker", placeholder="Ticker", style="width:100px"),
                            Select(
                                Option(t(lang, "alert_above"), value="above"),
                                Option(t(lang, "alert_below"), value="below"),
                                id="alert-cond",
                            ),
                            Input(type="number", id="alert-price", placeholder="Price", step="0.01", style="width:110px"),
                            Button(t(lang, "alert_add"), id="btn-add-alert", cls="accent small"),
                            cls="alert-form",
                        ),
                        Div(id="alerts-list"),
                        id="alerts-body",
                    ),
                    cls="modal small-modal",
                ),
                id="alerts-modal",
                cls="modal-overlay",
            ),
            # Toast
            Div(id="notif", cls="notif"),
            # Boot data for JS
            Script(f"""
                window.__WL__ = {{
                    settings: {settings_json},
                    i18n: {i18n_json},
                    currentFont: {json.dumps(font, ensure_ascii=False)}
                }};
            """),
            id="app-root",
            cls=_theme_class(theme),
        ),
    )


def _quote_rows(quotes: list[dict], lang: str):
    if not quotes:
        return [
            Tr(
                Td(t(lang, "empty_list"), colspan="7", style="text-align:center;padding:24px;color:var(--muted)"),
            )
        ]
    rows = []
    for q in quotes:
        d = q.get("direction", "flat")
        price_cls = f"price-{d}"
        rows.append(
            Tr(
                Td(q.get("name") or q.get("ticker")),
                Td(q.get("ticker")),
                Td(q.get("price_str", "—"), cls=price_cls),
                Td(q.get("change_str", "—"), cls=price_cls),
                Td(q.get("change_pct_str", "—"), cls=price_cls),
                Td(q.get("volume_str", "—")),
                Td(
                    Button("🔍", cls="icon-btn", title=t(lang, "browse"),
                           onclick=f"WL.browse('{q.get('ticker')}')"),
                    Button("↑", cls="icon-btn", title=t(lang, "move_up"),
                           onclick=f"WL.move('{q.get('ticker')}','up')"),
                    Button("↓", cls="icon-btn", title=t(lang, "move_down"),
                           onclick=f"WL.move('{q.get('ticker')}','down')"),
                    Button("🗑", cls="icon-btn danger-icon", title=t(lang, "delete"),
                           onclick=f"WL.remove('{q.get('ticker')}')"),
                    cls="actions-cell",
                ),
                data_ticker=q.get("ticker"),
            )
        )
    return rows


# ── API routes ────────────────────────────────────────────────────

@rt("/api/quotes")
def api_quotes():
    items = storage.active_items()
    quotes = [format_quote_row(q) for q in fetch_quotes(items)]
    ts = storage.set_last_updated()
    return JSONResponse({"quotes": quotes, "last_updated": ts})


@rt("/api/quote")
def api_quote(ticker: str):
    q = format_quote_row(fetch_quote(ticker))
    return JSONResponse(q)


@rt("/api/search")
def api_search(q: str = ""):
    return JSONResponse(search_all(q))


@rt("/api/add", methods=["POST"])
async def api_add(req):
    body = await req.json()
    name = (body.get("name") or "").strip()
    ticker = (body.get("ticker") or "").strip()
    ok, msg = storage.add_item(name, ticker)
    quote = None
    if ok:
        quote = format_quote_row(fetch_quote(ticker, name))
        # Update stored name if yfinance has better short name and user used ticker-only
        if quote.get("name") and name == ticker:
            items = storage.active_items()
            for it in items:
                if it["ticker"].upper() == ticker.upper():
                    it["name"] = quote["name"]
            storage.set_active_items(items)
            quote["name"] = quote["name"]
        storage.set_last_updated()
    return JSONResponse({
        "ok": ok,
        "msg": msg,
        "quote": quote,
        "last_updated": storage.get_state().get("last_updated"),
        "i18n_msg": t(_lang(), msg) if msg in ("already_in", "add_success") else msg,
    })


@rt("/api/remove", methods=["POST"])
async def api_remove(req):
    body = await req.json()
    ticker = (body.get("ticker") or "").strip()
    ok = storage.remove_item(ticker)
    return JSONResponse({"ok": ok})


@rt("/api/move", methods=["POST"])
async def api_move(req):
    body = await req.json()
    ticker = (body.get("ticker") or "").strip()
    direction = (body.get("direction") or "").strip()
    ok = storage.move_item(ticker, direction)
    return JSONResponse({"ok": ok})


@rt("/api/watchlist/switch", methods=["POST"])
async def api_switch_wl(req):
    body = await req.json()
    name = (body.get("name") or "").strip()
    state = storage.get_state()
    if name not in state.get("watchlists", {}):
        return JSONResponse({"ok": False, "error": "not found"}, status_code=400)
    storage.update_state(active_wl=name)
    items = storage.active_items()
    quotes = [format_quote_row(q) for q in fetch_quotes(items)]
    ts = storage.set_last_updated()
    return JSONResponse({"ok": True, "quotes": quotes, "last_updated": ts})

@rt("/api/watchlist/add", methods=["POST"])
async def api_add_wl(req):
    body = await req.json()
    name = (body.get("name") or "").strip()
    ok, msg, new_name = storage.add_watchlist(name)
    if not ok:
        return JSONResponse({"ok": False, "error": msg}, status_code=400)
    ts = storage.set_last_updated()
    state = storage.get_state()
    return JSONResponse({
        "ok": True,
        "active_wl": new_name,
        "watchlist_names": list(state.get("watchlists", {}).keys()),
        "quotes": [],          # new watchlist starts empty
        "last_updated": ts,
        "i18n_msg": t(_lang(), msg) if msg in ("wl_empty_name", "wl_created", "wl_exists") else msg,
    })

@rt("/api/watchlist/delete", methods=["POST"])
async def api_delete_wl(req):
    body = await req.json()
    name = (body.get("name") or "").strip()
    ok, msg, new_active, destroyed = storage.delete_watchlist(name)
    if not ok:
        return JSONResponse({"ok": False, "error": msg, "i18n_msg": t(_lang(), msg)}, status_code=400)
    # Refetch quotes for the watchlist we auto-switched to, and return its name
    # plus updated option list + the destroy-count so the UI can toast it.
    items = storage.active_items()
    quotes = [format_quote_row(q) for q in fetch_quotes(items)]
    ts = storage.set_last_updated()
    state = storage.get_state()
    return JSONResponse({
        "ok": True,
        "active_wl": new_active,
        "watchlist_names": list(state.get("watchlists", {}).keys()),
        "quotes": quotes,
        "destroyed": destroyed,
        "last_updated": ts,
        "i18n_msg": t(_lang(), msg),
    })


@rt("/api/fundamentals")
def api_fundamentals(ticker: str):
    return JSONResponse(get_fundamentals(ticker))


@rt("/api/chart")
def api_chart(ticker: str, period: str = "day"):
    if period not in ("day", "week", "month"):
        period = "day"
    return JSONResponse(get_chart_data(ticker, period))


@rt("/api/news")
def api_news(ticker: str, limit: int = 10):
    try:
        news = get_stock_news(ticker, limit=min(limit, 20))
    except Exception as e:
        news = []
        return JSONResponse({"news": news, "error": str(e)})
    return JSONResponse({"news": news})


@rt("/api/settings", methods=["GET"])
def api_get_settings():
    return JSONResponse(_settings_payload())


@rt("/api/settings", methods=["POST"])
async def api_save_settings(req):
    body = await req.json()
    allowed = {
        "lang", "theme", "font_family", "font_size", "zoom", "auto_refresh"
    }
    patch = {k: body[k] for k in allowed if k in body}
    if "font_size" in patch:
        patch["font_size"] = int(patch["font_size"])
    if "zoom" in patch:
        patch["zoom"] = float(patch["zoom"])
    if "auto_refresh" in patch:
        patch["auto_refresh"] = int(patch["auto_refresh"])
        if patch["auto_refresh"] not in AUTO_REFRESH_OPTIONS:
            patch["auto_refresh"] = 0
    if "zoom" in patch and patch["zoom"] not in ZOOM_OPTIONS:
        # allow close match
        patch["zoom"] = min(ZOOM_OPTIONS, key=lambda z: abs(z - float(patch["zoom"])))
    storage.update_state(**patch)
    return JSONResponse({"ok": True, "settings": _settings_payload()})


@rt("/api/alerts", methods=["GET"])
def api_get_alerts():
    return JSONResponse({"alerts": storage.get_state().get("alerts") or []})


@rt("/api/alerts", methods=["POST"])
async def api_add_alert(req):
    body = await req.json()
    ticker = (body.get("ticker") or "").strip().upper()
    condition = body.get("condition") or "above"
    if condition in ("高於", "above", "高于"):
        condition = "above"
    elif condition in ("低於", "below", "低于"):
        condition = "below"
    else:
        condition = "above"
    try:
        target = float(body.get("target_price"))
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid price"}, status_code=400)
    if not ticker:
        return JSONResponse({"ok": False, "error": "ticker required"}, status_code=400)
    state = storage.get_state()
    alerts = list(state.get("alerts") or [])
    alerts.append({
        "ticker": ticker,
        "name": body.get("name") or ticker,
        "condition": condition,
        "target_price": target,
        "triggered": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    })
    storage.update_state(alerts=alerts)
    return JSONResponse({"ok": True, "alerts": alerts})


@rt("/api/alerts/delete", methods=["POST"])
async def api_del_alert(req):
    body = await req.json()
    idx = body.get("index")
    state = storage.get_state()
    alerts = list(state.get("alerts") or [])
    try:
        idx = int(idx)
        if 0 <= idx < len(alerts):
            alerts.pop(idx)
            storage.update_state(alerts=alerts)
            return JSONResponse({"ok": True, "alerts": alerts})
    except Exception:
        pass
    # also allow delete by ticker+price
    ticker = (body.get("ticker") or "").upper()
    target = body.get("target_price")
    if ticker is not None:
        new_alerts = []
        for a in alerts:
            if a.get("ticker", "").upper() == ticker and (
                target is None or float(a.get("target_price", 0)) == float(target)
            ):
                continue
            new_alerts.append(a)
        storage.update_state(alerts=new_alerts)
        return JSONResponse({"ok": True, "alerts": new_alerts})
    return JSONResponse({"ok": False}, status_code=400)


@rt("/api/alerts/check", methods=["POST"])
async def api_check_alerts(req):
    """Check alerts against current prices; mark triggered."""
    state = storage.get_state()
    alerts = list(state.get("alerts") or [])
    if not alerts:
        return JSONResponse({"triggered": [], "alerts": []})
    tickers = list({a["ticker"] for a in alerts if not a.get("triggered")})
    prices = {}
    for tk in tickers:
        q = fetch_quote(tk)
        if q.get("price") is not None:
            prices[tk.upper()] = q["price"]
    triggered = []
    changed = False
    for a in alerts:
        if a.get("triggered"):
            continue
        px = prices.get(a["ticker"].upper())
        if px is None:
            continue
        cond = a.get("condition")
        target = float(a.get("target_price", 0))
        hit = (cond == "above" and px >= target) or (cond == "below" and px <= target)
        if hit:
            a["triggered"] = True
            a["triggered_at"] = datetime.now().isoformat(timespec="seconds")
            a["triggered_price"] = px
            triggered.append(a)
            changed = True
    if changed:
        storage.update_state(alerts=alerts)
    return JSONResponse({"triggered": triggered, "alerts": alerts})


@rt("/api/save", methods=["POST"])
def api_force_save():
    storage.save()
    return JSONResponse({"ok": True})


# ── Favicon ───────────────────────────────────────────────────────
from starlette.responses import FileResponse

@rt("/favicon.ico")
def favicon():
    icon_path = BASE_DIR / "static" / "yfWatchlist.ico"
    if icon_path.exists():
        return FileResponse(str(icon_path), media_type="image/x-icon")
    return JSONResponse({"error": "not found"}, status_code=404)


# ── Entry ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 56)
    print("  yfWatchlist — FastHTML Global Watchlist Manager")
    print("  Open: http://localhost:5001")
    print("=" * 56)
    serve(port=5001)
