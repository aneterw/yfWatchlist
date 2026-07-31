"""Application defaults and constants."""
import sys
from pathlib import Path

# Resolve base dir both for `python main.py` and frozen .exe (PyInstaller).
# Frozen: data files live next to sys.executable (the .exe), not in temp _MEIPASS.
# Source: data files live next to this .py file (same as before).
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "watchlist_data.json"
TICKERS_FILE = BASE_DIR / "top250_tickers.json"
STATIC_DIR = BASE_DIR / "static"

# Default 14 global market indices (fixed order)
DEFAULT_INDICES = [
    {"name": "道瓊工業平均指數", "name_en": "Dow Jones Industrial Average", "name_cn": "道琼斯工业平均指数", "ticker": "^DJI"},
    {"name": "S&P500指數", "name_en": "S&P 500", "name_cn": "S&P500指数", "ticker": "^GSPC"},
    {"name": "納斯達克綜合指數", "name_en": "NASDAQ Composite", "name_cn": "纳斯达克综合指数", "ticker": "^IXIC"},
    {"name": "費城半導體指數", "name_en": "PHLX Semiconductor", "name_cn": "费城半导体指数", "ticker": "^SOX"},
    {"name": "台灣加權指數", "name_en": "Taiwan Weighted Index", "name_cn": "台湾加权指数", "ticker": "^TWII"},
    {"name": "上證綜指", "name_en": "SSE Composite", "name_cn": "上证综指", "ticker": "000001.SS"},
    {"name": "深證成指", "name_en": "SZSE Component", "name_cn": "深证成指", "ticker": "399001.SZ"},
    {"name": "恆生指數", "name_en": "Hang Seng Index", "name_cn": "恒生指数", "ticker": "^HSI"},
    {"name": "日經225指數", "name_en": "Nikkei 225", "name_cn": "日经225指数", "ticker": "^N225"},
    {"name": "韓國綜合股價指數", "name_en": "KOSPI", "name_cn": "韩国综合股价指数", "ticker": "^KS11"},
    {"name": "新加坡海峽時報指數", "name_en": "Straits Times Index", "name_cn": "新加坡海峡时报指数", "ticker": "^STI"},
    {"name": "德國DAX指數", "name_en": "DAX", "name_cn": "德国DAX指数", "ticker": "^GDAXI"},
    {"name": "法國CAC40指數", "name_en": "CAC 40", "name_cn": "法国CAC40指数", "ticker": "^FCHI"},
    {"name": "英國富時100指數", "name_en": "FTSE 100", "name_cn": "英国富时100指数", "ticker": "^FTSE"},
]

DEFAULT_WATCHLIST_NAME = "全球主要指數"

DEFAULT_SETTINGS = {
    "active_wl": DEFAULT_WATCHLIST_NAME,
    "watchlists": {
        DEFAULT_WATCHLIST_NAME: [
            {"name": item["name"], "ticker": item["ticker"]} for item in DEFAULT_INDICES
        ]
    },
    "lang": "zh-TW",
    "theme": "purple",
    "font_family": "Microsoft JhengHei, system-ui, sans-serif",
    "font_size": 14,
    "zoom": 100,
    "auto_refresh": 0,  # minutes: 0=pause, 5, 15, 60
    "alerts": [],
    "last_updated": None,
}

ZOOM_OPTIONS = [75, 87.5, 100, 112.5, 125, 137.5]
AUTO_REFRESH_OPTIONS = [0, 5, 15, 60]  # minutes
CHART_PERIODS = {
    "day": {"period": "1y", "interval": "1d"},
    "week": {"period": "5y", "interval": "1wk"},
    "month": {"period": "max", "interval": "1mo"},
}
