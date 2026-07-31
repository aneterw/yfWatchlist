from fasthtml.common import *
import yfinance as yf
import pandas as pd
import numpy as np
import json

app, rt = fast_app()

# JSON序列化：NaN全部轉0，前端永遠沒有null
class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return 0.0 if np.isnan(obj) else float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

CSS_STYLE = """
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: system-ui, -apple-system, sans-serif;
}
body {
    background-color: #161923;
    color: #e2e2e2;
    padding: 16px;
}
.wrapper {
    max-width: 1900px;
    margin: 0 auto;
    background: #1e222d;
    border-radius: 8px;
    overflow: hidden;
}
.top-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 18px 22px;
}
.stock-title {
    font-size: 23px;
    color: #ffffff;
    font-weight: 500;
}
.period-buttons button {
    background: #333846;
    color: #c2c8d4;
    border: none;
    padding: 8px 18px;
    border-radius: 6px;
    margin-left: 8px;
    font-size: 15px;
    cursor: pointer;
}
.period-buttons button.active {
    background: #5369e9;
    color: #fff;
}
.indicator-buttons {
    display: flex;
    gap: 6px;
}
.indicator-buttons button {
    background: #333846;
    color: #c2c8d4;
    border: none;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 13px;
    cursor: pointer;
}
.indicator-buttons button.active {
    background: #5369e9;
    color: #fff;
}
.info-bar {
    padding: 14px 22px;
    border-top: 1px solid #2b303d;
    color: #ccc;
    font-size: 15px;
    min-height: 50px;
    line-height: 1.7;
}
.info-tag {
    display: inline-block;
    margin-right: 14px;
}
.color-green { color: #4cd964; }
.color-red { color: #ff5e57; }
.color-yellow { color: #ffcc00; }
.color-purple { color: #a855f7; }

.chart-box {
    width: 100%;
    background: #161923;
    border-bottom: 1px solid #282c38;
}
#chart_kline { height: 340px; }
#chart_volume { height: 120px; }
#chart_kdj { height: 160px; }
"""

# 計算KDJ(9,3,3) 只保留K、D，移除J
def calc_kdj(df):
    df = df.copy()
    high = df['High'].rolling(window=9).max()
    low = df['Low'].rolling(window=9).min()
    df['rsv'] = (df.Close - low) / (high - low) * 100
    df['K'] = df['rsv'].ewm(span=3, adjust=False).mean()
    df['D'] = df['K'].ewm(span=3, adjust=False).mean()
    # 空值填充0
    df[['K','D']] = df[['K','D']].fillna(0)
    return df

# 拉取NVDA行情數據
def get_stock_data(cycle: str):
    ticker = yf.Ticker("NVDA")
    if cycle == "day":
        raw = ticker.history(period="1y", interval="1d")
    elif cycle == "week":
        raw = ticker.history(period="5y", interval="1wk")
    else:
        raw = ticker.history(period="max", interval="1mo")

    raw = raw.reset_index(names="Date")
    raw = calc_kdj(raw)
    raw = calc_ma(raw)
    raw = calc_macd(raw)
    raw['timestamp'] = (raw.Date.astype(np.int64) // 10**9).astype(int)
    raw = raw.iloc[30:].reset_index(drop=True)
    return raw

# 計算移動平均線
def calc_ma(df):
    df = df.copy()
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df[['MA5','MA20']] = df[['MA5','MA20']].fillna(0)
    return df

# 計算MACD(12,26,9)
def calc_macd(df):
    df = df.copy()
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['DIF'] = df['EMA12'] - df['EMA26']
    df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['MACD'] = (df['DIF'] - df['DEA']) * 2
    df[['DIF','DEA','MACD']] = df[['DIF','DEA','MACD']].fillna(0)
    return df

# 打包圖表數據
def pack_chart_data(df):
    total_list = []
    kline_data = []
    volume_data = []
    k_line = []
    d_line = []
    ma5_data = []
    ma20_data = []
    dif_data = []
    dea_data = []
    macd_data = []

    for idx, row in df.iterrows():
        ts = int(row.timestamp)
        o = float(row.Open)
        h = float(row.High)
        l = float(row.Low)
        c = float(row.Close)
        vol = float(row.Volume)
        k = float(row.K)
        d = float(row.D)
        ma5 = float(row.MA5)
        ma20 = float(row.MA20)
        dif = float(row.DIF)
        dea = float(row.DEA)
        macd = float(row.MACD)

        kline_data.append({"time": ts, "open": o, "high": h, "low": l, "close": c})
        vol_color = "#4cd964" if c >= o else "#ff5e57"
        volume_data.append({"time": ts, "value": vol, "color": vol_color})
        k_line.append({"time": ts, "value": k})
        d_line.append({"time": ts, "value": d})
        ma5_data.append({"time": ts, "value": ma5})
        ma20_data.append({"time": ts, "value": ma20})
        dif_data.append({"time": ts, "value": dif})
        dea_data.append({"time": ts, "value": dea})
        macd_data.append({"time": ts, "value": macd, "color": "#4cd964" if macd >= 0 else "#ff5e57"})

        total_list.append({
            "idx": idx,
            "date": row.Date.strftime("%Y-%m-%d"),
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": vol,
            "K": k,
            "D": d,
            "MA5": ma5,
            "MA20": ma20,
            "DIF": dif,
            "DEA": dea,
            "MACD": macd
        })

    return {
        "kline": kline_data,
        "volume": volume_data,
        "K": k_line,
        "D": d_line,
        "MA5": ma5_data,
        "MA20": ma20_data,
        "DIF": dif_data,
        "DEA": dea_data,
        "MACD": macd_data,
        "source": total_list
    }

@rt("/api/data")
def api(cycle: str = "day"):
    df = get_stock_data(cycle)
    print(f"[API] cycle={cycle} rows={len(df)} first={df['Date'].iloc[0]} last={df['Date'].iloc[-1]}")
    res = pack_chart_data(df)
    return res

@rt("/")
def index():
    init_data = pack_chart_data(get_stock_data("day"))
    data_json = json.dumps(init_data, cls=NpEncoder)

    js_script = """
    let mainChart, volChart, kdjChart;
    let candleSeries, volSeries, lineK, lineD, lineMA5, lineMA20;
    let difSeries, deaSeries, macdSeries;
    let currentIndicator = "kd";
    let chartData = DATA_JSON;
    const infoDom = document.getElementById("info_panel");
    let isSyncingCrosshair = false;
    let isSyncingRange = false;

    // 時間 → 數據 查找表
    let volByTime = {}, kByTime = {}, dByTime = {}, dataByTime = {};
    let difByTime = {}, deaByTime = {}, macdByTime = {};

    function buildLookupMaps() {
        volByTime = {}; kByTime = {}; dByTime = {}; dataByTime = {};
        difByTime = {}; deaByTime = {}; macdByTime = {};
        chartData.volume.forEach(d => { volByTime[d.time] = d.value; });
        chartData.K.forEach(d => { kByTime[d.time] = d.value; });
        chartData.D.forEach(d => { dByTime[d.time] = d.value; });
        chartData.DIF.forEach(d => { difByTime[d.time] = d.value; });
        chartData.DEA.forEach(d => { deaByTime[d.time] = d.value; });
        chartData.MACD.forEach(d => { macdByTime[d.time] = d.value; });
        chartData.kline.forEach((d, i) => { dataByTime[d.time] = chartData.source[i]; });
    }
    buildLookupMaps();

    const baseTheme = {
        layout: {
            background: { type: "solid", color: "#161923" },
            textColor: "#c0c8d8"
        },
        grid: {
            vertLines: { color: "#282c38" },
            horzLines: { color: "#282c38" }
        },
        timeScale: {
            timeVisible: true,
            borderColor: "#353b48",
            visible: false,
        },
        rightPriceScale: {
            borderColor: "#353b48",
            visible: true,
            minimumWidth: 70
        },
        crosshair: {
            mode: 1,
            vertLine: { width: 1, color: "#788191", style: 0 },
            horzLine: { width: 1, color: "#788191", style: 0 }
        }
    };

    function numFormat(val) {
        if (typeof val !== "number" || isNaN(val)) return "--";
        return val.toFixed(2);
    }

    function updateInfoPanel(item) {
        const volM = numFormat(item.volume / 1000000);
        const closeColor = item.close >= item.open ? "color-green" : "color-red";
        var indicatorHtml = '';
        if (currentIndicator === "kd") {
            indicatorHtml =
                '<span class="info-tag color-yellow">K:' + numFormat(item.K) + '</span>' +
                '<span class="info-tag color-purple">D:' + numFormat(item.D) + '</span>';
        } else {
            var macdColor = item.MACD >= 0 ? "color-green" : "color-red";
            indicatorHtml =
                '<span class="info-tag" style="color:#2196F3">DIF:' + numFormat(item.DIF) + '</span>' +
                '<span class="info-tag" style="color:#FF9800">DEA:' + numFormat(item.DEA) + '</span>' +
                '<span class="info-tag ' + macdColor + '">MACD:' + numFormat(item.MACD) + '</span>';
        }
        infoDom.innerHTML =
            '<span class="info-tag">日期:' + item.date + '</span>' +
            '<span class="info-tag">開:<span class="color-green">' + numFormat(item.open) + '</span></span>' +
            '<span class="info-tag">高:<span class="color-green">' + numFormat(item.high) + '</span></span>' +
            '<span class="info-tag">低:<span class="color-red">' + numFormat(item.low) + '</span></span>' +
            '<span class="info-tag">收:<span class="' + closeColor + '">' + numFormat(item.close) + '</span></span>' +
            '<span class="info-tag color-green">成交量: ' + volM + 'M</span>' +
            indicatorHtml +
            '<span class="info-tag" style="color:#2196F3">MA5:' + numFormat(item.MA5) + '</span>' +
            '<span class="info-tag" style="color:#FF9800">MA20:' + numFormat(item.MA20) + '</span>';
    }

    // 三圖十字線同步：任一圖滑鼠移動都驅動其他兩圖
    function syncCrosshair(sourceChart, param) {
        if (isSyncingCrosshair) return;
        isSyncingCrosshair = true;

        if (!param || param.time === undefined) {
            [mainChart, volChart, kdjChart].forEach(c => {
                if (c !== sourceChart) c.clearCrosshairPosition();
            });
            isSyncingCrosshair = false;
            return;
        }

        var time = param.time;

        if (sourceChart !== mainChart) {
            var item = dataByTime[time];
            if (item) mainChart.setCrosshairPosition(item.close, time, candleSeries);
        }
        if (sourceChart !== volChart) {
            var vol = volByTime[time];
            if (vol !== undefined) volChart.setCrosshairPosition(vol, time, volSeries);
        }
        if (sourceChart !== kdjChart) {
            var kv = kByTime[time];
            if (kv !== undefined) kdjChart.setCrosshairPosition(kv, time, lineK);
        }

        var item2 = dataByTime[time];
        if (item2) updateInfoPanel(item2);

        isSyncingCrosshair = false;
    }

    // 時間範圍同步（拖拽縮放）
    function syncTimeRange(sourceChart) {
        if (isSyncingRange) return;
        isSyncingRange = true;
        var range = sourceChart.timeScale().getVisibleRange();
        if (range) {
            [mainChart, volChart, kdjChart].forEach(c => {
                if (c !== sourceChart) c.timeScale().setVisibleRange(range);
            });
        }
        isSyncingRange = false;
    }

    function initAllCharts() {
        // K線主圖
        mainChart = LightweightCharts.createChart(document.getElementById("chart_kline"), Object.assign({}, baseTheme));
        candleSeries = mainChart.addCandlestickSeries({
            upColor: "#4cd964", downColor: "#ff5e57",
            borderUpColor: "#4cd964", borderDownColor: "#ff5e57",
            wickUpColor: "#4cd964", wickDownColor: "#ff5e57"
        });
        candleSeries.setData(chartData.kline);

        lineMA5 = mainChart.addLineSeries({ color: "#2196F3", lineWidth: 1 });
        lineMA5.setData(chartData.MA5);
        lineMA20 = mainChart.addLineSeries({ color: "#FF9800", lineWidth: 1 });
        lineMA20.setData(chartData.MA20);

        // 成交量圖 - 使用與K線圖相同的 baseTheme（含 minimumWidth:70 確保對齊）
        volChart = LightweightCharts.createChart(document.getElementById("chart_volume"), Object.assign({}, baseTheme));
        volSeries = volChart.addHistogramSeries({
            priceFormat: { type: "custom", minMove: 1, formatter: function(v) { return (v / 1000000).toFixed(2); } },
            priceScaleId: "right"
        });
        volSeries.setData(chartData.volume);

        // KDJ圖（底部帶時間軸）
        var bottomTheme = Object.assign({}, baseTheme, { timeScale: Object.assign({}, baseTheme.timeScale, { visible: true }) });
        kdjChart = LightweightCharts.createChart(document.getElementById("chart_kdj"), bottomTheme);
        lineK = kdjChart.addLineSeries({ color: "#ffcc00", lineWidth: 2 });
        lineD = kdjChart.addLineSeries({ color: "#a855f7", lineWidth: 2 });
        lineK.setData(chartData.K);
        lineD.setData(chartData.D);

        // MACD系列（預創建，切換時顯示/隱藏）
        difSeries = kdjChart.addLineSeries({ color: "#2196F3", lineWidth: 2, visible: false });
        deaSeries = kdjChart.addLineSeries({ color: "#FF9800", lineWidth: 2, visible: false });
        macdSeries = kdjChart.addHistogramSeries({ visible: false });
        difSeries.setData(chartData.DIF);
        deaSeries.setData(chartData.DEA);
        macdSeries.setData(chartData.MACD);

        // 時間軸縮放同步
        mainChart.timeScale().subscribeVisibleTimeRangeChange(function() { syncTimeRange(mainChart); });
        volChart.timeScale().subscribeVisibleTimeRangeChange(function() { syncTimeRange(volChart); });
        kdjChart.timeScale().subscribeVisibleTimeRangeChange(function() { syncTimeRange(kdjChart); });

        // 三圖十字線同步
        mainChart.subscribeCrosshairMove(function(p) { syncCrosshair(mainChart, p); });
        volChart.subscribeCrosshairMove(function(p) { syncCrosshair(volChart, p); });
        kdjChart.subscribeCrosshairMove(function(p) { syncCrosshair(kdjChart, p); });

        mainChart.timeScale().fitContent();
    }

    async function switchCycle(cycle) {
        try {
            document.querySelectorAll(".period-buttons button").forEach(function(btn) { btn.classList.remove("active"); });
            document.getElementById("btn_" + cycle).classList.add("active");

            var res = await fetch("/api/data?cycle=" + cycle + "&_t=" + Date.now());
            if (!res.ok) throw new Error("HTTP " + res.status);
            var json = await res.json();
            if (typeof json === "string") json = JSON.parse(json);
            chartData = json;

            candleSeries.setData(chartData.kline);
            volSeries.setData(chartData.volume);
            volChart.priceScale("right").applyOptions({ scaleMargins: { top: 0.15, bottom: 0.15 } });
            lineK.setData(chartData.K);
            lineD.setData(chartData.D);
            lineMA5.setData(chartData.MA5);
            lineMA20.setData(chartData.MA20);
            difSeries.setData(chartData.DIF);
            deaSeries.setData(chartData.DEA);
            macdSeries.setData(chartData.MACD);

            buildLookupMaps();
        mainChart.timeScale().fitContent();
        volChart.timeScale().fitContent();
        kdjChart.timeScale().fitContent();
            volChart.timeScale().fitContent();
            kdjChart.timeScale().fitContent();
            infoDom.innerHTML = "滑鼠移至K線區域，查看：開高低收、成交量、K值、D值、MA5、MA20";
        } catch (e) {
            console.error("switchCycle error:", e);
        }
    }
    window.switchCycle = switchCycle;

    function switchIndicator(ind) {
        currentIndicator = ind;
        document.querySelectorAll(".indicator-buttons button").forEach(function(btn) { btn.classList.remove("active"); });
        document.getElementById("btn_" + ind).classList.add("active");

        if (ind === "kd") {
            lineK.applyOptions({ visible: true });
            lineD.applyOptions({ visible: true });
            difSeries.applyOptions({ visible: false });
            deaSeries.applyOptions({ visible: false });
            macdSeries.applyOptions({ visible: false });
        } else {
            lineK.applyOptions({ visible: false });
            lineD.applyOptions({ visible: false });
            difSeries.applyOptions({ visible: true });
            deaSeries.applyOptions({ visible: true });
            macdSeries.applyOptions({ visible: true });
        }
    }
    window.switchIndicator = switchIndicator;

    window.addEventListener("load", function() {
        setTimeout(initAllCharts, 100);
    });
    """
    js_script = js_script.replace("DATA_JSON", data_json)

    page_html = Div(
        Script(src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"),
        Style(CSS_STYLE),
        Div(
            Div(
                Div("NVIDIA NVDA 走勢圖 | K+D成交量", cls="stock-title"),
                Div(
                    Button("日線", id="btn_day", cls="active", onclick="switchCycle('day')"),
                    Button("週線", id="btn_week", onclick="switchCycle('week')"),
                    Button("月線", id="btn_month", onclick="switchCycle('month')"),
                    cls="period-buttons"
                ),
                Div(
                    Button("KDJ", id="btn_kd", cls="active", onclick="switchIndicator('kd')"),
                    Button("MACD", id="btn_macd", onclick="switchIndicator('macd')"),
                    cls="indicator-buttons"
                ),
                cls="top-bar"
            ),
            Div(id="info_panel", cls="info-bar", children="滑鼠移至K線區域，查看：開高低收、成交量、K值、D值"),

            # 排版順序：K線 → 成交量 → KDJ(底部帶唯一時間軸)
            Div(id="chart_kline", cls="chart-box"),
            Div(id="chart_volume", cls="chart-box"),
            Div(id="chart_kdj", cls="chart-box"),

            cls="wrapper"
        ),
        Script(js_script)
    )
    return page_html

if __name__ == "__main__":
    serve(host="127.0.0.1", port=8000, reload=False)