# yfWatchlist — 全球自選股觀測清單 / Global Watchlist Manager

> **Language / 語言**
> 
> [English Version](#english-version) | [中文版](#中文版)

---

<a id="chinese-version"></a>

## 專案起源與開發歷程

### 起因

本專案源自於對全球金融市場即時監控的需求。身為投資人，需要一個能同時追蹤美股、台股、港股、陸股以及全球主要指數的工具，但市面上的方案要麼需要付費訂閱，要麼資訊不夠即時、介面不夠直覺。

### 開發過程

1. **原型階段** — 從 
   run8.py 開始，最初只是一個命令列介面的個股財務數據監控中心，利用 yfinance 抓取單一股票的即時報價、估值指標、獲利指標、殖利率、現金流等 8 大類財務數據，並輸出 Markdown 報告。

2. **圖表化階段** — 引入     tradingView.py，將數據視覺化，使用 Lightweight Charts 套件繪製專業級 K 線圖、成交量圖、KDJ 與 MACD 技術指標，實現三圖同步十字線游標。

3. **Web 化階段** — 透過 FastHTML 框架將應用程式轉為 Web 應用，使用 main.py 作為主程式，提供完整的 HTTP API，支援前端互動操作。

4. **完善階段** — 加入多觀測清單管理、多語言支援（繁中/簡中/英文）、多種玻璃透視主題、價格提醒系統、搜尋功能、自動更新等完整功能。

---

## 功能特色

### 股票報價（延遲）

- 透過 Yahoo Finance 獲取全球股票報價（延遲 15-20 分鐘）
- 支援美股、台股、港股、陸股、ETF、指數等多種金融商品
- 並行抓取多檔股票報價，提升載入速度
- 顯示價格、漲跌、漲跌幅、成交量

### 多觀測清單管理

- 建立、刪除多個觀測清單
- 自由切換不同觀測清單
- 支援標的上下排序
- 預設包含 14 個全球主要指數（道瓊、S&P500、納斯達克、費半、加權指數等）

### 基本面資訊

- 點擊「瀏覽」按鈕即可查看個股完整基本面資料
- 估值指標：市值、本益比、預期本益比、PEG、股價淨值比、EV/EBITDA
- 獲利指標：EPS、ROE、ROA、ROIC、營業利潤率、純利率
- 殖利率與風險：殖利率、FCF 殖利率、放空比例、貝他值、速動比率
- 52 週區間：高點、低點、區間位置百分比
- 現金流：自由現金流、營業現金流、FCF 股利覆蓋
- 營收與成長：總營收、總現金、總負債、營收成長率、盈餘成長率
- 分析師評等：平均/中位目標價、分析師人數、推薦均值、內部人/機構持股

### 技術分析圖表

- K 線圖（日 K、週 K、月 K）
- 成交量圖（紅綠柱狀）
- KDJ 隨機指標（K 線、D 線）
- MACD 指標（DIF、DEA、MACD 柱狀）
- MA5 / MA20 均線疊加
- 三圖同步十字線游標與時間軸同步
- 支援滑鼠懸停查看開高低收詳細資訊

### 相關新聞

- 自動抓取個股 Yahoo Finance 相關新聞
- 顯示新聞標題、來源、发布时间
- 支援點擊跳轉原文連結

### 價格提醒

- 設定個股價格提醒（高於/低於目標價）
- 系統自動檢查是否觸發
- 觸發時發送視覺通知
- 支援多組提醒同時監控

### 搜尋功能

- 本地搜尋：內建 top250_tickers.json 索引（包含 A 股、港股等常用標的）
- 線上搜尋：透過 Yahoo Finance 搜尋全球股票
- 即時顯示搜尋結果，支援一鍵加入觀測清單

### 多語言支援

- 繁體中文（zh-TW）
- 简体中文（zh-CN）
- English（en）
- 即時切換，無需重新載入

### 主題與外觀

- 8 種精美主題：跟隨系統、淺色、深色、冰藍透玻璃、霧紫透玻璃、青綠透玻璃、煙藍透玻璃、煙灰綠透玻璃
- 可自訂字型、字體大小
- 介面縮放（75% ~ 137.5%）
- 玻璃透視（Glassmorphism）設計風格

### 自動更新

- 支援 5 分鐘、15 分鐘、60 分鐘自動刷新
- 手動刷新按鈕
- 進程結束時自動儲存狀態

---

## 技術架構

| 層級   | 技術                                     |
| ---- | -------------------------------------- |
| 後端框架 | FastHTML（基於 Starlette 的 Python Web 框架） |
| 資料來源 | yfinance（Yahoo Finance API）            |
| 圖表引擎 | Lightweight Charts（TradingView 開源圖表庫）  |
| 資料儲存 | 本地 JSON 檔案（watchlist_data.json）        |
| 資料處理 | pandas + numpy                         |

---

## 專案結構

```
yfWatchlist/
├── main.py              # FastHTML 主程式，定義所有頁面與 API 路由
├── config.py            # 應用程式設定與常數
├── market.py            # 市場資料抓取：報價、基本面、技術指標
├── news.py              # Yahoo Finance 新聞抓取
├── search_svc.py        # 雙來源股票搜尋（本地 + Yahoo）
├── storage.py           # 本地 JSON 狀態持久化
├── i18n.py              # 多語言字串（zh-TW / zh-CN / en）
├── run8.py              # 原始命令列版本（個股財務報告產生器）
├── tradingView.py       # 原始圖表原型
├── requirements.txt     # Python 相依套件
├── yfWatchlist.bat      # Windows 批次啟動檔
├── yfWatchlist.ico      # 應用程式圖示
├── yfWatchlist.png      # 應用程式圖片
├── top250_tickers.json  # 本地股票索引（A 股、港股、美股、台灣股市等）
├── watchlist_data.json  # 使用者觀測清單與設定資料
└── static/
    ├── app.js           # 前端 JavaScript 邏輯
    ├── styles.css       # 全域 CSS 樣式（含 8 種主題）
    └── yfWatchlist.ico  # 網頁 favicon
```

---

## 環境需求

- Python 3.10 以上
- Windows 10/11（主要開發平台，其他平台理論上可運行但未充分測試）

---

## 安裝與啟動

### 方法一：直接執行（推薦開發模式）

```bash

# 1. 複製專案到本機
git clone https://github.com/aneterw/yfWatchlist.git
cd yfWatchlist

# 2. 安裝相依套件
pip install -r requirements.txt

# 3. 啟動（瀏覽器存取 http://localhost:5001）
python main.py
```

### 方法二：使用批次檔啟動（Windows）

```bash

# 雙擊 yfWatchlist.bat 即可啟動

yfWatchlist.bat
```

---

## 使用說明

### 基本操作

1. **查看報價** — 啟動後自動載入預設觀測清單（14 個全球主要指數），即時顯示各指數報價
2. **搜尋股票** — 在搜尋欄位輸入股票代碼或名稱（至少 2 個字元），從本地或 Yahoo Finance 搜尋結果中點擊「加入」
3. **瀏覽個股** — 點擊表格中的「🔍」按鈕，開啟個股詳情面板，可切換「基本資訊」、「技術分析」、「相關新聞」三個分頁
4. **切換觀測清單** — 使用工具列的下拉選單切換不同觀測清單
5. **新增觀測清單** — 點擊「＋新清單」按鈕，輸入名稱即可建立
6. **刪除觀測清單** — 點擊「🗑 刪除清單」按鈕，需經過兩次確認（含輸入名稱驗證）
7. **排序標的** — 使用「↑」和「↓」按鈕調整標的順序
8. **刪除標的** — 點擊「🗑」按鈕並確認即可移除
9. **價格提醒** — 點擊「價格提醒」按鈕，設定目標價與條件（高於/低於）
10. **設定** — 點擊「設定」按鈕，可調整語言、主題、字型、字體大小、縮放比例、自動更新頻率

### 快捷操作

- **全部更新** — 點擊「全部更新」按鈕，重新抓取所有標的的最新報價
- **更新本頁** — 點擊「更新本頁」按鈕，重新整理當前頁面資料
- **自動更新** — 使用工具列的下拉選單設定自動更新頻率（暫停 / 5 分鐘 / 15 分鐘 / 60 分鐘）

---

## API 端點

| 方法       | 路徑                               | 說明               |
| -------- | -------------------------------- | ---------------- |
| GET      | /api/quotes                      | 取得當前觀測清單所有報價     |
| GET      | /api/quote?ticker=XXX            | 取得單一標的報價         |
| GET      | /api/search?q=XXX                | 搜尋股票（本地 + Yahoo） |
| POST     | /api/add                         | 新增標的到觀測清單        |
| POST     | /api/remove                      | 從觀測清單移除標的        |
| POST     | /api/move                        | 調整標的順序           |
| POST     | /api/watchlist/switch            | 切換觀測清單           |
| POST     | /api/watchlist/add               | 新增觀測清單           |
| POST     | /api/watchlist/delete            | 刪除觀測清單           |
| GET      | /api/fundamentals?ticker=XXX     | 取得個股基本面資料        |
| GET      | /api/chart?ticker=XXX&period=day | 取得 K 線圖資料        |
| GET      | /api/news?ticker=XXX             | 取得個股相關新聞         |
| GET/POST | /api/settings                    | 讀取/儲存設定          |
| GET/POST | /api/alerts                      | 讀取/新增價格提醒        |
| POST     | /api/alerts/delete               | 刪除價格提醒           |
| POST     | /api/alerts/check                | 檢查提醒是否觸發         |
| POST     | /api/save                        | 強制儲存狀態           |

---

## 授權條款

本專案採用 MIT 授權條款開源，詳見 [LICENCE.md](LICENCE.md)。

---

## 免責聲明

- 所有報價資訊來自 Yahoo Finance，可能延遲 15-20 分鐘
- 所有資訊僅供參考，不構成任何投資建議
- 實際交易價格請以券商或交易所為準

---

<a id="english-version"></a>

## Project Origin & Development History

### Motivation

This project originated from the need for real-time monitoring of global financial markets. As an investor, there was a need for a tool that could simultaneously track US stocks, Taiwan stocks, Hong Kong stocks, China A-shares, and global major indices. However, existing solutions were either expensive subscriptions, lacked real-time data, or had unintuitive interfaces.

### Development Process

1. **Prototype Phase** — Started with `run8.py`, originally a command-line stock financial data monitoring center that used `yfinance` to fetch real-time quotes, valuation metrics, profitability indicators, dividend yields, and cash flow data across 8 major financial categories, outputting Markdown reports.

2. **Visualization Phase** — Introduced `tradingView.py` to visualize data using the Lightweight Charts library, drawing professional-grade candlestick charts, volume charts, KDJ and MACD technical indicators with synchronized crosshair cursors across three charts.

3. **Web Phase** — Converted the application to a web app using the FastHTML framework, with `main.py` as the main entry point providing a complete HTTP API for frontend interactive operations.

4. **Polish Phase** — Added multi-watchlist management, multi-language support (Traditional/Simplified Chinese, English), glassmorphism themes, price alert system, search functionality, auto-refresh, and other complete features.

---

## Features

### Stock Quotes (Delayed)

- Fetches global stock quotes via Yahoo Finance (15-20 minute delay)
- Supports US stocks, Taiwan stocks, Hong Kong stocks, China A-shares, ETFs, indices, and more
- Concurrent quote fetching for faster loading
- Displays price, change, change percentage, and volume

### Multi-Watchlist Management

- Create and delete multiple watchlists
- Freely switch between different watchlists
- Reorder symbols with up/down buttons
- Pre-loaded with 14 global major indices (Dow Jones, S&P 500, NASDAQ, PHLX Semiconductor, Taiwan Weighted, etc.)

### Fundamentals

- Click "Browse" to view complete fundamental data for any stock
- Valuation: Market Cap, P/E, Forward P/E, PEG, P/B, EV/EBITDA
- Profitability: EPS, ROE, ROA, ROIC, Operating Margin, Profit Margin
- Yield & Risk: Dividend Yield, FCF Yield, Short %, Beta, Quick Ratio
- 52-Week Range: High, Low, Range Position percentage
- Cash Flow: Free Cash Flow, Operating Cash Flow, FCF Dividend Coverage
- Revenue & Growth: Total Revenue, Total Cash, Total Liabilities, Revenue Growth, Earnings Growth
- Analyst Ratings: Mean/Median Target Price, Number of Analysts, Recommendation Mean, Insider/Institutional Holdings

### Technical Analysis Charts

- Candlestick charts (Daily, Weekly, Monthly)
- Volume chart (red/green bars)
- KDJ stochastic indicator (K line, D line)
- MACD indicator (DIF, DEA, MACD histogram)
- MA5 / MA20 moving average overlays
- Synchronized crosshair cursor and time axis across three charts
- Hover to view detailed OHLCV information

### Related News

- Automatically fetches Yahoo Finance news for each stock
- Displays news title, publisher, and publish time
- Click to open the original article link

### Price Alerts

- Set price alerts for stocks (above/below target price)
- System automatically checks for triggers
- Visual notification when triggered
- Supports multiple simultaneous alerts

### Search

- Local search: Built-in top250_tickers.json index (includes A-shares, Hong Kong stocks, etc.)
- Online search: Search global stocks via Yahoo Finance
- Real-time search results with one-click add to watchlist

### Multi-Language Support

- Traditional Chinese (zh-TW)
- Simplified Chinese (zh-CN)
- English (en)
- Instant switching without page reload

### Themes & Appearance

- 8 beautiful themes: System, Light, Dark, Frost Glass, Purple Glass, Cyan Glass, Smoke Blue Glass, Smoke Green Glass
- Customizable font family and font size
- UI zoom (75% ~ 137.5%)
- Glassmorphism design style

### Auto Refresh

- Supports 5-minute, 15-minute, 60-minute auto refresh
- Manual refresh buttons
- Auto-save state on process exit

---

## Tech Stack

| Layer             | Technology                                                    |
| ----------------- | ------------------------------------------------------------- |
| Backend Framework | FastHTML (Python web framework based on Starlette)            |
| Data Source       | yfinance (Yahoo Finance API)                                  |
| Chart Engine      | Lightweight Charts (TradingView open-source charting library) |
| Data Storage      | Local JSON file (`watchlist_data.json`)                       |
| Data Processing   | pandas + numpy                                                |

---

## Project Structure

```
yfWatchlist/
├── main.py              # FastHTML main app, defines all pages and API routes
├── config.py            # Application configuration and constants
├── market.py            # Market data: quotes, fundamentals, technical indicators
├── news.py              # Yahoo Finance news fetching
├── search_svc.py        # Dual-source stock search (local + Yahoo)
├── storage.py           # Local JSON state persistence
├── i18n.py              # Multi-language strings (zh-TW / zh-CN / en)
├── run8.py              # Original CLI version (stock financial report generator)
├── tradingView.py       # Original chart prototype
├── requirements.txt     # Python dependencies
├── yfWatchlist.bat      # Windows batch launcher
├── yfWatchlist.ico      # Application icon
├── yfWatchlist.png      # Application image
├── top250_tickers.json  # Local stock index (A-shares, HK stocks, US stocks, Taiwan stocks, etc.)
├── watchlist_data.json  # User watchlist and settings data
└── static/
    ├── app.js           # Frontend JavaScript logic
    ├── styles.css       # Global CSS styles (8 themes)
    └── yfWatchlist.ico  # Web favicon
```

---

## Requirements

- Python 3.10+
- Windows 10/11 (primary development platform; other platforms may work but are not fully tested)

---

## Installation & Launch

### Method 1: Direct Execution (Recommended for Development)

```bash
# 1. Clone the repository
git clone https://github.com/aneterw/yfWatchlist.git
cd yfWatchlist

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch (browser access at http://localhost:5001)
python main.py
```

### Method 2: Batch File Launch (Windows)

```bash
# Double-click yfWatchlist.bat to launch
yfWatchlist.bat
```

---

## Usage Guide

### Basic Operations

1. **View Quotes** — On startup, automatically loads the default watchlist (14 global major indices) with real-time quotes
2. **Search Stocks** — Type a ticker or name in the search field (minimum 2 characters), click "Add" from local or Yahoo Finance results
3. **Browse Stock Details** — Click the magnifier button in the table to open the detail panel with three tabs: "Fundamentals", "Technical Chart", "Related News"
4. **Switch Watchlist** — Use the dropdown in the toolbar to switch between watchlists
5. **Create Watchlist** — Click "+ New list" and enter a name
6. **Delete Watchlist** — Click "Delete list" and confirm twice (including typing the name)
7. **Reorder Symbols** — Use the up and down arrow buttons to adjust symbol order
8. **Remove Symbol** — Click the trash button and confirm to remove
9. **Price Alerts** — Click "Price Alerts" to set target price and condition (above/below)
10. **Settings** — Click "Settings" to adjust language, theme, font, font size, zoom level, and auto-refresh interval

### Quick Actions

- **Refresh All** — Click "Refresh All" to re-fetch quotes for all symbols
- **Refresh Page** — Click "Refresh Page" to refresh current page data
- **Auto Refresh** — Use the toolbar dropdown to set auto-refresh interval (Pause / 5 min / 15 min / 60 min)

---

## API Endpoints

| Method   | Path                               | Description                          |
| -------- | ---------------------------------- | ------------------------------------ |
| GET      | `/api/quotes`                      | Get all quotes for current watchlist |
| GET      | `/api/quote?ticker=XXX`            | Get quote for a single symbol        |
| GET      | `/api/search?q=XXX`                | Search stocks (local + Yahoo)        |
| POST     | `/api/add`                         | Add symbol to watchlist              |
| POST     | `/api/remove`                      | Remove symbol from watchlist         |
| POST     | `/api/move`                        | Reorder symbol position              |
| POST     | `/api/watchlist/switch`            | Switch watchlist                     |
| POST     | `/api/watchlist/add`               | Create new watchlist                 |
| POST     | `/api/watchlist/delete`            | Delete watchlist                     |
| GET      | `/api/fundamentals?ticker=XXX`     | Get stock fundamental data           |
| GET      | `/api/chart?ticker=XXX&period=day` | Get K-line chart data                |
| GET      | `/api/news?ticker=XXX`             | Get related news for a stock         |
| GET/POST | `/api/settings`                    | Read/save settings                   |
| GET/POST | `/api/alerts`                      | Read/add price alerts                |
| POST     | `/api/alerts/delete`               | Delete price alert                   |
| POST     | `/api/alerts/check`                | Check alert triggers                 |
| POST     | `/api/save`                        | Force save state                     |

---

## License

This project is open source under the MIT License. See [LICENCE.md](LICENCE.md) for details.

---

## Disclaimer

- All quote data comes from Yahoo Finance and may be delayed by 15-20 minutes
- All information is for reference only and does not constitute investment advice
- Actual trading prices should be verified with your broker or exchange
