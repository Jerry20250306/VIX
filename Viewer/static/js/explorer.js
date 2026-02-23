/**
 * explorer.js — 自由探勘模式前端邏輯
 * 負責：頁籤切換、下拉選單動態載入、搜尋/河流查詢、算式還原、差異跳轉
 */

// ===================================================================
// 狀態管理
// ===================================================================
const ExploreState = {
    date: null,
    term: "Near",
    strike: null,
    cp: "Call",
    timeInt: null,         // 目前顯示的 time_int (HMMSS 整數)
    sysidMap: {},          // {time_int_str: sysid}
    currentRange: [0, 0],  // 目前已載入的 [min_sysid, max_sysid]
    ticks: [],             // 所有已載入的 tick（含標記）
    snapshots: [],         // 所有分界線
    activeSnapSysid: null, // 目前選取（高亮）的 snapshot sysid
    allTimes: [],          // 該 date+term 所有可用的 time_int 清單（供 ±15s 用）
};

// 錯誤代碼對應中文說明字典
const ERROR_LABELS = {
    "E1": "報價為零",
    "E2": "價差過大",
    "E3": "離群值(Outlier)",
};

// ===================================================================
// 頁籤切換
// ===================================================================
function switchTab(mode) {
    const isDiff = mode === "diff";
    const isExplore = mode === "explore";
    const isSigma = mode === "sigma";

    document.getElementById("mode-diff").style.display = isDiff ? "" : "none";
    document.getElementById("mode-explore").style.display = isExplore ? "" : "none";
    if (document.getElementById("mode-sigma")) {
        document.getElementById("mode-sigma").style.display = isSigma ? "" : "none";
    }

    document.getElementById("tab-diff").classList.toggle("active", isDiff);
    document.getElementById("tab-explore").classList.toggle("active", isExplore);
    if (document.getElementById("tab-sigma")) {
        document.getElementById("tab-sigma").classList.toggle("active", isSigma);
    }

    // 重設狀態或自動觸發查詢
    const dateSelect = document.getElementById("date-selector");
    const currentDate = dateSelect ? dateSelect.value : null;

    if (isExplore) {
        ExploreState.date = currentDate;
        if (currentDate) exploreLoadOptions();
    } else if (isSigma) {
        if (currentDate) loadSigmaDiff();
    }
}

// ===================================================================
// 動態載入履約價 & 時間下拉選單
// ===================================================================
async function exploreLoadOptions() {
    const dateSelect = document.getElementById("date-selector");
    ExploreState.date = dateSelect ? dateSelect.value : null;
    ExploreState.term = document.getElementById("ex-term").value;

    const strikeSelect = document.getElementById("ex-strike");
    const timeSelect = document.getElementById("ex-time");

    if (!ExploreState.date) {
        strikeSelect.innerHTML = '<option value="">-- 請先選擇日期 --</option>';
        timeSelect.innerHTML = '<option value="">-- 請先選擇日期 --</option>';
        return;
    }

    strikeSelect.innerHTML = '<option value="">載入中...</option>';
    timeSelect.innerHTML = '<option value="">載入中...</option>';

    try {
        const res = await fetch(`/api/explore/options?date=${ExploreState.date}&term=${ExploreState.term}`);
        const data = await res.json();

        if (data.error) throw new Error(data.error);

        // 填入履約價
        strikeSelect.innerHTML = data.strikes.map(s =>
            `<option value="${s}">${s}</option>`
        ).join("");

        // 填入時間（格式化為 HH:MM:SS 顯示，但 value 存原始整數）
        timeSelect.innerHTML = data.times.map(t =>
            `<option value="${t}">${formatTimeInt(t)}</option>`
        ).join("");

        // 記錄所有時間點，供 ±15s 使用
        ExploreState.allTimes = data.times;

        // 若時間列表中存在 09:00:00 (數值為 90000)，則預設選擇它
        if (data.times.includes(90000)) {
            timeSelect.value = 90000;
        } else if (data.times.includes("90000")) {
            timeSelect.value = "90000";
        }

    } catch (err) {
        strikeSelect.innerHTML = `<option value="">載入失敗</option>`;
        timeSelect.innerHTML = `<option value="">載入失敗</option>`;
        console.error("exploreLoadOptions error:", err);
    }
}

// ===================================================================
// 搜尋主流程
// ===================================================================
async function exploreSearch() {
    const dateSelect = document.getElementById("date-selector");
    ExploreState.date = dateSelect ? dateSelect.value : null;
    ExploreState.term = document.getElementById("ex-term").value;
    ExploreState.strike = document.getElementById("ex-strike").value;
    ExploreState.cp = document.getElementById("ex-cp").value;
    ExploreState.timeInt = parseInt(document.getElementById("ex-time").value, 10) || null;

    if (!ExploreState.date || !ExploreState.strike || !ExploreState.timeInt) {
        alert("請先選擇日期、履約價與時間！");
        return;
    }

    showExploreLoading(true);

    try {
        // 1. 取得 SysID Map（若已載入過可重用）
        if (Object.keys(ExploreState.sysidMap).length === 0) {
            const mapRes = await fetch(`/api/explore/sysid_map?date=${ExploreState.date}&term=${ExploreState.term}`);
            const mapData = await mapRes.json();
            if (mapData.error) throw new Error(mapData.error);
            ExploreState.sysidMap = mapData.sysid_map || {};
        }

        // 2. 取得河流 Tick 資料（全新搜尋）
        await _fetchStream();

        // 3. 更新標籤
        updateCurrentLabel();

        // 4. 自動捲動至目標時間分界線，同時觸發算式還原
        _scrollToTargetTime(ExploreState.timeInt);

    } catch (err) {
        showExploreError("搜尋失敗：" + err.message);
    } finally {
        showExploreLoading(false);
    }
}

// ===================================================================
// 核心：取得河流資料並重繪
// ===================================================================
async function _fetchStream({ prependSysid, appendSysid } = {}) {
    let url = `/api/explore/ticks_stream`
        + `?date=${ExploreState.date}`
        + `&term=${ExploreState.term}`
        + `&strike=${ExploreState.strike}`
        + `&cp=${ExploreState.cp}`
        + `&time_int=${ExploreState.timeInt}`;

    if (prependSysid != null) url += `&prepend_sysid=${prependSysid}`;
    if (appendSysid != null) url += `&append_sysid=${appendSysid}`;

    const res = await fetch(url);
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    // 合併：擴充模式，把新 tick 合入（依 seqno 去重）
    if (prependSysid != null || appendSysid != null) {
        const existingSeqnos = new Set(ExploreState.ticks.map(t => t.seqno));
        const newTicks = (data.ticks || []).filter(t => !existingSeqnos.has(t.seqno));
        ExploreState.ticks = [...ExploreState.ticks, ...newTicks]
            .sort((a, b) => a.seqno - b.seqno);

        const existingSnapSysids = new Set(ExploreState.snapshots.map(s => s.sysid));
        const newSnaps = (data.snapshots || []).filter(s => !existingSnapSysids.has(s.sysid));
        ExploreState.snapshots = [...ExploreState.snapshots, ...newSnaps]
            .sort((a, b) => a.sysid - b.sysid);

        ExploreState.currentRange = [
            Math.min(ExploreState.currentRange[0], data.range[0]),
            Math.max(ExploreState.currentRange[1], data.range[1]),
        ];
    } else {
        // 全新搜尋
        ExploreState.ticks = data.ticks || [];
        ExploreState.snapshots = data.snapshots || [];
        ExploreState.currentRange = data.range || [0, 0];
        ExploreState.activeSnapSysid = null;
        ExploreState.sysidMap = {};  // 下次要搜不同 term 時清掉快取
    }

    renderTickStream();
    showLoadMoreButtons(true);
}

// ===================================================================
// 自動捲動至目標時間分界線
// ===================================================================
function _scrollToTargetTime(targetTimeInt) {
    if (!targetTimeInt || !ExploreState.snapshots.length) return;

    // 找最接近 targetTimeInt 的 snapshot
    const closest = ExploreState.snapshots.reduce((prev, cur) =>
        Math.abs(cur.time_int - targetTimeInt) < Math.abs(prev.time_int - targetTimeInt) ? cur : prev
    );

    // 高亮並捲動
    ExploreState.activeSnapSysid = closest.sysid;

    // 重新渲染以套用 active-divider class
    renderTickStream();

    // 等 DOM 更新後捲動
    requestAnimationFrame(() => {
        const divider = document.querySelector(`.snapshot-divider[data-sysid="${closest.sysid}"]`);
        if (divider) {
            divider.scrollIntoView({ behavior: "smooth", block: "center" });
        }
        // 同步觸發左側算式還原
        loadCalcTrace(closest.sysid, closest.time_int);
    });
}

// ===================================================================
// 河流渲染
// ===================================================================
function renderTickStream() {
    const container = document.getElementById("ex-tick-stream");
    const placeholder = document.getElementById("ex-stream-placeholder");
    const header = document.getElementById("ex-stream-header");

    if (!ExploreState.ticks.length && !ExploreState.snapshots.length) {
        container.style.display = "none";
        if (header) header.style.display = "none";
        placeholder.style.display = "flex";
        placeholder.innerHTML = "<p>⚠️ 查無 Tick 資料</p>";
        return;
    }

    placeholder.style.display = "none";
    container.style.display = "block";
    if (header) header.style.display = "flex";

    // 建立 snapshot sysid → 物件快速查找
    const snapMap = {};
    ExploreState.snapshots.forEach(s => { snapMap[s.sysid] = s; });

    const fragments = [];
    const snapSysids = ExploreState.snapshots.map(s => s.sysid).sort((a, b) => a - b);
    let snapIdx = 0;

    ExploreState.ticks.forEach(tick => {
        // 在此 tick 之前若有 snapshot，先插入分界線
        while (snapIdx < snapSysids.length && snapSysids[snapIdx] <= tick.seqno) {
            const snap = snapMap[snapSysids[snapIdx]];
            if (snap) fragments.push(renderSnapDivider(snap));
            snapIdx++;
        }
        fragments.push(renderTickRow(tick));
    });

    // 尾端剩餘 snapshot
    while (snapIdx < snapSysids.length) {
        const snap = snapMap[snapSysids[snapIdx]];
        if (snap) fragments.push(renderSnapDivider(snap));
        snapIdx++;
    }

    container.innerHTML = fragments.join("");

    // 更新 meta 資訊
    const metaEl = document.getElementById("ex-stream-meta");
    if (metaEl) {
        const validCount = ExploreState.ticks.filter(t => t.is_valid).length;
        metaEl.textContent =
            `${ExploreState.ticks.length} 筆 Tick（有效 ${validCount}），${ExploreState.snapshots.length} 個快照`;
    }
}

function renderSnapDivider(snap) {
    const timeStr = formatTimeInt(snap.time_int);
    const isActive = snap.sysid === ExploreState.activeSnapSysid;
    const activeClass = isActive ? " active-divider" : "";
    return `
    <div class="snapshot-divider${activeClass}"
         data-sysid="${snap.sysid}"
         data-time-int="${snap.time_int}"
         onclick="onDividerClick(${snap.sysid}, ${snap.time_int})">
        <span class="divider-time">▶ ${timeStr}</span>
        <span class="divider-sysid">SysID: ${snap.sysid}</span>
        <span class="divider-snap-info">點擊查看算式</span>
    </div>`;
}

function renderTickRow(tick) {
    const spread = (tick.ask - tick.bid).toFixed(1);
    const invalidClass = tick.is_valid ? "" : " tick-invalid";

    // tags badge：LAST / MIN
    const tagBadges = (tick.tags || []).map(tag =>
        `<span class="badge badge-${tag.toLowerCase()}">${tag}</span>`
    );

    // 錯誤 badge：E1: 報價為零 格式，時指漂显示完整說明
    const errorBadges = (tick.error_codes || []).map(ec => {
        const label = ERROR_LABELS[ec] ? `${ec}: ${ERROR_LABELS[ec]}` : ec;
        return `<span class="badge badge-error" title="${label}">${label}</span>`;
    });

    const badgesHtml = [...tagBadges, ...errorBadges].join("");

    return `
    <div class="tick-row${invalidClass}">
        <span class="t-time">${tick.time_display || tick.time}</span>
        <span class="t-bid">${tick.bid.toFixed(1)}</span>
        <span class="t-ask">${tick.ask.toFixed(1)}</span>
        <span class="t-spread">±${spread}</span>
        <span class="t-seqno">#${tick.seqno}</span>
        <span class="t-badges">${badgesHtml}</span>
    </div>`;
}

// ===================================================================
// 分界線點擊 → 算式還原
// ===================================================================
async function onDividerClick(sysid, timeInt) {
    ExploreState.activeSnapSysid = sysid;
    // 只更新 class，不整個重繪（效能優化）
    document.querySelectorAll(".snapshot-divider").forEach(el => {
        el.classList.toggle("active-divider", parseInt(el.dataset.sysid) === sysid);
    });
    await loadCalcTrace(sysid, timeInt);
}

async function loadCalcTrace(sysid, timeInt) {
    const { date, term, strike } = ExploreState;
    if (!date || !term || !strike || !timeInt) return;

    try {
        const res = await fetch(
            `/api/explore/calc_trace?date=${date}&term=${term}&time_int=${timeInt}&strike=${strike}`
        );
        const trace = await res.json();
        if (trace.error) throw new Error(trace.error);
        renderCalcTrace(trace);
        renderExploreCompare(trace);
    } catch (err) {
        document.getElementById("ex-trace-content").innerHTML =
            `<p style="color:#d9534f;">載入算式失敗：${err.message}</p>`;
    }
}

// ===================================================================
// 算式還原渲染
// ===================================================================
function renderCalcTrace(trace) {
    const container = document.getElementById("ex-calc-trace");
    const content = document.getElementById("ex-trace-content");
    const placeholder = document.getElementById("ex-analysis-placeholder");

    if (placeholder) placeholder.style.display = "none";
    container.style.display = "block";

    const fmt = (v, digits = 4) => (v == null) ? "—" : Number(v).toFixed(digits);
    const diffClass = (a, b, digits = 4) => {
        if (a == null || b == null) return "";
        return (Math.abs(a - b) > Math.pow(10, -digits)) ? " trace-diff" : " trace-match";
    };

    content.innerHTML = `
    <div class="trace-row" style="font-weight:bold; margin-bottom:8px;">Call 側 (CP=C)</div>
    <div class="trace-row">
        <span class="trace-label">Q_hat Bid/Ask</span>
        <span class="trace-value">${fmt(trace.c_q_hat_bid)} / ${fmt(trace.c_q_hat_ask)}</span>
    </div>
    <div class="trace-row">
        <span class="trace-label">來源</span>
        <span class="trace-value">${trace.c_source || "—"}</span>
    </div>
    <div class="trace-row">
        <span class="trace-label">EMA 前值</span>
        <span class="trace-value">${fmt(trace.c_ema_prev)}</span>
    </div>
    <div class="trace-row">
        <span class="trace-label">Alpha</span>
        <span class="trace-value">${fmt(trace.alpha, 6)}</span>
    </div>
    <div class="trace-formula">${trace.c_formula || "—"}</div>
    <div class="trace-row" style="margin-top:6px;">
        <span class="trace-label">EMA (Ours)</span>
        <span class="trace-value${diffClass(trace.c_ema, trace.c_ema_prod)}">${fmt(trace.c_ema)}</span>
    </div>
    <div class="trace-row">
        <span class="trace-label">EMA (PROD)</span>
        <span class="trace-value${diffClass(trace.c_ema, trace.c_ema_prod)}">${fmt(trace.c_ema_prod)}</span>
    </div>
    <hr style="margin:10px 0; border-color:#e0e0e0;">
    <div class="trace-row" style="font-weight:bold; margin-bottom:8px;">Put 側 (CP=P)</div>
    <div class="trace-row">
        <span class="trace-label">Q_hat Bid/Ask</span>
        <span class="trace-value">${fmt(trace.p_q_hat_bid)} / ${fmt(trace.p_q_hat_ask)}</span>
    </div>
    <div class="trace-row">
        <span class="trace-label">來源</span>
        <span class="trace-value">${trace.p_source || "—"}</span>
    </div>
    <div class="trace-row">
        <span class="trace-label">EMA 前值</span>
        <span class="trace-value">${fmt(trace.p_ema_prev)}</span>
    </div>
    <div class="trace-formula">${trace.p_formula || "—"}</div>
    <div class="trace-row" style="margin-top:6px;">
        <span class="trace-label">EMA (Ours)</span>
        <span class="trace-value${diffClass(trace.p_ema, trace.p_ema_prod)}">${fmt(trace.p_ema)}</span>
    </div>
    <div class="trace-row">
        <span class="trace-label">EMA (PROD)</span>
        <span class="trace-value${diffClass(trace.p_ema, trace.p_ema_prod)}">${fmt(trace.p_ema_prod)}</span>
    </div>`;
}

// ===================================================================
// Ours vs PROD 比對
// ===================================================================
function renderExploreCompare(trace) {
    const section = document.getElementById("ex-compare-section");
    const content = document.getElementById("ex-compare-content");
    section.style.display = "block";

    const fields = [
        { label: "Call EMA", ours: trace.c_ema, prod: trace.c_ema_prod },
        { label: "Put EMA", ours: trace.p_ema, prod: trace.p_ema_prod },
        { label: "Alpha", ours: trace.alpha, prod: trace.alpha },
        { label: "Snap SysID", ours: trace.snapshot_sysID, prod: null },
    ];

    const rows = fields.map(f => {
        const isDiff = (f.ours != null && f.prod != null && Math.abs(f.ours - f.prod) > 1e-4);
        const cls = isDiff ? ' class="diff-row"' : "";
        return `<tr${cls}>
            <td>${f.label}</td>
            <td class="${isDiff ? "diff-ours" : ""}">${f.ours != null ? Number(f.ours).toFixed(4) : "—"}</td>
            <td class="${isDiff ? "diff-prod" : ""}">${f.prod != null ? Number(f.prod).toFixed(4) : "—"}</td>
        </tr>`;
    }).join("");

    content.innerHTML = `
    <table class="compare-table" style="font-size:13px;">
        <thead><tr><th>欄位</th><th>Ours</th><th>PROD</th></tr></thead>
        <tbody>${rows}</tbody>
    </table>`;
}

// ===================================================================
// ±15 秒移動（在下拉選單中找相鄰選項）
// ===================================================================
function exploreMoveTime(deltaSeconds) {
    const timeSelect = document.getElementById("ex-time");
    const allTimes = ExploreState.allTimes;

    if (!allTimes || allTimes.length === 0) return;

    const currentVal = parseInt(timeSelect.value, 10);
    const currentIdx = allTimes.indexOf(currentVal);

    let newIdx;
    if (deltaSeconds > 0) {
        newIdx = currentIdx < allTimes.length - 1 ? currentIdx + 1 : currentIdx;
    } else {
        newIdx = currentIdx > 0 ? currentIdx - 1 : 0;
    }

    const newTime = allTimes[newIdx];
    timeSelect.value = newTime;
    ExploreState.timeInt = newTime;

    updateCurrentLabel();
    // 自動重新搜尋
    exploreSearch();
}

// ===================================================================
// 載入更早 / 更晚
// ===================================================================
async function exploreLoadMore(direction) {
    if (!ExploreState.date) return;
    showExploreLoading(true);
    try {
        if (direction === "earlier") {
            await _fetchStream({ prependSysid: ExploreState.currentRange[0] - 1 });
        } else {
            await _fetchStream({ appendSysid: ExploreState.currentRange[1] + 1 });
        }
    } catch (err) {
        alert("載入失敗：" + err.message);
    } finally {
        showExploreLoading(false);
    }
}

// ===================================================================
// 跳至上/下一個差異
// ===================================================================
async function exploreJumpDiff(direction) {
    const { date, term, strike, cp, timeInt } = ExploreState;
    if (!date || !strike || !timeInt) {
        alert("請先執行一次搜尋！");
        return;
    }

    showExploreLoading(true);
    try {
        const res = await fetch(
            `/api/explore/find_diff?date=${date}&term=${term}&strike=${strike}&cp=${cp}`
            + `&current_time=${timeInt}&direction=${direction}`
        );
        const data = await res.json();

        if (!data.found) {
            alert(direction === "next" ? "已是最後一個差異" : "已是第一個差異");
            return;
        }

        // 更新下拉選單選項並搜尋
        const timeSelect = document.getElementById("ex-time");
        if (timeSelect) timeSelect.value = data.time_int;
        ExploreState.timeInt = data.time_int;

        updateCurrentLabel(`↕ 差異：${data.column}（${data.ours} vs ${data.prod}）`);
        await _fetchStream();
        _scrollToTargetTime(data.time_int);

    } catch (err) {
        alert("跳轉失敗：" + err.message);
    } finally {
        showExploreLoading(false);
    }
}

// ===================================================================
// 顯示/隱藏按鈕
// ===================================================================
function showLoadMoreButtons(show) {
    document.getElementById("ex-btn-load-earlier").style.display = show ? "block" : "none";
    document.getElementById("ex-btn-load-later").style.display = show ? "block" : "none";
}

// ===================================================================
// 工具函式
// ===================================================================
function formatTimeInt(t) {
    /** 將 HMMSS 或 HHMMSS 格式整數轉為 HH:MM:SS */
    const s = String(t).padStart(6, "0");
    return `${s.slice(0, 2)}:${s.slice(2, 4)}:${s.slice(4, 6)}`;
}

function updateCurrentLabel(extra) {
    const el = document.getElementById("ex-current-label");
    if (!el) return;
    const timeStr = ExploreState.timeInt ? formatTimeInt(ExploreState.timeInt) : "—";
    el.textContent = `${ExploreState.term} | Strike: ${ExploreState.strike} | CP: ${ExploreState.cp} | @${timeStr}${extra ? "  " + extra : ""}`;
}

function showExploreLoading(show) {
    const btn = document.getElementById("ex-btn-search");
    if (btn) btn.disabled = show;
    const ind = document.getElementById("loading-indicator");
    if (ind) ind.style.display = show ? "inline" : "none";
}

function showExploreError(msg) {
    const placeholder = document.getElementById("ex-stream-placeholder");
    if (placeholder) {
        placeholder.style.display = "flex";
        placeholder.innerHTML = `<p style="color:#d9534f;">⚠️ ${msg}</p>`;
    }
    const container = document.getElementById("ex-tick-stream");
    if (container) container.style.display = "none";
    const header = document.getElementById("ex-stream-header");
    if (header) header.style.display = "none";
}
