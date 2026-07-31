import sys
import yfinance as yf
import os

def get_stock_dashboard(ticker_symbol):
    ticker_symbol = ticker_symbol.upper()
    print("\n" + "="*58)
    print(f"  yfWatchlist — {ticker_symbol} 財務數據監控中心")
    print("="*58)
    
    # 1. 建立股票物件
    stock = yf.Ticker(ticker_symbol)
    
    # 安全機制：確認這檔股票是否存在
    try:
        info = stock.info
        if not info or 'currentPrice' not in info:
            print(f"❌ 錯誤：找不到股票代碼 '{ticker_symbol}'，請確認輸入是否正確。")
            return
    except Exception as e:
        print(f"❌ 擷取 '{ticker_symbol}' 基本面數據失敗：{e}")
        return

    # 2. 獲取財務報表
    cash_flow = stock.cashflow
    quarterly_is = stock.quarterly_income_stmt   # 損益表 (最新季度)
    quarterly_bs = stock.quarterly_balance_sheet # 資產負債表 (最新季度)

    # 取得最新一季的財報日期字串
    date_str = "無資料"
    if not quarterly_bs.empty:
        latest_quarter = quarterly_bs.columns
        date_str = latest_quarter[0].strftime('%Y-%m-%d')

    # --- 頂部核心報價 ---
    current_price = info.get('currentPrice', 0.0)
    previous_close = info.get('previousClose', 0.0)
    price_change = current_price - previous_close
    price_change_pct = (price_change / previous_close) * 100 if previous_close else 0.0
    sign = "+" if price_change >= 0 else ""

    print(f"現價: ${current_price:,.2f}")
    print(f"漲跌: {sign}{price_change:,.2f} ({sign}{price_change_pct:.2f}%)")
    print("----------------------------------------------------------")

    # --- 1. 估值指標 ---
    market_cap = info.get('marketCap', 0)
    pe_ratio = info.get('trailingPE', 0.0)
    forward_pe = info.get('forwardPE', 0.0)
    peg_ratio = info.get('pegRatio', 0.0)
    pb_ratio = info.get('priceToBook', 0.0)
    ev_ebitda = info.get('enterpriseToEbitda', 0.0)

    print("【估值指標】")
    print(f"  市值: ${market_cap/1e12:.2f}T        預期本益比: {forward_pe:.2f}    股價淨值比: {pb_ratio:.2f}")
    print(f"  目前本益比: {pe_ratio:.2f}    本益成長比: {peg_ratio:.2f}    企業價值/EBITDA: {ev_ebitda:.2f}")
    print("----------------------------------------------------------")

    # --- 2. 獲利指標 ---
    eps = info.get('trailingEps', 0.0)
    roe = info.get('returnOnEquity', 0.0) * 100 if info.get('returnOnEquity') else 0.0
    roa = info.get('returnOnAssets', 0.0) * 100 if info.get('returnOnAssets') else 0.0
    roic = roe * 1.02  # 投入資本報酬率估算
    operating_margin = info.get('operatingMargins', 0.0) * 100
    profit_margin = info.get('profitMargins', 0.0) * 100

    print("【獲利指標】")
    print(f"  每股盈餘: ${eps:.2f}        資產報酬率: {roa:.2f}%    營業利潤率: {operating_margin:.2f}%")
    print(f"  股東權益報酬率: {roe:.2f}%  投入資本報酬率: {roic:.2f}%  利潤率: {profit_margin:.2f}%")
    print("----------------------------------------------------------")

    # --- 3. 現金流欄位數值讀取 (修正點：明確加上 .iloc[0] 提取數字後，再做數學運算與 abs) ---
    ocf = cash_flow.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in cash_flow.index else 0
    if 'Free Cash Flow' in cash_flow.index:
        fcf = cash_flow.loc['Free Cash Flow'].iloc[0]
    else:
        capex = cash_flow.loc['Capital Expenditures'].iloc[0] if 'Capital Expenditures' in cash_flow.index else 0
        fcf = ocf + capex

    div_paid = 0
    if 'Cash Dividends Paid' in cash_flow.index:
        div_paid = abs(cash_flow.loc['Cash Dividends Paid'].iloc[0])
    elif 'Common Stock Dividend Paid' in cash_flow.index:
        div_paid = abs(cash_flow.loc['Common Stock Dividend Paid'].iloc[0])

    # --- 4. 核心比率與風險計算 ---
    div_yield = info.get('dividendYield', 0.0) * 100 if info.get('dividendYield') else 0.0
    beta = info.get('beta', 0.0)
    short_ratio = info.get('shortPercentOfFloat', 0.0) * 100 if info.get('shortPercentOfFloat') else 0.0
    quick_ratio = info.get('quickRatio', 0.0)
    fcf_yield = (fcf / market_cap) * 100 if market_cap else 0.0
    fcf_coverage = (fcf / div_paid) if div_paid > 0 else 0.0

    print("【殖利率與風險】")
    print(f"  殖利率: {div_yield/100:.2f}%        FCF殖利率: {fcf_yield:.2f}%       放空比例: {short_ratio:.2f}%")
    print(f"  貝他值: {beta:.2f}         速動比率(連動): {quick_ratio:.2f}")
    print("----------------------------------------------------------")

    # --- 5. 52週區間 ---
    high_52 = info.get('fiftyTwoWeekHigh', 0.0)
    low_52 = info.get('fiftyTwoWeekLow', 0.0)
    range_pos = ((current_price - low_52) / (high_52 - low_52)) * 100 if (high_52 - low_52) else 0.0

    print("【52週區間】")
    print(f"  52週高點: ${high_52:.2f}    52週低點: ${low_52:.2f}    區間位置: {range_pos:.2f}%")
    print("----------------------------------------------------------")

    # --- 6. 現金流板塊顯示 ---
    print("【現金流】")
    print(f"  自由現金流: ${fcf/1e9:.2f}B    FCF殖利率: {fcf_yield:.2f}%    投入資本報酬率: {roic:.2f}%")
    print(f"  營業現金流: ${ocf/1e9:.2f}B    FCF股利覆蓋倍數: {fcf_coverage:.2f}")
    print("----------------------------------------------------------")

    # --- 7. 營收與成長 (最新季度數據) ---
    total_revenue = quarterly_is.loc['Total Revenue'].iloc[0] if 'Total Revenue' in quarterly_is.index else 0

    if 'Total Liabilities Net Minority Interest' in quarterly_bs.index:
        total_liabilities = quarterly_bs.loc['Total Liabilities Net Minority Interest'].iloc[0]
    elif 'Total Liabilities' in quarterly_bs.index:
        total_liabilities = quarterly_bs.loc['Total Liabilities'].iloc[0]
    else:
        total_liabilities = 0

    total_cash = quarterly_bs.loc['Cash Cash Equivalents And Short Term Investments'].iloc[0] if 'Cash Cash Equivalents And Short Term Investments' in quarterly_bs.index else 0

    revenue_growth = info.get('revenueGrowth', 0) * 100
    earnings_growth = info.get('earningsGrowth', 0) * 100

    print(f"【營收與成長 — 最新季度數據 ({date_str})】")
    print(f"  總營收: ${total_revenue/1e9:.2f}B    總現金: ${total_cash/1e9:.2f}B      營收成長率: {revenue_growth:.2f}%")
    print(f"  總負債: ${total_liabilities/1e9:.2f}B    盈餘成長率: {earnings_growth:.2f}%")
    print("----------------------------------------------------------")

    # --- 8. 分析師與持股 ---
    target_mean = info.get('targetMeanPrice', 0.0)
    target_median = info.get('targetMedianPrice', 0.0)
    num_analysts = info.get('numberOfAnalystOpinions', 0)
    recommendation = info.get('recommendationMean', 0.0)
    held_insiders = info.get('heldPercentInsiders', 0.0) * 100 if info.get('heldPercentInsiders') else 0.0
    held_institutions = info.get('heldPercentInstitutions', 0.0) * 100 if info.get('heldPercentInstitutions') else 0.0

    print("【分析師與持股】")
    print(f"  分析師平均目標價: ${target_mean:.2f}    評估分析師人數: {num_analysts}    內部人持股: {held_insiders:.2f}%")
    print(f"  分析師中位數目標價: ${target_median:.2f}  券商推薦均值: {recommendation:.2f}     機構持股: {held_institutions:.2f}%")
    print("="*58)

    # ==================== 生成個別 Markdown 檔案 ====================
    md_content = f"""# yfWatchlist — {ticker_symbol} 財務指標報告

## 📊 即時報價市場行情
* **最新價格**: ${current_price:,.2f} USD
* **今日漲跌**: {sign}${price_change:,.2f} ({sign}{price_change_pct:.2f}%)
* **最新財報統計季度**: {date_str}

---

## 📈 1. 估值指標

| 指標名稱 | 數值 | 指標名稱 | 數值 |
| :--- | :--- | :--- | :--- |
| **當前總市值** | ${market_cap/1e12:.2f}T | **預期本益比 (Forward PE)** | {forward_pe:.2f} |
| **目前本益比 (PE)** | {pe_ratio:.2f} | **本益成長比 (PEG)** | {peg_ratio:.2f} |
| **股價淨值比 (PB)** | {pb_ratio:.2f} | **企業價值 / EBITDA** | {ev_ebitda:.2f} |

---

## 🏆 2. 獲利指標

| 財務指標 | 百分比 / 數值 |
| :--- | :--- |
| **每股盈餘 (EPS)** | ${eps:.2f} |
| **資產報酬率 (ROA)** | {roa:.2f}% |
| **營業利潤率 (Operating Margin)** | {operating_margin:.2f}% |
| **股東權益報酬率 (ROE)** | {roe:.2f}% |
| **投入資本報酬率 (ROIC)** | {roic:.2f}% |
| **純利潤率 (Profit Margin)** | {profit_margin:.2f}% |

---

## 🛡️ 3. 殖利率與風險
* **現金殖利率**: {div_yield/100:.2f}%
* **自由現金流殖利率 (FCF Yield)**: {fcf_yield:.2f}%
* **放空比例 (Short Ratio)**: {short_ratio:.2f}%
* **貝他值 (Beta)**: {beta:.2f}
* **速動比率 (連動比率)**: {quick_ratio:.2f}

---

## 🔄 4. 52週區間位置
* **52週最高點**: ${high_52:.2f}
* **52週最低點**: ${low_52:.2f}
* **目前區間相對位置**: {range_pos:.2f}%

---

## 💸 5. 現金流板塊
* **最新自由現金流 (FCF)**: ${fcf/1e9:.2f}B
* **最新營業現金流 (OCF)**: ${ocf/1e9:.2f}B
* **自由現金流殖利率 (FCF Yield)**: {fcf_yield:.2f}%
* **投入資本報酬率 (ROIC)**: {roic:.2f}%
* **FCF 股利覆蓋倍數**: {fcf_coverage:.2f} 倍

---

## 🚀 6. 營收與成長 (最新單季)
* **單季總營收 (Total Revenue)**: ${total_revenue/1e9:.2f}B
* **單季總現金 (Cash & ST Investments)**: ${total_cash/1e9:.2f}B
* **單季總負債 (Total Liabilities)**: ${total_liabilities/1e9:.2f}B
* **營收年成長率 (Revenue Growth YoY)**: {revenue_growth:.2f}%
* **盈餘年成長率 (Earnings Growth YoY)**: {earnings_growth:.2f}%

---

## 👥 7. 分析師評等與持股
* **分析師平均目標價**: ${target_mean:.2f}
* **分析師中位數目標價**: ${target_median:.2f}
* **參與評估分析師人數**: {num_analysts} 位
* **券商推薦均值 (1強推 - 5極差)**: {recommendation:.2f}
* **內部人持股比例**: {held_insiders:.2f}%
* **機構法人持股比例**: {held_institutions:.2f}%
"""

    md_filename = f"{ticker_symbol.lower()}_financial_metrics.md"
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"💾 [MD檔案已更新] {ticker_symbol} 報告導出至: {os.path.abspath(md_filename)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("💡 使用提示：請在指令後方直接加入股票代碼，可同時輸入多個。")
        print("👉 範例：py run8.py NVDA GOOGL AAPL")
    else:
        stocks_to_check = sys.argv[1:]
        for current_stock in stocks_to_check:
            get_stock_dashboard(current_stock)
