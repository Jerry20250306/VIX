document.addEventListener("DOMContentLoaded", () => {
    init();
});

const API_BASE = "/api";

// 分頁與篩選狀態
let currentDate = null;
let currentPage = 1;
const perPage = 200; // Updated to 200 as requested
let currentColumnFilter = "all";
let currentTickRow = null; // 儲存目前檢視明細的 row，供手動查詢 Tick 用

async function init() {
    const dateSelect = document.getElementById("date-selector");
    const colFilter = document.getElementById("column-filter");

    try {
        const res = await fetch(`${API_BASE}/dates`);
        const data = await res.json();

        dateSelect.innerHTML = '<option value="">請選擇日期...</option>';
        data.dates.forEach(date => {
            const opt = document.createElement("option");
            opt.value = date;
            opt.textContent = date;
            dateSelect.appendChild(opt);
        });

        dateSelect.addEventListener("change", (e) => {
            if (e.target.value) {
                currentDate = e.target.value;
                currentPage = 1;
                // 重置篩選
                currentColumnFilter = "all";
                colFilter.value = "all";
                loadDiffData(currentDate, currentPage);
            } else {
                clearPanels();
            }
        });

        // 監聽欄位篩選
        colFilter.addEventListener("change", (e) => {
            if (!currentDate) return;
            currentColumnFilter = e.target.value;
            currentPage = 1;
            loadDiffData(currentDate, currentPage);
        });

    } catch (err) {
        console.error("初始化失敗:", err);
        dateSelect.innerHTML = '<option value="">載入失敗</option>';
    }
}

async function loadDiffData(date, page) {
    const loading = document.getElementById("loading-indicator");
    loading.style.display = "inline";

    try {
        // 加入 column 參數
        const url = `${API_BASE}/diff/${date}?page=${page}&per_page=${perPage}&column=${currentColumnFilter}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error("API Error");

        const data = await res.json();

        renderSummary(data);
        updateColumnFilterOptions(data); // 更新篩選選單
        renderDiffTable(data.rows);
        renderPagination(data.page, data.total_pages, data.total);

        // 顯示面板
        document.getElementById("summary-panel").classList.remove("hidden");
        document.getElementById("diff-panel").classList.remove("hidden");

    } catch (err) {
        console.error("載入差異失敗:", err);
        alert("載入差異報告失敗，請檢查後端 logs");
    } finally {
        loading.style.display = "none";
    }
}

function updateColumnFilterOptions(data) {
    const select = document.getElementById("column-filter");
    const currentVal = select.value;
    const allCols = data.all_columns || [];

    // 若選項已存在且數量一致，則不重新渲染 (避免畫面閃爍或使用者操作中斷)
    // 但簡單起見，我們檢查第一個選項之後的長度
    if (select.options.length - 1 === allCols.length) {
        return;
    }

    let html = '<option value="all">全部</option>';
    allCols.forEach(col => {
        const isSelected = col === currentVal ? 'selected' : '';
        html += `<option value="${col}" ${isSelected}>${col}</option>`;
    });
    select.innerHTML = html;
    // 確保值正確 (若是重新渲染)
    select.value = currentColumnFilter;
}

function renderSummary(data) {
    const container = document.getElementById("summary-content");
    const { summary, no_diff_summary, total_per_term, all_columns, total_diffs } = data;

    let html = `<p>總差異筆數: <strong style="color: ${total_diffs > 0 ? '#d9534f' : '#5cb85c'}">${total_diffs.toLocaleString()}</strong></p>`;

    // 收集所有 Term（合併 diff 和 no-diff 的 keys）
    const allTerms = new Set([...Object.keys(summary || {}), ...Object.keys(no_diff_summary || {})]);

    html += '<div style="display:flex; gap:20px; flex-wrap:wrap;">';

    for (const term of allTerms) {
        const diffCols = summary[term] || {};
        const noDiffCols = no_diff_summary[term] || {};
        const totalRows = (total_per_term || {})[term] || 0;

        html += `<div class="summary-box" style="min-width:300px;">
            <h3>${term} Term <span style="font-size:12px; color:#888;">(共 ${totalRows.toLocaleString()} 筆比對)</span></h3>
            <table style="width:100%; font-size:13px;">
                <thead>
                    <tr>
                        <th>欄位</th>
                        <th>狀態</th>
                        <th>差異筆數</th>
                        <th>一致筆數</th>
                    </tr>
                </thead>
                <tbody>`;

        // 用 all_columns 排序顯示所有欄位
        const cols = all_columns || Object.keys({ ...diffCols, ...noDiffCols });

        for (const col of cols) {
            const diffCount = diffCols[col] || 0;
            const noDiffCount = diffCount > 0 ? (totalRows - diffCount) : (noDiffCols[col] || totalRows);
            const isPassing = diffCount === 0;

            const statusIcon = isPassing ? '✅' : '❌';
            const rowStyle = isPassing ? '' : 'background-color: #fff5f5;';

            html += `<tr style="${rowStyle}">
                <td><strong>${col}</strong></td>
                <td style="text-align:center">${statusIcon}</td>
                <td style="text-align:right; color:${diffCount > 0 ? '#d9534f' : '#ccc'};">${diffCount > 0 ? diffCount.toLocaleString() : '-'}</td>
                <td style="text-align:right; color:#5cb85c;">${noDiffCount.toLocaleString()}</td>
            </tr>`;
        }

        html += `</tbody></table></div>`;
    }

    html += '</div>';
    container.innerHTML = html;
}

function renderDiffTable(rows) {
    const tbody = document.querySelector("#diff-table tbody");
    tbody.innerHTML = "";

    rows.forEach((row, index) => {
        const tr = document.createElement("tr");
        // 計算全域序號
        const globalIndex = (currentPage - 1) * perPage + index + 1;
        tr.innerHTML = `
            <td>${globalIndex}</td>
            <td>${row.Time}</td>
            <td>${row.Term}</td>
            <td>${row.Strike}</td>
            <td>${row.CP}</td>
            <td>${row.Column}</td>
            <td class="diff-ours">${formatValue(row.Ours)}</td>
            <td class="diff-prod">${formatValue(row.PROD)}</td>
            <td><button onclick='viewDetail(${JSON.stringify(row)})'>查看明細</button></td>
        `;

        tr.addEventListener("click", () => viewDetail(row));
        tbody.appendChild(tr);
    });
}

function renderPagination(page, totalPages, total) {
    // 如果分頁容器不存在，動態建立
    let paginationEl = document.getElementById("pagination");
    if (!paginationEl) {
        paginationEl = document.createElement("div");
        paginationEl.id = "pagination";
        paginationEl.className = "pagination";
        // 插入到 diff-table 後面
        const diffPanel = document.getElementById("diff-panel");
        diffPanel.appendChild(paginationEl);
    }

    const startRow = (page - 1) * perPage + 1;
    const endRow = Math.min(page * perPage, total);

    paginationEl.innerHTML = `
        <button ${page <= 1 ? 'disabled' : ''} onclick="goToPage(1)">⏮ 首頁</button>
        <button ${page <= 1 ? 'disabled' : ''} onclick="goToPage(${page - 1})">◀ 上一頁</button>
        <span>第 ${page} / ${totalPages} 頁（顯示 ${startRow.toLocaleString()} ~ ${endRow.toLocaleString()} / ${total.toLocaleString()} 筆）</span>
        <button ${page >= totalPages ? 'disabled' : ''} onclick="goToPage(${page + 1})">下一頁 ▶</button>
        <button ${page >= totalPages ? 'disabled' : ''} onclick="goToPage(${totalPages})">末頁 ⏭</button>
    `;
}

function goToPage(page) {
    if (!currentDate) return;
    currentPage = page;
    loadDiffData(currentDate, currentPage);
    // 捲動到表格頂部
    document.getElementById("diff-panel").scrollIntoView({ behavior: "smooth" });
}

async function viewDetail(row) {
    console.log("查看明細:", row);

    // 儲存 row context 供手動查詢使用
    currentTickRow = row;

    const detailPanel = document.getElementById("detail-panel");
    const compareContainer = document.getElementById("compare-container");
    const currTicksContainer = document.getElementById("curr-ticks");
    const prevTicksContainer = document.getElementById("prev-ticks");

    // 初始化 UI
    detailPanel.classList.remove("hidden");
    compareContainer.innerHTML = "載入中...";
    currTicksContainer.innerHTML = "-";
    prevTicksContainer.innerHTML = "-";

    document.getElementById("curr-sysid-range").textContent = `${row.Prev_SysID || '?'} ~ ${row.SysID}`;
    document.getElementById("prev-sysid-range").textContent = `? ~ ${row.Prev_SysID || '?'}`;

    // 顯示手動查詢區塊並填入預設值
    const manualQuery = document.getElementById("manual-tick-query");
    manualQuery.style.display = "block";
    document.getElementById("manual-curr-start").value = row.Prev_SysID || '';
    document.getElementById("manual-curr-end").value = row.SysID || '';
    document.getElementById("manual-prev-start").value = '';
    document.getElementById("manual-prev-end").value = row.Prev_SysID || '';

    // 捲動到明細區塊
    detailPanel.scrollIntoView({ behavior: "smooth" });

    try {
        // 1. 取得 Comparison Table
        const params = new URLSearchParams({
            date: row.Date,
            term: row.Term,
            strike: row.Strike,
            time: row.Time
        });

        const res = await fetch(`${API_BASE}/prod_row?${params}`);
        if (!res.ok) throw new Error("API Error");

        const data = await res.json();
        renderCompareTable(data, row.Column);

        // 2. 取得 Tick Data
        loadTickData(row);

    } catch (err) {
        console.error("載入明細失敗:", err);
        compareContainer.innerHTML = `<span style="color:red">載入失敗: ${err.message}</span>`;
    }
}

function renderCompareTable(data, highlightCol) {
    const container = document.getElementById("compare-container");

    if (data.error) {
        container.innerHTML = `<span style="color:red">${data.error}</span>`;
        return;
    }

    const { ours, prod, diffs } = data;

    // 找出所有欄位 (聯集)
    const allKeys = new Set([...Object.keys(ours || {}), ...Object.keys(prod || {})]);
    const keyOrder = ["date", "time", "strike", "c.bid", "c.ask", "p.bid", "p.ask", "c.ema", "p.ema", "c.gamma", "p.gamma"];
    const sortedKeys = Array.from(allKeys).sort((a, b) => {
        const idxA = keyOrder.indexOf(a);
        const idxB = keyOrder.indexOf(b);
        if (idxA !== -1 && idxB !== -1) return idxA - idxB;
        if (idxA !== -1) return -1;
        if (idxB !== -1) return 1;
        return a.localeCompare(b);
    });

    let html = `<table class="compare-table">
        <thead>
            <tr>
                <th>欄位</th>
                <th>Ours</th>
                <th>PROD</th>
                <th>差異</th>
            </tr>
        </thead>
        <tbody>`;

    sortedKeys.forEach(key => {
        const valOurs = ours ? ours[key] : "-";
        const valProd = prod ? prod[key] : "-";
        const isDiff = diffs.includes(key);
        let isTargetDiff = false;
        if (highlightCol === key) isTargetDiff = true;
        if (highlightCol === "EMA" && key.endsWith(".ema")) isTargetDiff = true;
        if (highlightCol === "Gamma" && key.endsWith(".gamma")) isTargetDiff = true;

        let rowClass = "";
        if (isTargetDiff) rowClass = "target-diff-row";
        else if (isDiff) rowClass = "diff-row";

        html += `<tr class="${rowClass}">
            <td>${key}</td>
            <td>${formatValue(valOurs)}</td>
            <td>${formatValue(valProd)}</td>
            <td>${isDiff ? '✗' : ''}</td>
        </tr>`;
    });

    html += `</tbody></table>`;
    container.innerHTML = html;
}

function clearPanels() {
    document.getElementById("summary-panel").classList.add("hidden");
    document.getElementById("diff-panel").classList.add("hidden");
    document.getElementById("detail-panel").classList.add("hidden");
}

function formatValue(val) {
    if (val === null || val === undefined) return '<span style="color:#ccc">Null</span>';
    return val;
}

async function loadTickData(row) {
    const currContainer = document.getElementById("curr-ticks");
    const prevContainer = document.getElementById("prev-ticks");

    currContainer.innerHTML = "載入中...";
    prevContainer.innerHTML = "載入中...";

    try {
        const params = new URLSearchParams({
            date: row.Date,
            term: row.Term,
            strike: row.Strike,
            cp: row.CP,
            sys_id: row.SysID,
            prev_sys_id: row.Prev_SysID || ""
        });

        const res = await fetch(`${API_BASE}/ticks?${params}`);
        if (!res.ok) throw new Error("API Error");

        const data = await res.json();

        if (data.error) {
            throw new Error(data.error);
        }

        renderTickTable(data.current_interval, currContainer, "current");
        renderTickTable(data.prev_interval, prevContainer, "prev");

    } catch (err) {
        console.error("載入 ticks 失敗:", err);
        currContainer.innerHTML = `<span style="color:red">載入失敗: ${err.message}</span>`;
        prevContainer.innerHTML = "-";
    }
}

function renderTickTable(intervalData, container, type) {
    if (!intervalData || !intervalData.ticks) {
        container.innerHTML = "無資料";
        return;
    }

    if (intervalData.ticks.length === 0) {
        container.innerHTML = "無 Tick 資料";
        return;
    }

    let html = `<table>
        <thead>
            <tr>
                <th>時間</th>
                <th>Bid</th>
                <th>Ask</th>
                <th>SeqNo</th>
            </tr>
        </thead>
        <tbody>`;

    intervalData.ticks.forEach(tick => {
        html += `<tr>
            <td>${tick.time_display}</td>
            <td>${tick.bid}</td>
            <td>${tick.ask}</td>
            <td>${tick.seqno}</td>
        </tr>`;
    });

    html += `</tbody></table>`;
    container.innerHTML = html;
}

// ===== 手動 SysID 查詢 =====

async function reloadTicksManual() {
    if (!currentTickRow) {
        alert("請先點選差異列表中的『查看明細』");
        return;
    }

    const currStart = document.getElementById("manual-curr-start").value;
    const currEnd = document.getElementById("manual-curr-end").value;
    const prevStart = document.getElementById("manual-prev-start").value;
    const prevEnd = document.getElementById("manual-prev-end").value;

    if (!currEnd && !prevEnd) {
        alert("請至少填入當前區間 SysID 迄 或 前一區間 SysID 迄");
        return;
    }

    const currContainer = document.getElementById("curr-ticks");
    const prevContainer = document.getElementById("prev-ticks");

    currContainer.innerHTML = "查詢中...";
    prevContainer.innerHTML = "查詢中...";

    // 更新顯示標題
    document.getElementById("curr-sysid-range").textContent = `${currStart || '?'} ~ ${currEnd || '?'}`;
    document.getElementById("prev-sysid-range").textContent = `${prevStart || '?'} ~ ${prevEnd || '?'}`;

    try {
        const row = currentTickRow;
        const params = new URLSearchParams({
            date: row.Date,
            term: row.Term,
            strike: row.Strike,
            cp: row.CP,
            sys_id: row.SysID || "0",
            prev_sys_id: row.Prev_SysID || ""
        });

        // 加入手動範圍參數
        if (currStart) params.set("curr_start", currStart);
        if (currEnd) params.set("curr_end", currEnd);
        if (prevStart) params.set("prev_start", prevStart);
        if (prevEnd) params.set("prev_end", prevEnd);

        const res = await fetch(`${API_BASE}/ticks?${params}`);
        if (!res.ok) throw new Error("API Error");

        const data = await res.json();

        if (data.error) {
            throw new Error(data.error);
        }

        renderTickTable(data.current_interval, currContainer, "current");
        renderTickTable(data.prev_interval, prevContainer, "prev");

    } catch (err) {
        console.error("手動查詢 Ticks 失敗:", err);
        currContainer.innerHTML = `<span style="color:red">查詢失敗: ${err.message}</span>`;
        prevContainer.innerHTML = "-";
    }
}

function resetTickInputs() {
    if (!currentTickRow) return;
    const row = currentTickRow;
    document.getElementById("manual-curr-start").value = row.Prev_SysID || '';
    document.getElementById("manual-curr-end").value = row.SysID || '';
    document.getElementById("manual-prev-start").value = '';
    document.getElementById("manual-prev-end").value = row.Prev_SysID || '';
    // 重新使用預設值載入
    loadTickData(row);
}
