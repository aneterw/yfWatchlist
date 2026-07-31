"""Market data: quotes, fundamentals, chart series (yfinance)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

from config import CHART_PERIODS


def _safe_float(v, default=None):
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return default
        return float(v)
    except Exception:
        return default


def _fmt_num(v, digits=2, prefix="", suffix=""):
    if v is None:
        return "—"
    try:
        return f"{prefix}{float(v):,.{digits}f}{suffix}"
    except Exception:
        return "—"


def _fmt_large(v):
    if v is None:
        return "—"
    try:
        v = float(v)
        abs_v = abs(v)
        if abs_v >= 1e12:
            return f"${v / 1e12:.2f}T"
        if abs_v >= 1e9:
            return f"${v / 1e9:.2f}B"
        if abs_v >= 1e6:
            return f"${v / 1e6:.2f}M"
        return f"${v:,.0f}"
    except Exception:
        return "—"


def _fmt_volume(v):
    if v is None:
        return "—"
    try:
        v = float(v)
        if v >= 1e9:
            return f"{v / 1e9:.2f}B"
        if v >= 1e6:
            return f"{v / 1e6:.2f}M"
        if v >= 1e3:
            return f"{v / 1e3:.1f}K"
        return f"{v:,.0f}"
    except Exception:
        return "—"


def fetch_quote(ticker: str, name: str | None = None) -> dict:
    """Fetch single symbol quote."""
    result = {
        "ticker": ticker,
        "name": name or ticker,
        "price": None,
        "change": None,
        "change_pct": None,
        "volume": None,
        "currency": "",
        "error": None,
    }
    try:
        t = yf.Ticker(ticker)
        info = {}
        try:
            info = t.info or {}
        except Exception:
            info = {}

        price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose")
        )
        prev = info.get("previousClose") or info.get("regularMarketPreviousClose")
        volume = info.get("volume") or info.get("regularMarketVolume")
        display_name = (
            name
            or info.get("shortName")
            or info.get("longName")
            or ticker
        )

        # Fallback via fast_info / history
        if price is None:
            try:
                fi = t.fast_info
                price = getattr(fi, "last_price", None) or getattr(fi, "regular_market_price", None)
                prev = prev or getattr(fi, "previous_close", None)
                volume = volume or getattr(fi, "last_volume", None)
            except Exception:
                pass

        if price is None:
            hist = t.history(period="5d", interval="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
                if len(hist) >= 2:
                    prev = float(hist["Close"].iloc[-2])
                volume = float(hist["Volume"].iloc[-1]) if "Volume" in hist else None

        price = _safe_float(price)
        prev = _safe_float(prev)
        change = (price - prev) if (price is not None and prev is not None) else None
        change_pct = (change / prev * 100) if (change is not None and prev) else None

        result.update(
            {
                "name": display_name,
                "price": price,
                "change": change,
                "change_pct": change_pct,
                "volume": _safe_float(volume),
                "currency": info.get("currency") or "",
            }
        )
    except Exception as e:
        result["error"] = str(e)
    return result


def fetch_quotes(items: list[dict], max_workers: int = 8) -> list[dict]:
    """Fetch quotes for a list of {name, ticker} concurrently."""
    if not items:
        return []
    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as ex:
        futs = {
            ex.submit(fetch_quote, it["ticker"], it.get("name")): it["ticker"]
            for it in items
        }
        for fut in as_completed(futs):
            ticker = futs[fut]
            try:
                results[ticker] = fut.result()
            except Exception as e:
                results[ticker] = {
                    "ticker": ticker,
                    "name": ticker,
                    "price": None,
                    "change": None,
                    "change_pct": None,
                    "volume": None,
                    "error": str(e),
                }
    # preserve order
    ordered = []
    for it in items:
        q = results.get(it["ticker"]) or fetch_quote(it["ticker"], it.get("name"))
        # keep user-defined name if present
        if it.get("name"):
            q["name"] = it["name"]
        ordered.append(q)
    return ordered


def get_fundamentals(ticker: str) -> dict[str, Any]:
    """Card-friendly fundamentals based on run8.py fields."""
    out: dict[str, Any] = {"ticker": ticker, "ok": False, "sections": [], "quote": {}}
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
        if not info:
            out["error"] = "no info"
            return out

        current_price = _safe_float(
            info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose"),
            0.0,
        )
        previous_close = _safe_float(info.get("previousClose"), 0.0) or 0.0
        price_change = (current_price or 0) - previous_close
        price_change_pct = (price_change / previous_close * 100) if previous_close else 0.0

        cash_flow = stock.cashflow
        quarterly_is = stock.quarterly_income_stmt
        quarterly_bs = stock.quarterly_balance_sheet

        date_str = "—"
        try:
            if quarterly_bs is not None and not quarterly_bs.empty:
                date_str = quarterly_bs.columns[0].strftime("%Y-%m-%d")
        except Exception:
            pass

        market_cap = info.get("marketCap")
        pe_ratio = _safe_float(info.get("trailingPE"))
        forward_pe = _safe_float(info.get("forwardPE"))
        peg_ratio = _safe_float(info.get("pegRatio"))
        pb_ratio = _safe_float(info.get("priceToBook"))
        ev_ebitda = _safe_float(info.get("enterpriseToEbitda"))

        eps = _safe_float(info.get("trailingEps"))
        roe = (_safe_float(info.get("returnOnEquity"), 0) or 0) * 100
        roa = (_safe_float(info.get("returnOnAssets"), 0) or 0) * 100
        roic = roe * 1.02
        operating_margin = (_safe_float(info.get("operatingMargins"), 0) or 0) * 100
        profit_margin = (_safe_float(info.get("profitMargins"), 0) or 0) * 100

        ocf = 0.0
        fcf = 0.0
        div_paid = 0.0
        try:
            if cash_flow is not None and not cash_flow.empty:
                if "Operating Cash Flow" in cash_flow.index:
                    ocf = float(cash_flow.loc["Operating Cash Flow"].iloc[0])
                if "Free Cash Flow" in cash_flow.index:
                    fcf = float(cash_flow.loc["Free Cash Flow"].iloc[0])
                else:
                    capex = 0.0
                    if "Capital Expenditures" in cash_flow.index:
                        capex = float(cash_flow.loc["Capital Expenditures"].iloc[0])
                    fcf = ocf + capex
                for key in ("Cash Dividends Paid", "Common Stock Dividend Paid"):
                    if key in cash_flow.index:
                        div_paid = abs(float(cash_flow.loc[key].iloc[0]))
                        break
        except Exception:
            pass

        # yfinance `dividendYield` is *already a percent* (NVDA→0.51 means
        # 0.51%); do NOT multiply by 100. Empty/None → None.
        div_yield = _safe_float(info.get("dividendYield"))
        beta = _safe_float(info.get("beta"))
        short_ratio = (_safe_float(info.get("shortPercentOfFloat"), 0) or 0) * 100
        quick_ratio = _safe_float(info.get("quickRatio"))
        fcf_yield = (fcf / market_cap * 100) if market_cap else None
        fcf_coverage = (fcf / div_paid) if div_paid > 0 else None

        high_52 = _safe_float(info.get("fiftyTwoWeekHigh"))
        low_52 = _safe_float(info.get("fiftyTwoWeekLow"))
        range_pos = None
        if high_52 and low_52 and high_52 != low_52 and current_price is not None:
            range_pos = ((current_price - low_52) / (high_52 - low_52)) * 100

        total_revenue = None
        total_liabilities = None
        total_cash = None
        try:
            if quarterly_is is not None and not quarterly_is.empty and "Total Revenue" in quarterly_is.index:
                total_revenue = float(quarterly_is.loc["Total Revenue"].iloc[0])
            if quarterly_bs is not None and not quarterly_bs.empty:
                for key in (
                    "Total Liabilities Net Minority Interest",
                    "Total Liabilities",
                ):
                    if key in quarterly_bs.index:
                        total_liabilities = float(quarterly_bs.loc[key].iloc[0])
                        break
                if "Cash Cash Equivalents And Short Term Investments" in quarterly_bs.index:
                    total_cash = float(
                        quarterly_bs.loc["Cash Cash Equivalents And Short Term Investments"].iloc[0]
                    )
        except Exception:
            pass

        revenue_growth = (_safe_float(info.get("revenueGrowth"), 0) or 0) * 100
        earnings_growth = (_safe_float(info.get("earningsGrowth"), 0) or 0) * 100

        target_mean = _safe_float(info.get("targetMeanPrice"))
        target_median = _safe_float(info.get("targetMedianPrice"))
        num_analysts = info.get("numberOfAnalystOpinions") or 0
        recommendation = _safe_float(info.get("recommendationMean"))
        held_insiders = (_safe_float(info.get("heldPercentInsiders"), 0) or 0) * 100
        held_institutions = (_safe_float(info.get("heldPercentInstitutions"), 0) or 0) * 100

        sign = "+" if price_change >= 0 else ""
        out["quote"] = {
            "price": current_price,
            "change": price_change,
            "change_pct": price_change_pct,
            "sign": sign,
            "name": info.get("shortName") or info.get("longName") or ticker,
            "currency": info.get("currency") or "",
            "quarter": date_str,
        }
        out["sections"] = [
            {
                "key": "quote",
                "items": [
                    {"key": "price", "value": _fmt_num(current_price)},
                    {"key": "change", "value": f"{sign}{_fmt_num(price_change)} ({sign}{_fmt_num(price_change_pct)}%)"},
                ],
            },
            {
                "key": "val_metrics",
                "items": [
                    {"key": "market_cap", "value": _fmt_large(market_cap)},
                    {"key": "pe", "value": _fmt_num(pe_ratio)},
                    {"key": "forward_pe", "value": _fmt_num(forward_pe)},
                    {"key": "peg", "value": _fmt_num(peg_ratio)},
                    {"key": "pb", "value": _fmt_num(pb_ratio)},
                    {"key": "ev_ebitda", "value": _fmt_num(ev_ebitda)},
                ],
            },
            {
                "key": "profit_metrics",
                "items": [
                    {"key": "eps", "value": _fmt_num(eps, prefix="$")},
                    {"key": "roe", "value": _fmt_num(roe, suffix="%")},
                    {"key": "roa", "value": _fmt_num(roa, suffix="%")},
                    {"key": "roic", "value": _fmt_num(roic, suffix="%")},
                    {"key": "op_margin", "value": _fmt_num(operating_margin, suffix="%")},
                    {"key": "profit_margin", "value": _fmt_num(profit_margin, suffix="%")},
                ],
            },
            {
                "key": "yield_risk",
                "items": [
                    {"key": "div_yield", "value": _fmt_num(div_yield, suffix="%")},
                    {"key": "fcf_yield", "value": _fmt_num(fcf_yield, suffix="%")},
                    {"key": "short_ratio", "value": _fmt_num(short_ratio, suffix="%")},
                    {"key": "beta", "value": _fmt_num(beta)},
                    {"key": "quick_ratio", "value": _fmt_num(quick_ratio)},
                ],
            },
            {
                "key": "range_52w",
                "items": [
                    {"key": "high_52", "value": _fmt_num(high_52, prefix="$")},
                    {"key": "low_52", "value": _fmt_num(low_52, prefix="$")},
                    {"key": "range_pos", "value": _fmt_num(range_pos, suffix="%")},
                ],
            },
            {
                "key": "cashflow",
                "items": [
                    {"key": "fcf", "value": _fmt_large(fcf)},
                    {"key": "ocf", "value": _fmt_large(ocf)},
                    {"key": "fcf_yield", "value": _fmt_num(fcf_yield, suffix="%")},
                    {"key": "fcf_coverage", "value": _fmt_num(fcf_coverage)},
                ],
            },
            {
                "key": "revenue_growth",
                "items": [
                    {"key": "total_revenue", "value": _fmt_large(total_revenue)},
                    {"key": "total_cash", "value": _fmt_large(total_cash)},
                    {"key": "total_liab", "value": _fmt_large(total_liabilities)},
                    {"key": "rev_growth", "value": _fmt_num(revenue_growth, suffix="%")},
                    {"key": "earn_growth", "value": _fmt_num(earnings_growth, suffix="%")},
                ],
            },
            {
                "key": "analyst",
                "items": [
                    {"key": "target_mean", "value": _fmt_num(target_mean, prefix="$")},
                    {"key": "target_median", "value": _fmt_num(target_median, prefix="$")},
                    {"key": "num_analysts", "value": str(num_analysts)},
                    {"key": "recommendation", "value": _fmt_num(recommendation)},
                    {"key": "insiders", "value": _fmt_num(held_insiders, suffix="%")},
                    {"key": "institutions", "value": _fmt_num(held_institutions, suffix="%")},
                ],
            },
        ]
        out["ok"] = True
    except Exception as e:
        out["error"] = str(e)
    return out


# ── Technical indicators ──────────────────────────────────────────

def calc_kd(df: pd.DataFrame, n=9, m1=3, m2=3) -> pd.DataFrame:
    df = df.copy()
    df["lowest_low"] = df["Low"].rolling(window=n).min()
    df["highest_high"] = df["High"].rolling(window=n).max()
    rng = df["highest_high"] - df["lowest_low"]
    df["RSV"] = np.where(rng == 0, 50, (df["Close"] - df["lowest_low"]) / rng * 100)
    df["RSV"] = df["RSV"].fillna(50)
    df["K"] = df["RSV"].ewm(span=m1, adjust=False).mean()
    df["D"] = df["K"].ewm(span=m2, adjust=False).mean()
    return df


def calc_ma(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MA5"] = df["Close"].rolling(window=5).mean().fillna(0)
    df["MA20"] = df["Close"].rolling(window=20).mean().fillna(0)
    return df


def calc_macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
    df = df.copy()
    ema_fast = df["Close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["Close"].ewm(span=slow, adjust=False).mean()
    df["DIF"] = ema_fast - ema_slow
    df["DEA"] = df["DIF"].ewm(span=signal, adjust=False).mean()
    df["MACD_hist"] = (df["DIF"] - df["DEA"]) * 2
    return df


def _to_unix_time(series) -> pd.Series:
    """Convert DatetimeIndex/Series to unix seconds for Lightweight Charts."""
    s = pd.to_datetime(series)
    # handle timezone-aware
    try:
        if getattr(s.dt, "tz", None) is not None:
            s = s.dt.tz_convert("UTC").dt.tz_localize(None)
    except Exception:
        try:
            s = s.dt.tz_localize(None)
        except Exception:
            pass
    return (s.astype("int64") // 10**9).astype(int)


def get_chart_data(ticker: str, period_type: str = "day") -> dict:
    """Return kline / volume / KD / MACD for Lightweight Charts."""
    cfg = CHART_PERIODS.get(period_type, CHART_PERIODS["day"])
    try:
        t = yf.Ticker(ticker)
        # month: try 17y first, fall back to max
        try:
            df = t.history(period=cfg["period"], interval=cfg["interval"])
        except Exception:
            df = t.history(period="max", interval=cfg["interval"])

        if df is None or df.empty:
            return {"kline": [], "volume": [], "K": [], "D": [], "DIF": [], "DEA": [], "MACD": [], "MA5": [], "MA20": [], "source": []}

        df = df.reset_index()
        # Date column name may vary
        date_col = "Date" if "Date" in df.columns else df.columns[0]
        df = calc_kd(df)
        df = calc_macd(df)
        df = calc_ma(df)
        df["time"] = _to_unix_time(df[date_col])

        # Lightweight Charts needs unique ascending times
        df = df.drop_duplicates(subset=["time"], keep="last").sort_values("time")

        # Skip first 30 rows to avoid MA5/MA20 break points (matching tradingView.py)
        df = df.iloc[30:].reset_index(drop=True)

        kline, volume, k_data, d_data = [], [], [], []
        dif_data, dea_data, macd_data = [], [], []
        ma5_data, ma20_data = [], []
        source = []

        for idx, row in df.iterrows():
            tm = int(row["time"])
            o, h, l, c = float(row["Open"]), float(row["High"]), float(row["Low"]), float(row["Close"])
            vol = float(row["Volume"]) if "Volume" in row and not pd.isna(row["Volume"]) else 0.0
            k_val = float(row["K"]) if not pd.isna(row.get("K")) else 0.0
            d_val = float(row["D"]) if not pd.isna(row.get("D")) else 0.0
            dif_val = float(row["DIF"]) if not pd.isna(row.get("DIF")) else 0.0
            dea_val = float(row["DEA"]) if not pd.isna(row.get("DEA")) else 0.0
            macd_val = float(row["MACD_hist"]) if not pd.isna(row.get("MACD_hist")) else 0.0
            ma5_val = float(row["MA5"]) if not pd.isna(row.get("MA5")) else 0.0
            ma20_val = float(row["MA20"]) if not pd.isna(row.get("MA20")) else 0.0

            kline.append({"time": tm, "open": o, "high": h, "low": l, "close": c})
            volume.append({
                "time": tm,
                "value": vol,
                "color": "#4cd964" if c >= o else "#ff5e57",
            })
            k_data.append({"time": tm, "value": k_val})
            d_data.append({"time": tm, "value": d_val})
            dif_data.append({"time": tm, "value": dif_val})
            dea_data.append({"time": tm, "value": dea_val})
            macd_data.append({
                "time": tm,
                "value": macd_val,
                "color": "#4cd964" if macd_val >= 0 else "#ff5e57",
            })
            ma5_data.append({"time": tm, "value": ma5_val})
            ma20_data.append({"time": tm, "value": ma20_val})
            source.append({
                "idx": idx,
                "date": row[date_col].strftime("%Y-%m-%d") if hasattr(row[date_col], "strftime") else str(row[date_col])[:10],
                "open": o, "high": h, "low": l, "close": c,
                "volume": vol,
                "K": k_val, "D": d_val,
                "MA5": ma5_val, "MA20": ma20_val,
                "DIF": dif_val, "DEA": dea_val, "MACD": macd_val,
            })

        return {
            "kline": kline,
            "volume": volume,
            "K": k_data,
            "D": d_data,
            "DIF": dif_data,
            "DEA": dea_data,
            "MACD": macd_data,
            "MA5": ma5_data,
            "MA20": ma20_data,
            "source": source,
            "ticker": ticker,
            "period": period_type,
        }
    except Exception as e:
        return {
            "kline": [], "volume": [], "K": [], "D": [],
            "DIF": [], "DEA": [], "MACD": [], "MA5": [], "MA20": [],
            "source": [], "error": str(e),
        }


def format_quote_row(q: dict) -> dict:
    """Add display strings for frontend."""
    price = q.get("price")
    change = q.get("change")
    change_pct = q.get("change_pct")
    direction = "flat"
    if change is not None:
        if change > 0:
            direction = "up"
        elif change < 0:
            direction = "down"

    def snum(v, digits=2, signed=False):
        if v is None:
            return "—"
        if signed:
            return f"{v:+,.{digits}f}"
        return f"{v:,.{digits}f}"

    return {
        **q,
        "price_str": snum(price),
        "change_str": snum(change, signed=True),
        "change_pct_str": (snum(change_pct, signed=True) + "%") if change_pct is not None else "—",
        "volume_str": _fmt_volume(q.get("volume")),
        "direction": direction,
    }
