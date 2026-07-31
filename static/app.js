/* yfWatchlist frontend — search, table, charts, settings, alerts */
(function () {
  "use strict";

  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

  let i18n = (window.__WL__ && window.__WL__.i18n) || {};
  let settings = (window.__WL__ && window.__WL__.settings) || {};
  let autoTimer = null;
  let searchTimer = null;
  let detailTicker = null;
  let chartPeriod = "day";
  let mainChart, volChart, kdjChart;
  let candleSeries, volSeries, lineK, lineD, lineMA5, lineMA20;
  let difSeries, deaSeries, macdSeries;
  let currentIndicator = "kd";
  let chartData = {};
  let chartsReady = false;
  let isSyncingCrosshair = false;
  let isSyncingRange = false;
  // Lookup maps for crosshair sync
  let volByTime = {}, kByTime = {}, dByTime = {}, dataByTime = {};
  let difByTime = {}, deaByTime = {}, macdByTime = {};

  function t(key) {
    return i18n[key] || key;
  }

  function toast(msg, type = "info") {
    const n = $("#notif");
    if (!n) return;
    n.textContent = msg;
    n.className = "notif show " + type;
    clearTimeout(n._t);
    n._t = setTimeout(() => {
      n.className = "notif";
    }, 2600);
  }

  async function api(url, opts) {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json", ...(opts && opts.headers) },
      ...opts,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || res.statusText);
    }
    return res.json();
  }

  // ── Theme / appearance ─────────────────────────────────────────
  function applyTheme(theme) {
    const root = $("#app-root");
    if (!root) return;
    root.classList.remove("theme-light", "theme-dark", "theme-system", "theme-frost", "theme-purple", "theme-cyan", "theme-smokeblue", "theme-smoke");
    if (theme === "light") root.classList.add("theme-light");
    else if (theme === "dark") root.classList.add("theme-dark");
    else if (theme === "frost") root.classList.add("theme-frost");
    else if (theme === "purple") root.classList.add("theme-purple");
    else if (theme === "cyan") root.classList.add("theme-cyan");
    else if (theme === "smokeblue") root.classList.add("theme-smokeblue");
    else if (theme === "smoke") root.classList.add("theme-smoke");
    else root.classList.add("theme-system");
  }

  function applyAppearance(s) {
    const r = document.documentElement;
    if (s.font_family) r.style.setProperty("--font-family", s.font_family);
    if (s.font_size) r.style.setProperty("--font-size", s.font_size + "px");
    if (s.zoom != null) {
      r.style.setProperty("--zoom", s.zoom + "%");
      document.body.style.zoom = s.zoom + "%";
    }
    applyTheme(s.theme || "dark");
  }

  // ── Table render ───────────────────────────────────────────────
  function priceClass(dir) {
    if (dir === "up") return "price-up";
    if (dir === "down") return "price-down";
    return "price-flat";
  }

  function renderRows(quotes) {
    const body = $("#wl-body");
    if (!body) return;
    if (!quotes || !quotes.length) {
      body.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--muted)">${t("empty_list")}</td></tr>`;
      return;
    }
    body.innerHTML = quotes
      .map((q) => {
        const pc = priceClass(q.direction);
        const tk = (q.ticker || "").replace(/'/g, "\\'");
        return `<tr data-ticker="${esc(q.ticker)}">
          <td>${esc(q.name || q.ticker)}</td>
          <td>${esc(q.ticker)}</td>
          <td class="${pc}">${esc(q.price_str || "—")}</td>
          <td class="${pc}">${esc(q.change_str || "—")}</td>
          <td class="${pc}">${esc(q.change_pct_str || "—")}</td>
          <td>${esc(q.volume_str || "—")}</td>
          <td class="actions-cell">
            <button class="icon-btn" title="${t("browse")}" onclick="WL.browse('${tk}')">🔍</button>
            <button class="icon-btn" title="${t("move_up")}" onclick="WL.move('${tk}','up')">↑</button>
            <button class="icon-btn" title="${t("move_down")}" onclick="WL.move('${tk}','down')">↓</button>
            <button class="icon-btn danger-icon" title="${t("delete")}" onclick="WL.remove('${tk}')">🗑</button>
          </td>
        </tr>`;
      })
      .join("");
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setLastUpdated(ts) {
    const el = $("#last-updated");
    if (el) el.textContent = ts || t("never");
  }

  async function refreshQuotes() {
    try {
      const data = await api("/api/quotes");
      renderRows(data.quotes);
      setLastUpdated(data.last_updated);
      checkAlerts();
      return data;
    } catch (e) {
      toast(String(e.message || e), "warn");
    }
  }

  // ── Search ─────────────────────────────────────────────────────
  function renderSearch(data) {
    const box = $("#sr");
    if (!box) return;
    const local = data.local || [];
    const yahoo = data.yahoo || [];
    if (!local.length && !yahoo.length) {
      box.innerHTML = `<div class="sr-empty">${t("no_results")}</div>`;
      box.classList.add("show");
      return;
    }
    let html = "";
    if (local.length) {
      html += `<div class="sr-sec-hdr">📁 ${t("local_index")}</div>`;
      html += local.map((r) => searchItem(r)).join("");
    }
    if (yahoo.length) {
      html += `<div class="sr-sec-hdr">🌐 ${t("yahoo_index")}</div>`;
      html += yahoo.map((r) => searchItem(r)).join("");
    }
    box.innerHTML = html;
    box.classList.add("show");
  }

  function searchItem(r) {
    const tk = esc(r.ticker);
    const name = esc(r.name);
    const extra = r.exchange ? ` <span class="sr-exch">${esc(r.exchange)}</span>` : "";
    return `<div class="sr-item">
      <div>
        <div class="sr-item-name">${name}${extra}</div>
        <div class="sr-item-ticker">${tk}</div>
      </div>
      <button class="small accent" onclick="WL.add('${tk.replace(/'/g, "\\'")}','${name.replace(/'/g, "\\'")}')">${t("add")}</button>
    </div>`;
  }

  function onSearchInput(e) {
    const q = e.target.value.trim();
    clearTimeout(searchTimer);
    if (q.length < 2) {
      $("#sr").classList.remove("show");
      $("#sr").innerHTML = "";
      return;
    }
    searchTimer = setTimeout(async () => {
      try {
        const data = await api("/api/search?q=" + encodeURIComponent(q));
        renderSearch(data);
      } catch (err) {
        console.error(err);
      }
    }, 180);
  }

  async function addSymbol(ticker, name) {
    try {
      const data = await api("/api/add", {
        method: "POST",
        body: JSON.stringify({ ticker, name }),
      });
      if (data.ok) {
        toast(data.i18n_msg || t("add_success"), "success");
        await refreshQuotes();
      } else {
        toast(data.i18n_msg || t("already_in"), "warn");
      }
    } catch (e) {
      toast(String(e.message || e), "warn");
    }
    // Return focus to search for continuous adding
    const inp = $("#search-input");
    if (inp) {
      inp.focus();
      inp.select();
    }
    // keep results visible for multi-add
  }

  async function removeSymbol(ticker) {
    if (!confirm(t("confirm_delete"))) return;
    try {
      await api("/api/remove", {
        method: "POST",
        body: JSON.stringify({ ticker }),
      });
      await refreshQuotes();
    } catch (e) {
      toast(String(e.message || e), "warn");
    }
  }

  async function moveSymbol(ticker, direction) {
    try {
      await api("/api/move", {
        method: "POST",
        body: JSON.stringify({ ticker, direction }),
      });
      await refreshQuotes();
    } catch (e) {
      toast(String(e.message || e), "warn");
    }
  }

  // ── Detail browse ──────────────────────────────────────────────
  function openModal(id) {
    const m = $(id);
    if (m) m.classList.add("active");
  }
  function closeModal(id) {
    const m = $(id);
    if (m) m.classList.remove("active");
  }

  function switchTab(tab) {
    $$("#detail-tabs .tab-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.tab === tab);
    });
    ["info", "chart", "news"].forEach((name) => {
      const pane = $("#tab-pane-" + name);
      if (pane) pane.classList.toggle("active", name === tab);
    });
    if (tab === "chart" && detailTicker) {
      // longer delay so modal transition finishes and containers have dimensions
      setTimeout(() => loadChart(detailTicker, chartPeriod), 150);
    }
  }

  async function browse(ticker) {
    detailTicker = ticker;
    chartPeriod = "day";
    currentIndicator = "kd";
    _chartLoadRetries = 0;
    $("#detail-title").textContent = ticker;
    openModal("#detail-modal");
    switchTab("info");
    $$(".chart-toolbar button[data-period]").forEach((b) => {
      b.classList.toggle("active", b.dataset.period === "day");
    });
    $$(".chart-toolbar button[data-indicator]").forEach((b) => {
      b.classList.toggle("active", b.dataset.indicator === "kd");
    });
    $("#tab-pane-info").innerHTML = `<div class="loading">${t("loading")}</div>`;
    $("#tab-pane-news").innerHTML = `<div class="loading">${t("loading")}</div>`;

    // fundamentals
    try {
      const data = await api("/api/fundamentals?ticker=" + encodeURIComponent(ticker));
      renderFundamentals(data);
      if (data.quote && data.quote.name) {
        $("#detail-title").textContent = `${data.quote.name} (${ticker})`;
      }
    } catch (e) {
      $("#tab-pane-info").innerHTML = `<div class="loading">${esc(e.message)}</div>`;
    }

    // news preload
    loadNews(ticker);
  }

  function renderFundamentals(data) {
    const pane = $("#tab-pane-info");
    if (!data || !data.ok) {
      pane.innerHTML = `<div class="loading">${t("no_data")}${data && data.error ? " — " + esc(data.error) : ""}</div>`;
      return;
    }
    let html = "";
    (data.sections || []).forEach((sec) => {
      html += `<h3>${t(sec.key)}</h3><div class="info-cards">`;
      (sec.items || []).forEach((it) => {
        html += `<div class="info-card"><div class="ic-lbl">${t(it.key)}</div><div class="ic-val">${esc(it.value)}</div></div>`;
      });
      html += `</div>`;
    });
    pane.innerHTML = html || `<div class="loading">${t("no_data")}</div>`;
  }

  async function loadNews(ticker) {
    const pane = $("#tab-pane-news");
    try {
      const data = await api("/api/news?ticker=" + encodeURIComponent(ticker));
      const news = data.news || [];
      if (!news.length) {
        pane.innerHTML = `<div class="loading">${t("no_news")}</div>`;
        return;
      }
      pane.innerHTML =
        `<ul class="news-list">` +
        news
          .map((n) => {
            const url = n.url && n.url !== "無連結" ? n.url : "#";
            const ext = url.startsWith("http") ? `target="_blank" rel="noopener noreferrer"` : "";
            return `<li class="news-item">
              <a href="${esc(url)}" ${ext}>${esc(n.title || "")}</a>
              <div class="news-meta">${t("publisher")}: ${esc(n.publisher || "—")} · ${t("pub_date")}: ${esc(n.publish_time || "—")}</div>
            </li>`;
          })
          .join("") +
        `</ul>`;
    } catch (e) {
      pane.innerHTML = `<div class="loading">${esc(e.message)}</div>`;
    }
  }

  // ── Lightweight Charts ─────────────────────────────────────────
  function chartTheme() {
    const isLight = $("#app-root")?.classList.contains("theme-light");
    if (isLight) {
      return {
        layout: { background: { type: "solid", color: "#ffffff" }, textColor: "#2d3436" },
        grid: { vertLines: { color: "#eef0f3" }, horzLines: { color: "#eef0f3" } },
      };
    }
    // Dark theme matching tradingView.py colors
    return {
      layout: { background: { type: "solid", color: "#161923" }, textColor: "#c0c8d8" },
      grid: { vertLines: { color: "#282c38" }, horzLines: { color: "#282c38" } },
    };
  }

  function destroyCharts() {
    [mainChart, volChart, kdjChart].forEach((c) => {
      try {
        c && c.remove();
      } catch (_) {}
    });
    mainChart = volChart = kdjChart = null;
    candleSeries = volSeries = lineK = lineD = lineMA5 = lineMA20 = null;
    difSeries = deaSeries = macdSeries = null;
    chartsReady = false;
    chartData = {};
  }

  function buildLookupMaps() {
    volByTime = {}; kByTime = {}; dByTime = {}; dataByTime = {};
    difByTime = {}; deaByTime = {}; macdByTime = {};
    (chartData.volume || []).forEach(d => { volByTime[d.time] = d.value; });
    (chartData.K || []).forEach(d => { kByTime[d.time] = d.value; });
    (chartData.D || []).forEach(d => { dByTime[d.time] = d.value; });
    (chartData.DIF || []).forEach(d => { difByTime[d.time] = d.value; });
    (chartData.DEA || []).forEach(d => { deaByTime[d.time] = d.value; });
    (chartData.MACD || []).forEach(d => { macdByTime[d.time] = d.value; });
    (chartData.kline || []).forEach((d, i) => { dataByTime[d.time] = (chartData.source || [])[i]; });
  }

  function numFormat(val) {
    if (typeof val !== "number" || isNaN(val)) return "--";
    return val.toFixed(2);
  }

  function updateInfoPanel(item) {
    const infoBar = $("#chart-info-bar");
    if (!infoBar || !item) return;
    const volM = numFormat(item.volume / 1000000);
    const closeColor = item.close >= item.open ? "color-green" : "color-red";
    let indicatorHtml = "";
    if (currentIndicator === "kd") {
      indicatorHtml =
        '<span class="info-tag color-yellow">K: ' + numFormat(item.K) + '</span>' +
        '<span class="info-tag color-purple">D: ' + numFormat(item.D) + '</span>';
    } else {
      const macdColor = item.MACD >= 0 ? "color-green" : "color-red";
      indicatorHtml =
        '<span class="info-tag" style="color:#2196F3">DIF: ' + numFormat(item.DIF) + '</span>' +
        '<span class="info-tag" style="color:#FF9800">DEA: ' + numFormat(item.DEA) + '</span>' +
        '<span class="info-tag ' + macdColor + '">MACD: ' + numFormat(item.MACD) + '</span>';
    }
    infoBar.innerHTML =
      '<span class="info-tag">' + item.date + '</span>' +
      '<span class="info-tag">O: <span class="color-green">' + numFormat(item.open) + '</span></span>' +
      '<span class="info-tag">H: <span class="color-green">' + numFormat(item.high) + '</span></span>' +
      '<span class="info-tag">L: <span class="color-red">' + numFormat(item.low) + '</span></span>' +
      '<span class="info-tag">C: <span class="' + closeColor + '">' + numFormat(item.close) + '</span></span>' +
      '<span class="info-tag color-green">Vol: ' + volM + 'M</span>' +
      indicatorHtml +
      '<span class="info-tag" style="color:#2196F3">MA5: ' + numFormat(item.MA5) + '</span>' +
      '<span class="info-tag" style="color:#FF9800">MA20: ' + numFormat(item.MA20) + '</span>';
  }

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

    const time = param.time;

    if (sourceChart !== mainChart) {
      const item = dataByTime[time];
      if (item) mainChart.setCrosshairPosition(item.close, time, candleSeries);
    }
    if (sourceChart !== volChart) {
      const vol = volByTime[time];
      if (vol !== undefined) volChart.setCrosshairPosition(vol, time, volSeries);
    }
    if (sourceChart !== kdjChart) {
      const kv = kByTime[time];
      if (kv !== undefined) kdjChart.setCrosshairPosition(kv, time, lineK);
    }

    const item2 = dataByTime[time];
    if (item2) updateInfoPanel(item2);

    isSyncingCrosshair = false;
  }

  function syncTimeRange(sourceChart) {
    if (isSyncingRange) return;
    isSyncingRange = true;
    const range = sourceChart.timeScale().getVisibleRange();
    if (range) {
      [mainChart, volChart, kdjChart].forEach(c => {
        if (c !== sourceChart) c.timeScale().setVisibleRange(range);
      });
    }
    isSyncingRange = false;
  }

  function initCharts() {
    if (typeof LightweightCharts === "undefined") {
      console.error("LightweightCharts not loaded");
      return;
    }
    // Check containers have dimensions before creating charts
    const klineEl = $("#chart_kline");
    const volEl = $("#chart_volume");
    const kdjEl = $("#chart_kdj");
    if (!klineEl || !volEl || !kdjEl) return;
    if (klineEl.clientWidth === 0 || klineEl.clientHeight === 0) return;
    destroyCharts();
    const th = chartTheme();
    const baseTheme = {
      layout: {
        background: th.layout.background,
        textColor: th.layout.textColor,
      },
      grid: {
        vertLines: th.grid.vertLines,
        horzLines: th.grid.horzLines,
      },
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: "#353b48", visible: false },
      rightPriceScale: { borderColor: "#353b48", visible: true, minimumWidth: 70 },
      crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: { width: 1, color: "#788191", style: 0 },
        horzLine: { width: 1, color: "#788191", style: 0 },
      },
      autoSize: true,
    };

    // K-line main chart
    mainChart = LightweightCharts.createChart($("#chart_kline"), Object.assign({}, baseTheme));
    candleSeries = mainChart.addCandlestickSeries({
      upColor: "#4cd964", downColor: "#ff5e57",
      borderUpColor: "#4cd964", borderDownColor: "#ff5e57",
      wickUpColor: "#4cd964", wickDownColor: "#ff5e57",
    });
    lineMA5 = mainChart.addLineSeries({ color: "#2196F3", lineWidth: 1 });
    lineMA20 = mainChart.addLineSeries({ color: "#FF9800", lineWidth: 1 });

    // Volume chart
    volChart = LightweightCharts.createChart($("#chart_volume"), Object.assign({}, baseTheme));
    volSeries = volChart.addHistogramSeries({
      priceFormat: { type: "custom", minMove: 1, formatter: function(v) { return (v / 1000000).toFixed(2); } },
      priceScaleId: "right",
    });

    // Indicator chart (KDJ or MACD)
    const bottomTheme = Object.assign({}, baseTheme, { timeScale: Object.assign({}, baseTheme.timeScale, { visible: true }) });
    kdjChart = LightweightCharts.createChart($("#chart_kdj"), bottomTheme);
    lineK = kdjChart.addLineSeries({ color: "#ffd600", lineWidth: 2 });
    lineD = kdjChart.addLineSeries({ color: "#a855f7", lineWidth: 2 });
    difSeries = kdjChart.addLineSeries({ color: "#2196F3", lineWidth: 2, visible: false });
    deaSeries = kdjChart.addLineSeries({ color: "#FF9800", lineWidth: 2, visible: false });
    macdSeries = kdjChart.addHistogramSeries({ visible: false });

    // Time range sync
    mainChart.timeScale().subscribeVisibleTimeRangeChange(function() { syncTimeRange(mainChart); });
    volChart.timeScale().subscribeVisibleTimeRangeChange(function() { syncTimeRange(volChart); });
    kdjChart.timeScale().subscribeVisibleTimeRangeChange(function() { syncTimeRange(kdjChart); });

    // Crosshair sync
    mainChart.subscribeCrosshairMove(function(p) { syncCrosshair(mainChart, p); });
    volChart.subscribeCrosshairMove(function(p) { syncCrosshair(volChart, p); });
    kdjChart.subscribeCrosshairMove(function(p) { syncCrosshair(kdjChart, p); });

    chartsReady = true;
  }

  function renderChartData(data) {
    if (!chartsReady) initCharts();
    if (!candleSeries || !volSeries || !lineK || !lineD) return;
    chartData = data;
    // Wrap each setData in try-catch to prevent one failure from blocking others
    try { candleSeries.setData(data.kline || []); } catch (e) { console.warn("candleSeries.setData failed:", e); }
    try { volSeries.setData(data.volume || []); } catch (_) {}
    try { volChart.priceScale("right").applyOptions({ scaleMargins: { top: 0.15, bottom: 0.15 } }); } catch (_) {}
    try { lineK.setData(data.K || []); } catch (_) {}
    try { lineD.setData(data.D || []); } catch (_) {}
    try { lineMA5.setData(data.MA5 || []); } catch (_) {}
    try { lineMA20.setData(data.MA20 || []); } catch (_) {}
    try { difSeries.setData(data.DIF || []); } catch (_) {}
    try { deaSeries.setData(data.DEA || []); } catch (_) {}
    try { macdSeries.setData(data.MACD || []); } catch (_) {}
    buildLookupMaps();
    try { mainChart.timeScale().fitContent(); } catch (_) {}
    try { volChart.timeScale().fitContent(); } catch (_) {}
    try { kdjChart.timeScale().fitContent(); } catch (_) {}
    const infoBar = $("#chart-info-bar");
    if (infoBar) infoBar.innerHTML = "滑鼠移至K線區域查看：開高低收、成交量、K/D 或 DIF/DEA/MACD、MA5、MA20";
  }

  function switchIndicator(ind) {
    currentIndicator = ind;
    $$(".chart-toolbar button[data-indicator]").forEach((b) => {
      b.classList.toggle("active", b.dataset.indicator === ind);
    });
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

  let _chartLoadRetries = 0;

  async function loadChart(ticker, period) {
    chartPeriod = period || "day";
    // Retry initCharts if containers weren't ready yet
    if (!chartsReady) {
      initCharts();
      if (!chartsReady) {
        _chartLoadRetries++;
        if (_chartLoadRetries < 5) {
          setTimeout(() => loadChart(ticker, period), 200);
        }
        return;
      }
    }
    _chartLoadRetries = 0;
    try {
      const data = await api(
        `/api/chart?ticker=${encodeURIComponent(ticker)}&period=${encodeURIComponent(chartPeriod)}&_t=${Date.now()}`
      );
      if (typeof data === "string") data = JSON.parse(data);
      if (data.error) toast(data.error, "warn");
      renderChartData(data);
    } catch (e) {
      toast(String(e.message || e), "warn");
    }
  }

  // ── Settings & fonts ───────────────────────────────────────────
  function isVerticalFont(name) {
    if (!name) return true;
    const n = name.trim();
    if (n.startsWith("@")) return true;
    const lower = n.toLowerCase();
    if (lower.includes("vertical") || lower.includes("vert")) return true;
    // CJK vertical variants often prefixed
    if (/^@/.test(n)) return true;
    return false;
  }

  const FALLBACK_FONTS = [
    "Microsoft JhengHei",
    "Microsoft YaHei",
    "PingFang TC",
    "PingFang SC",
    "Noto Sans TC",
    "Noto Sans SC",
    "Source Han Sans TC",
    "Segoe UI",
    "Arial",
    "Helvetica Neue",
    "Tahoma",
    "Verdana",
    "Georgia",
    "Times New Roman",
    "Consolas",
    "Courier New",
    "system-ui",
    "sans-serif",
    "serif",
    "monospace",
  ];

  async function detectFonts() {
    const set = new Set();
    // Local Font Access API
    try {
      if (window.queryLocalFonts) {
        const fonts = await window.queryLocalFonts();
        fonts.forEach((f) => {
          const family = f.family || f.fullName;
          if (family && !isVerticalFont(family)) set.add(family);
        });
      }
    } catch (e) {
      console.info("queryLocalFonts unavailable", e);
    }
    // document.fonts check for common list
    FALLBACK_FONTS.forEach((f) => set.add(f));
    try {
      if (document.fonts && document.fonts.check) {
        // keep all fallback; browser will use available ones
      }
    } catch (_) {}
    return [...set].sort((a, b) => a.localeCompare(b));
  }

  async function populateFontSelect() {
    const sel = $("#set-font");
    if (!sel) return;
    const fonts = await detectFonts();
    const current = (settings.font_family || "").split(",")[0].trim().replace(/["']/g, "");
    sel.innerHTML = fonts
      .map((f) => {
        const selected = f === current || (settings.font_family || "").includes(f) ? "selected" : "";
        return `<option value="${esc(f)}" ${selected} style="font-family:'${esc(f)}'">${esc(f)}</option>`;
      })
      .join("");
    if (current && ![...sel.options].some((o) => o.value === current)) {
      const opt = document.createElement("option");
      opt.value = current;
      opt.textContent = current;
      opt.selected = true;
      sel.insertBefore(opt, sel.firstChild);
    }
  }

  async function saveSettings() {
    const payload = {
      lang: $("#set-lang").value,
      theme: $("#set-theme").value,
      font_family: $("#set-font").value + ", system-ui, sans-serif",
      font_size: parseInt($("#set-fsize").value, 10) || 14,
      zoom: parseFloat($("#set-zoom").value) || 100,
      auto_refresh: parseInt($("#set-auto").value, 10) || 0,
    };
    try {
      const data = await api("/api/settings", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      settings = data.settings || payload;
      i18n = settings.i18n || i18n;
      applyAppearance(settings);
      setupAutoRefresh(settings.auto_refresh);
      // sync toolbar auto-refresh select
      const ar = $("#auto-refresh");
      if (ar) ar.value = String(settings.auto_refresh || 0);
      toast(t("settings_saved"), "success");
      closeModal("#settings-modal");
      // language change needs full reload for server-rendered labels
      if (payload.lang !== (window.__WL__.settings || {}).lang) {
        location.reload();
      }
    } catch (e) {
      toast(String(e.message || e), "warn");
    }
  }

  // ── Alerts ─────────────────────────────────────────────────────
  async function loadAlertsUI() {
    const list = $("#alerts-list");
    try {
      const data = await api("/api/alerts");
      const alerts = data.alerts || [];
      if (!alerts.length) {
        list.innerHTML = `<div class="loading">${t("no_data")}</div>`;
        return;
      }
      list.innerHTML = alerts
        .map((a, i) => {
          const cond =
            a.condition === "above" || a.condition === "高於" || a.condition === "高于"
              ? t("alert_above")
              : t("alert_below");
          const status = a.triggered
            ? `<span class="badge warn">${t("alert_triggered")}</span>`
            : `<span class="badge ok">${t("alert_active")}</span>`;
          return `<div class="alert-item">
            <div><strong>${esc(a.ticker)}</strong> ${cond} ${esc(a.target_price)} ${status}</div>
            <button class="small danger" onclick="WL.delAlert(${i})">${t("alert_remove")}</button>
          </div>`;
        })
        .join("");
    } catch (e) {
      list.innerHTML = `<div class="loading">${esc(e.message)}</div>`;
    }
  }

  async function addAlert() {
    const ticker = ($("#alert-ticker").value || "").trim();
    const condition = $("#alert-cond").value;
    const target_price = parseFloat($("#alert-price").value);
    if (!ticker || isNaN(target_price)) {
      toast("Ticker / price required", "warn");
      return;
    }
    try {
      await api("/api/alerts", {
        method: "POST",
        body: JSON.stringify({ ticker, condition, target_price }),
      });
      $("#alert-ticker").value = "";
      $("#alert-price").value = "";
      loadAlertsUI();
      toast(t("settings_saved"), "success");
    } catch (e) {
      toast(String(e.message || e), "warn");
    }
  }

  async function delAlert(index) {
    try {
      await api("/api/alerts/delete", {
        method: "POST",
        body: JSON.stringify({ index }),
      });
      loadAlertsUI();
    } catch (e) {
      toast(String(e.message || e), "warn");
    }
  }

  async function checkAlerts() {
    try {
      const data = await api("/api/alerts/check", { method: "POST", body: "{}" });
      (data.triggered || []).forEach((a) => {
        const cond = a.condition === "above" ? "≥" : "≤";
        toast(
          `🔔 ${a.ticker} ${cond} ${a.target_price} (now ${a.triggered_price})`,
          "warn"
        );
      });
    } catch (_) {}
  }

  // ── Auto refresh ───────────────────────────────────────────────
  function setupAutoRefresh(minutes) {
    if (autoTimer) {
      clearInterval(autoTimer);
      autoTimer = null;
    }
    const m = parseInt(minutes, 10) || 0;
    if (m > 0) {
      autoTimer = setInterval(refreshQuotes, m * 60 * 1000);
    }
  }

  async function setAutoFromToolbar() {
    const v = parseInt($("#auto-refresh").value, 10) || 0;
    try {
      const data = await api("/api/settings", {
        method: "POST",
        body: JSON.stringify({ auto_refresh: v }),
      });
      settings = data.settings || settings;
      setupAutoRefresh(v);
      const sa = $("#set-auto");
      if (sa) sa.value = String(v);
    } catch (e) {
      toast(String(e.message || e), "warn");
    }
  }

  async function switchWatchlist() {
    const name = $("#wl-select").value;
    try {
      const data = await api("/api/watchlist/switch", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      if (data.ok) {
        renderRows(data.quotes);
        setLastUpdated(data.last_updated);
        toast(t("update_success"), "success");
      }
    } catch (e) {
      toast(String(e.message || e), "warn");
    }
  }

  async function addWatchlist() {
    const raw = prompt(t("wl_new_prompt"));
    if (raw == null) return;             // user cancelled
    const name = String(raw).trim();
    if (!name) { toast(t("wl_empty_name"), "warn"); return; }
    try {
      const data = await api("/api/watchlist/add", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      if (data.ok) {
        // Rebuild <select> options + switch to the new watchlist.
        const sel = $("#wl-select");
        sel.innerHTML = (data.watchlist_names || [data.active_wl]).map(
          (n) => `<option value="${esc(n)}" ${n === data.active_wl ? "selected" : ""}>${esc(n)}</option>`
        ).join("");
        renderRows(data.quotes || []);
        setLastUpdated(data.last_updated);
        toast(t(data.i18n_msg || "wl_created"), "success");
      } else {
        toast(t(data.error || data.i18n_msg || "wl_error"), "warn");
      }
    } catch (e) {
      toast(String(e.message || e), "warn");
    }
  }

  async function deleteWatchlist() {
    const sel = $("#wl-select");
    const name = sel && sel.value;
    if (!name) { toast(t("wl_empty_name"), "warn"); return; }

    // ── 第一層警告：說明影響範圍、列出會被刪的商品數 ──────────────
    const itemCount = $$("#tbl-wl tbody tr").length;
    const firstWarn = confirm(
      t("wl_del_warn1").replace("{name}", name).replace("{count}", String(itemCount))
    );
    if (!firstWarn) return;        // 使用者按「取消」→ 直接退出

    // ── 第二層確認：強制輸入清單名稱以確認意圖 ───────────────────
    const typed = prompt(
      t("wl_del_warn2").replace("{name}", name)
    );
    if (typed == null) return;     // 取消
    if (String(typed).trim() !== name) {
      toast(t("wl_del_mismatch"), "warn");
      return;
    }

    try {
      const data = await api("/api/watchlist/delete", {
        method: "POST",
        body: JSON.stringify({ name }),
      });
      if (data.ok) {
        // 重建 <select>、切換至後端選定的清單、重新繪製表格
        sel.innerHTML = (data.watchlist_names || [data.active_wl]).map(
          (n) => `<option value="${esc(n)}" ${n === data.active_wl ? "selected" : ""}>${esc(n)}</option>`
        ).join("");
        renderRows(data.quotes || []);
        setLastUpdated(data.last_updated);
        toast(t("wl_deleted_with_count").replace("{count}", String(data.destroyed || 0)), "success");
      } else {
        toast(t(data.i18n_msg || data.error || "wl_error"), "warn");
      }
    } catch (e) {
      toast(String(e.message || e), "warn");
    }
  }

  // ── Force save on unload ───────────────────────────────────────
  function forceSave() {
    try {
      navigator.sendBeacon && navigator.sendBeacon("/api/save", "{}");
      // fallback
      fetch("/api/save", { method: "POST", body: "{}", keepalive: true });
    } catch (_) {}
  }

  // ── Wire events ────────────────────────────────────────────────
  function init() {
    applyAppearance(settings);
    setupAutoRefresh(settings.auto_refresh || 0);

    const search = $("#search-input");
    if (search) {
      search.addEventListener("input", onSearchInput);
      search.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
          $("#sr").classList.remove("show");
        }
      });
    }
    document.addEventListener("click", (e) => {
      const box = $(".search-box");
      if (box && !box.contains(e.target)) {
        $("#sr")?.classList.remove("show");
      }
    });

    $("#btn-refresh-page")?.addEventListener("click", async () => {
      await refreshQuotes();
      toast(t("update_success"), "success");
    });
    $("#btn-refresh-all")?.addEventListener("click", async () => {
      await refreshQuotes();
      toast(t("update_success"), "success");
    });
    $("#auto-refresh")?.addEventListener("change", setAutoFromToolbar);
    $("#wl-select")?.addEventListener("change", switchWatchlist);
    $("#btn-add-wl")?.addEventListener("click", addWatchlist);
    $("#btn-del-wl")?.addEventListener("click", deleteWatchlist);

    $("#btn-settings")?.addEventListener("click", async () => {
      openModal("#settings-modal");
      await populateFontSelect();
    });
    $("#btn-close-settings")?.addEventListener("click", () => closeModal("#settings-modal"));
    $("#btn-save-settings")?.addEventListener("click", saveSettings);

    $("#btn-alerts")?.addEventListener("click", () => {
      openModal("#alerts-modal");
      loadAlertsUI();
    });
    $("#btn-close-alerts")?.addEventListener("click", () => closeModal("#alerts-modal"));
    $("#btn-add-alert")?.addEventListener("click", addAlert);

    $("#btn-close-detail")?.addEventListener("click", () => {
      closeModal("#detail-modal");
      destroyCharts();
      detailTicker = null;
    });

    $$("#detail-tabs .tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });
    $$(".chart-toolbar button[data-period]").forEach((btn) => {
      btn.addEventListener("click", () => {
        $$(".chart-toolbar button[data-period]").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        if (detailTicker) loadChart(detailTicker, btn.dataset.period);
      });
    });
    $$(".chart-toolbar button[data-indicator]").forEach((btn) => {
      btn.addEventListener("click", () => {
        switchIndicator(btn.dataset.indicator);
      });
    });

    // close modals on overlay click
    ["#detail-modal", "#settings-modal", "#alerts-modal"].forEach((id) => {
      $(id)?.addEventListener("click", (e) => {
        if (e.target === $(id)) {
          closeModal(id);
          if (id === "#detail-modal") destroyCharts();
        }
      });
    });

    window.addEventListener("beforeunload", forceSave);
    // initial alert check
    setTimeout(checkAlerts, 2000);
  }

  // Public API for inline handlers
  window.WL = {
    browse,
    remove: removeSymbol,
    move: moveSymbol,
    add: addSymbol,
    newWatchlist: addWatchlist,
    delWatchlist: deleteWatchlist,
    delAlert,
    refresh: refreshQuotes,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
