/**
 * 正式環境 VIX 走勢儀表板
 */

let vixChart = null;
let dashboardTimes = [];
let currentDashboardIdx = -1;

// 當切換到 Dashboard 頁籤時，重新 resize chart
function initDashboard() {
    if (!vixChart) {
        let chartDom = document.getElementById('dashboard-chart');
        if (chartDom) {
            vixChart = echarts.init(chartDom);

            // 監聽圖表點擊事件
            vixChart.on('click', function (params) {
                if (params.data && params.data.time_str) {
                    let time_str = params.data.time_str; // e.g. "091500"
                    loadSnapshot(time_str);
                }
            });
        }
    } else {
        vixChart.resize();
    }
}

// 供 main.js 呼叫載入當天圖表
async function loadDashboardChart() {
    initDashboard();

    const date = document.getElementById('date-selector').value;
    if (!date) return;

    document.getElementById('loading-indicator').style.display = 'inline';

    try {
        const res = await fetch(`/api/vix_trend?date=${date}`);
        const data = await res.json();

        if (data.error) {
            console.error("載入 VIX 走勢失敗:", data.error);
            alert("載入 VIX 走勢失敗：" + data.error);
            return;
        }

        renderVixChart(data.rows);

        // 隱藏快照面板，直到使用者點擊圖表
        document.getElementById('dashboard-snapshot-panel').classList.add('hidden');

    } catch (e) {
        console.error(e);
        alert("網路錯誤或 JSON 解析失敗");
    } finally {
        document.getElementById('loading-indicator').style.display = 'none';
    }
}

function renderVixChart(rows) {
    if (!vixChart) return;

    // 預期 rows: [{time: "090000", vix: 14.5, ori_vix: 15.1}, ...]
    let times = [];
    let vixData = [];
    let oriVixData = [];
    dashboardTimes = [];

    rows.forEach(row => {
        // 格式化時間，例如 090000 -> 09:00:00
        let t = row.time.toString().padStart(6, '0');
        dashboardTimes.push(t);
        let formattedTime = `${t.substring(0, 2)}:${t.substring(2, 4)}:${t.substring(4, 6)}`;

        times.push(formattedTime);
        vixData.push({
            value: row.vix > 0 ? row.vix : null, // 把 -1 當作 null 處理，讓圖斷開或是以 ori_vix 為主
            time_str: t
        });
        oriVixData.push({
            value: row.ori_vix,
            time_str: t
        });
    });

    let option = {
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' }
        },
        legend: {
            data: ['PROD VIX', 'ORI VIX'],
            top: 10
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '10%', // 留空間給 dataZoom
            containLabel: true
        },
        xAxis: {
            type: 'category',
            boundaryGap: false,
            data: times
        },
        yAxis: {
            type: 'value',
            min: 'dataMin', // Y軸不要從0開始，比較容易看出波動
            max: 'dataMax'
        },
        dataZoom: [
            {
                type: 'inside', // 支持滑鼠滾輪縮放
                start: 0,
                end: 100
            },
            {
                start: 0,
                end: 100,
                height: 15, // 底部拖拉條
                bottom: 5
            }
        ],
        series: [
            {
                name: 'PROD VIX',
                type: 'line',
                data: vixData,
                smooth: true,
                showSymbol: false,
                lineStyle: {
                    width: 3,
                    color: '#dc3545' // 醒目的紅色
                },
                itemStyle: {
                    color: '#dc3545'
                }
            },
            {
                name: 'ORI VIX',
                type: 'line',
                data: oriVixData,
                smooth: true,
                showSymbol: false,
                lineStyle: {
                    width: 2,
                    color: '#adb5bd',  // 灰色
                    type: 'dashed'     // 虛線
                },
                itemStyle: {
                    color: '#adb5bd'
                }
            }
        ]
    };

    vixChart.setOption(option);
}

// 載入序列快照 (左右兩側: Near, Next)
async function loadSnapshot(time_str) {
    const date = document.getElementById('date-selector').value;
    if (!date) return;

    document.getElementById('loading-indicator').style.display = 'inline';

    // 更新標題時間與按鈕狀態
    currentDashboardIdx = dashboardTimes.indexOf(time_str);
    document.getElementById('btn-snapshot-prev').disabled = (currentDashboardIdx <= 0);
    document.getElementById('btn-snapshot-next').disabled = (currentDashboardIdx === -1 || currentDashboardIdx >= dashboardTimes.length - 1);

    let formattedTime = `${time_str.substring(0, 2)}:${time_str.substring(2, 4)}:${time_str.substring(4, 6)}`;
    document.getElementById('snapshot-time-label').innerText = `(${formattedTime})`;
    document.getElementById('dashboard-snapshot-panel').classList.remove('hidden');

    try {
        const res = await fetch(`/api/snapshot?date=${date}&time_int=${time_str}`);
        const data = await res.json();

        if (data.error) {
            alert("載入快照失敗：" + data.error);
            return;
        }

        renderSnapshotTable(data.Near, 'Near', 'snapshot-near-tbody');
        renderSnapshotTable(data.Next, 'Next', 'snapshot-next-tbody');

    } catch (e) {
        console.error(e);
        alert("載入快照錯誤");
    } finally {
        document.getElementById('loading-indicator').style.display = 'none';
    }
}

function renderSnapshotTable(rows, term, tbodyId) {
    const tbody = document.getElementById(tbodyId);
    tbody.innerHTML = '';

    if (!rows || rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8">（無資料）</td></tr>';
        return;
    }

    // 找出最大 contribution 用來畫相對長度的 bar
    const maxContrib = Math.max(...rows.map(r => r.contrib_num || 0));

    rows.forEach(row => {
        let tr = document.createElement('tr');
        if (row.is_atm) {
            tr.classList.add('snapshot-row-atm');
        }

        // 點擊事件：下鑽看行情河流 (使用現有的 tick-stream 邏輯，但放在 modal 裡)
        // 注意：這裡固定使用該列的 time 作為基準，這可能與探勘模式所需參數相似
        tr.style.cursor = 'pointer';
        tr.onclick = function () {
            openStreamModal(term, row.strike, row.time.toString());
        };

        const formatPrice = (val) => (val == null || val === 'X' || val === 'NaN' || val === '') ? '' : Number(val).toFixed(4);

        const c_bid = formatPrice(row['c.bid']);
        const c_ask = formatPrice(row['c.ask']);
        const p_bid = formatPrice(row['p.bid']);
        const p_ask = formatPrice(row['p.ask']);
        const midVal = formatPrice(row['mid']);

        let c_mid = '';
        let p_mid = '';

        // Mid 應該只會有CP的其中一邊 除非市價平序列
        if (row.is_atm) {
            c_mid = midVal;
            p_mid = midVal;
        } else {
            // 用來計算 VIX 的那一方會有報價 (不是 X)
            if (row['c.bid'] != null && row['c.bid'] !== 'X') {
                c_mid = midVal;
            } else if (row['p.bid'] != null && row['p.bid'] !== 'X') {
                p_mid = midVal;
            }
        }

        // 處理 Contrib 與 Bar
        const contribNum = row.contrib_num || 0;
        let barWidth = "0%";
        if (maxContrib > 0 && contribNum > 0) {
            barWidth = `${Math.min(100, Math.max(1, (contribNum / maxContrib) * 100))}%`;
        }

        // 超小數值用科學記號，一般數值用 fixed
        let contribDisplay = contribNum > 0 ?
            (contribNum < 0.0001 ? contribNum.toExponential(4) : contribNum.toFixed(6)) : '';

        let html = `
            <td><span style="color:#0a5c36">${c_bid}</span></td>
            <td><span style="color:#8b1a1a">${c_ask}</span></td>
            <td style="color:#666">${c_mid}</td>
            <td style="font-weight:bold; font-size:13px;">${row.strike}</td>
            <td style="color:#666">${p_mid}</td>
            <td><span style="color:#0a5c36">${p_bid}</span></td>
            <td><span style="color:#8b1a1a">${p_ask}</span></td>
            <td class="contrib-cell">
                <div style="position:relative; width:100%; height:18px; display:flex; align-items:center; justify-content:flex-end;">
                    <div style="position:absolute; right:0; top:0; bottom:0; background:rgba(25, 135, 84, 0.2); border-radius:3px; width:${barWidth}; min-width:1px;"></div>
                    <span style="position:relative; z-index:1; font-size:11px; font-family:monospace; padding-right:4px;">${contribDisplay}</span>
                </div>
            </td>
        `;

        tr.innerHTML = html;
        tbody.appendChild(tr);
    });

    // 渲染完畢後，將價平序列 (ATM) 自動捲動置中
    requestAnimationFrame(() => {
        const atmRow = tbody.querySelector('.snapshot-row-atm');
        if (atmRow) {
            atmRow.scrollIntoView({ block: 'center', behavior: 'smooth' });
        }
    });
}

function navigateSnapshot(step) {
    if (dashboardTimes.length === 0 || currentDashboardIdx === -1) return;

    let nextIdx = currentDashboardIdx + step;
    if (nextIdx >= 0 && nextIdx < dashboardTimes.length) {
        let nextTimeStr = dashboardTimes[nextIdx];
        loadSnapshot(nextTimeStr);
    }
}

/* ===================================================
   Modal 行情河流 (復用/擴展自 explore_stream 邏輯)
   =================================================== */

// 這個變數只用於 modal 開啟的這組查詢
let currentModalStream = {
    date: '', term: '', strike: '', time_int: ''
};

function openStreamModal(term, strike, time_int) {
    const date = document.getElementById('date-selector').value;
    if (!date) return;

    currentModalStream = { date, term, strike, time_int };

    let formattedTime = `${time_int.substring(0, 2)}:${time_int.substring(2, 4)}:${time_int.substring(4, 6)}`;
    document.getElementById('modal-stream-meta').innerText = `(${term} Term, Strike: ${strike}, 基期時間: ${formattedTime})`;

    document.getElementById('tick-stream-modal').style.display = 'flex';
    document.getElementById('modal-stream-header').style.display = 'flex';

    // 清空並載入
    const container = document.getElementById('modal-tick-stream');
    container.innerHTML = '<div style="padding: 20px; text-align: center; color: #888;">載入中...</div>';

    document.getElementById('modal-btn-load-earlier').style.display = 'none';
    document.getElementById('modal-btn-load-later').style.display = 'none';

    // 呼叫既有的 API (同時附帶 CP 其實不重要，因為我們在前後台會展示所有 tick)
    // 但 tick_loader.query_stream 會傳回連續行情，我們可以稍微封裝
    // 因為底層 API 必須帶 CP (在 get_stream 時用來分組)
    // 為了展示兩邊，我們這裡 Call 跟 Put 是分開兩條河流嗎？其實一般是一個選項

    // 因為你的 "行情河流" API (`/api/explore/ticks_stream`) 需要 CP，我們選擇預設先載入 Call ?
    // 如果想要同時呈現，也可以。依照原本設計，我們可能需要做個小切換，但這裡為了簡化，
    // 我先判斷是 Call 邊有價還是 Put 邊有價。以 Out-Of-The-Money 優先！

    let defaultCp = 'Call';
    // 簡單判斷：如果 Strike > (假設一個目前指數 21000)，我們抓 Call。這並不完美。
    // 或我們也可以給一個提示。

    fetchStreamDataForModal(defaultCp);
}

function fetchStreamDataForModal(cp, prependSysId = null, appendSysId = null) {
    const { date, term, strike, time_int } = currentModalStream;

    // 我們可以同時顯示 Call 和 Put 嗎？目前的 UI `tick-stream-header` 只有一組 Bid/Ask
    // 為了簡單起見，我們先用一個 CP。更好的作法是在 Modal 標題旁放個 Call/Put 切換按鈕
    // 這裡我們預設先抓 Call，把標題加上 (Call) 讓使用者知道。
    document.getElementById('modal-stream-meta').innerText = `(${term} Term, Strike: ${strike}, ${cp}, 基期: ${time_int})`;

    let url = `/api/explore/ticks_stream?date=${date}&term=${term}&strike=${strike}&cp=${cp}&time_int=${time_int}`;
    if (prependSysId) url += `&prepend_sysid=${prependSysId}`;
    if (appendSysId) url += `&append_sysid=${appendSysId}`;

    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                document.getElementById('modal-tick-stream').innerHTML = `<div style="color:red; margin:10px;">${data.error}</div>`;
                return;
            }

            // 復用 explorer.js 裡的渲染函式
            // 但因為 explorer.js 寫死了 document.getElementById("ex-tick-stream")
            // 我們需要直接將 data.html 塞給 modal

            if (prependSysId) {
                // 往上增加
                const oldScroll = document.getElementById('modal-tick-stream').scrollHeight;
                document.getElementById('modal-tick-stream').insertAdjacentHTML('afterbegin', data.html);
                const newScroll = document.getElementById('modal-tick-stream').scrollHeight;
                document.getElementById('modal-tick-stream').scrollTop = newScroll - oldScroll;
            } else if (appendSysId) {
                // 往下增加
                document.getElementById('modal-tick-stream').insertAdjacentHTML('beforeend', data.html);
            } else {
                // 初次載入
                document.getElementById('modal-tick-stream').innerHTML = data.html;
                // 自動轉向中間
                setTimeout(() => {
                    const snapDiv = document.querySelector('#modal-tick-stream .active-divider');
                    if (snapDiv) {
                        snapDiv.scrollIntoView({ block: 'center', behavior: 'smooth' });
                    }
                }, 100);
            }

            // 更新按鈕狀態
            const btnEarly = document.getElementById('modal-btn-load-earlier');
            const btnLater = document.getElementById('modal-btn-load-later');

            if (data.min_sysid && data.min_sysid > 0) {
                btnEarly.style.display = 'block';
                btnEarly.onclick = () => fetchStreamDataForModal(cp, data.min_sysid, null);
            } else {
                btnEarly.style.display = 'none';
            }

            if (data.max_sysid) {
                btnLater.style.display = 'block';
                btnLater.onclick = () => fetchStreamDataForModal(cp, null, data.max_sysid);
            } else {
                btnLater.style.display = 'none';
            }
        })
        .catch(err => {
            document.getElementById('modal-tick-stream').innerHTML = `<div style="color:red; margin:10px;">載入發生錯誤</div>`;
            console.error(err);
        });
}

function closeStreamModal() {
    document.getElementById('tick-stream-modal').style.display = 'none';
}
