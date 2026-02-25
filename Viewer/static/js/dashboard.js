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

            // 讓整個圖表區域 (包含沒有畫點的垂直空間) 都能輕易捕捉點擊位置
            vixChart.getZr().on('click', function (params) {
                const pointInPixel = [params.offsetX, params.offsetY];
                // 確保點擊落入表格有效範圍
                if (vixChart.containPixel('grid', pointInPixel)) {
                    // convertFromPixel 取得游標對應的 x 軸資料索引
                    const xIndex = vixChart.convertFromPixel({ seriesIndex: 0 }, pointInPixel)[0];
                    if (xIndex >= 0 && xIndex < dashboardTimes.length) {
                        let time_str = dashboardTimes[xIndex];
                        loadSnapshot(time_str);
                    }
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
    if (vixChart) {
        vixChart.showLoading({ text: '🔄 讀取走勢資料中...', color: '#dc3545', textColor: '#2c3e50', maskColor: 'rgba(255, 255, 255, 0.8)', fontSize: 18 });
    }

    try {
        // 加入 300ms 的視覺緩衝時間，讓 User 確實看見 Loading 提示，不會覺得畫面結凍
        await new Promise(r => setTimeout(r, 300));

        const [trendRes, alertRes] = await Promise.all([
            fetch(`/api/vix_trend?date=${date}`),
            fetch(`/api/alerts?date=${date}`)
        ]);

        const data = await trendRes.json();
        const alertData = await alertRes.json();

        if (data.error) {
            console.error("載入 VIX 走勢失敗:", data.error);
            alert("載入 VIX 走勢失敗：" + data.error);
            return;
        }

        renderVixChart(data.rows, alertData.alerts || []);

        // 隱藏快照面板，直到使用者點擊圖表
        document.getElementById('dashboard-snapshot-panel').classList.add('hidden');

    } catch (e) {
        console.error(e);
        alert("網路錯誤或 JSON 解析失敗");
    } finally {
        if (vixChart) vixChart.hideLoading();
        document.getElementById('loading-indicator').style.display = 'none';
    }
}

function renderVixChart(rows, alerts) {
    if (!vixChart) return;

    // 預期 rows: [{time: "090000", vix: 14.5, ori_vix: 15.1}, ...]
    let times = [];
    let vixData = [];
    let oriVixData = [];
    dashboardTimes = [];

    rows.forEach(row => {
        // 格式化時間，例如 090000 -> 09:00:00 (保留秒數給 tooltip，X軸另透過 formatter 截斷)
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
            formatter: function (params) {
                let html = `<div style="font-weight:bold;margin-bottom:8px;border-bottom:1px solid #eee;padding-bottom:4px;">${params[0].axisValue}</div>`;
                let alertHtml = "";

                params.forEach(p => {
                    if (p.seriesName === 'Alert') {
                        alertHtml += `<div style="margin-top: 8px; padding: 6px 8px; background-color: #f8dbd9; border: 1px solid #e03e3e; border-radius: 4px; color: #a41515;">
                            <strong>${p.data.tooltipLabel}</strong><br>
                            <span style="font-size:12px; color:#555;">(點擊閃爍紅點查看報告明細)</span>
                        </div>`;
                    } else if (p.value !== null && p.value !== undefined) {
                        let val = Number(p.value).toFixed(2);
                        html += `<div>${p.marker} ${p.seriesName}: <span style="font-weight:bold; float:right; margin-left:15px;">${val}</span></div>`;
                    }
                });

                return html + alertHtml;
            },
            axisPointer: {
                type: 'cross',
                label: { backgroundColor: '#37352f' }
            },
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            borderColor: 'rgba(55, 53, 47, 0.09)',
            borderWidth: 1,
            textStyle: { color: '#37352f', fontSize: 13 },
            padding: 12,
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
        },
        legend: {
            data: ['VIX揭示值', 'VIX計算值'],
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
            data: times,
            axisLine: { lineStyle: { color: 'rgba(55, 53, 47, 0.16)' } },
            axisLabel: {
                color: 'rgba(55, 53, 47, 0.65)',
                fontSize: 13,
                formatter: function (value) {
                    return value.substring(0, 5); // 截掉秒數，只留 HH:MM
                }
            }
        },
        yAxis: {
            type: 'value',
            min: 'dataMin', // Y軸不要從0開始，比較容易看出波動
            max: 'dataMax',
            splitLine: { lineStyle: { color: 'rgba(55, 53, 47, 0.06)', type: 'dashed' } },
            axisLabel: {
                color: 'rgba(55, 53, 47, 0.65)',
                fontSize: 13,
                formatter: function (value) {
                    return value.toFixed(1); // 強制小數點第一位
                }
            }
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
                name: 'VIX揭示值',
                type: 'line',
                data: vixData,
                smooth: 0.3, // 更加平滑柔和
                showSymbol: false,
                lineStyle: {
                    width: 3,
                    color: '#2383e2', // 高雅的科技藍
                    shadowColor: 'rgba(35, 131, 226, 0.3)',
                    shadowBlur: 10,
                    shadowOffsetY: 5
                },
                itemStyle: {
                    color: '#2383e2'
                },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(35, 131, 226, 0.2)' },
                        { offset: 1, color: 'rgba(35, 131, 226, 0.01)' }
                    ])
                },
                valueFormatter: function (value) {
                    return value != null ? Number(value).toFixed(2) : '-';
                },
                z: 3 // 讓它蓋在計算值之上
            },
            {
                name: 'VIX計算值',
                type: 'line',
                data: oriVixData,
                smooth: 0.3,
                showSymbol: false,
                lineStyle: {
                    width: 2,
                    type: 'dashed', // 改為虛線，強調是理論上的"計算值"
                    color: 'rgba(55, 53, 47, 0.35)' // 柔和的灰色透視感
                },
                itemStyle: {
                    color: 'rgba(55, 53, 47, 0.4)'
                },
                valueFormatter: function (value) {
                    return value != null ? Number(value).toFixed(2) : '-';
                },
                z: 2
            }
        ]
    };

    // 如果有 alerts，加入 effectScatter Series (閃爍紅點，不僅好看也不會重疊雜亂)
    if (alerts && alerts.length > 0) {
        let alertSeriesData = alerts.map(alert => {
            let t = alert.time.padStart(6, '0');
            let formattedTime = `${t.substring(0, 2)}:${t.substring(2, 4)}:${t.substring(4, 6)}`;

            // 找出對應時間的 y 值 (沿著線條繪製)
            let targetRow = rows.find(r => r.time.toString().padStart(6, '0') === t);
            let y_val = targetRow ? (targetRow.vix > 0 ? targetRow.vix : targetRow.ori_vix) : null;

            return {
                name: 'Alert',
                value: [formattedTime, y_val],
                tooltipLabel: `⚠️ ${alert.time_display} Alert — Condition ${alert.triggered_conditions.join(', ')}`,
                alertData: alert
            };
        });

        option.series.push({
            name: 'Alert',
            type: 'effectScatter',
            coordinateSystem: 'cartesian2d',
            data: alertSeriesData.filter(d => d.value[1] !== null), // 過濾掉找不到對應 Y 軸的點
            symbolSize: 10,
            showEffectOn: 'render',
            rippleEffect: {
                brushType: 'stroke',
                scale: 3
            },
            itemStyle: {
                color: '#e03e3e',
                shadowBlur: 8,
                shadowColor: '#e03e3e'
            },
            zlevel: 5,
            tooltip: {
                // 獨立於全域 cross tooltip，專為 Alert 特製 Hover
                formatter: function (params) {
                    return `<div style="padding: 4px;"><strong>${params.data.tooltipLabel}</strong><br><span style="font-size:12px;color:#666;">點擊紅點查看報告明細</span></div>`;
                }
            }
        });

        // 綁定效果點 click 顯示 modal
        vixChart.on('click', function (params) {
            if (params.seriesName === 'Alert') {
                showAlertModal(params.data.alertData);
                // 防止事件穿透導致觸發背景格線的 snapshot
                params.event.event.stopPropagation();
            }
        });
    }

    vixChart.setOption(option);
}

// 供 Alert Modal 內部切換 Tab 使用
function switchAlertTab(tabName) {
    document.querySelectorAll('.alert-tab').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('[id^="alert-tab-"]').forEach(div => div.style.display = 'none');

    document.querySelector(`.alert-tab[onclick*="'${tabName}'"]`).classList.add('active');
    document.getElementById(`alert-tab-${tabName}`).style.display = 'block';
}

function showAlertModal(alertData) {
    if (!alertData) return;

    // 預設切回摘要 Tab
    switchAlertTab('summary');

    // --- 填充條件清單 ---
    const ul = document.getElementById('alert-conditions-list');
    ul.innerHTML = '';
    alertData.triggered_conditions.forEach(c => {
        let li = document.createElement('li');
        li.innerHTML = `<strong>${c}</strong> — ${alertData.condition_descriptions[c] || 'Unknown condition'}`;
        ul.appendChild(li);
    });

    // --- 填充 Summary ---
    const summary = alertData.summary;
    const p = summary.prev;
    const c = summary.current;

    // Near
    document.getElementById('alert-near-sigma').innerText = `${p.nearSigma2} ${c.nearSigma2 !== p.nearSigma2 ? '→ ' + c.nearSigma2 : '(不變)'}`;
    document.getElementById('alert-near-series').innerText = `${p.nearSeriesCount} → ${c.nearSeriesCount}`;
    let nearPct = p.nearSeriesCount > 0 ? ((c.nearSeriesCount - p.nearSeriesCount) / p.nearSeriesCount * 100).toFixed(1) : 0;
    document.getElementById('alert-near-diff').innerText = `${nearPct > 0 ? '▲' : '▼'}${Math.abs(nearPct)}%`;
    document.getElementById('alert-near-diff').style.color = nearPct < -15 ? '#e03e3e' : '#555';
    document.getElementById('alert-near-type').innerText = `${p.nearType} → ${c.nearType}`;

    // Next
    document.getElementById('alert-next-sigma').innerText = `${p.nextSigma2} ${c.nextSigma2 !== p.nextSigma2 ? '→ ' + c.nextSigma2 : '(不變)'}`;
    document.getElementById('alert-next-series').innerText = `${p.nextSeriesCount} → ${c.nextSeriesCount}`;
    let nextPct = p.nextSeriesCount > 0 ? ((c.nextSeriesCount - p.nextSeriesCount) / p.nextSeriesCount * 100).toFixed(1) : 0;
    document.getElementById('alert-next-diff').innerText = `${nextPct > 0 ? '▲' : '▼'}${Math.abs(nextPct)}%`;
    document.getElementById('alert-next-diff').style.color = nextPct < -15 ? '#e03e3e' : '#555';
    document.getElementById('alert-next-type').innerText = `${p.nextType} → ${c.nextType}`;

    // Global VIX
    let oriPct = c.ori_vix_change ? (parseFloat(c.ori_vix_change) * 100).toFixed(6) : 0;
    document.getElementById('alert-ori-vix').innerHTML = `${p.ori_vix} → ${c.ori_vix} <span style="color:${oriPct > 0 ? 'green' : (oriPct < 0 ? 'red' : 'gray')}">(${oriPct > 0 ? '+' : ''}${oriPct}%)</span>`;
    document.getElementById('alert-display-vix').innerText = `${p.vix} → ${c.vix}`;

    // --- 填充 Contribution 表格 ---
    function renderContribTable(term, tbodyId) {
        let tbody = document.getElementById(tbodyId);
        tbody.innerHTML = '';
        if (alertData.contributions && alertData.contributions[term]) {
            alertData.contributions[term].forEach(row => {
                let tr = document.createElement('tr');
                // 如果右側有值(有改變)，加點淺底色高亮
                if (row.has_changed) {
                    tr.style.backgroundColor = '#fffbeb'; // 淺黃
                }

                let diffPctStr = row.contrib_diff_pct;
                let diffVal = diffPctStr ? parseFloat(diffPctStr.replace('%', '')) : 0;
                let diffColor = diffPctStr === "" ? '#555' : (diffVal > 0 ? '#198754' : (diffVal < 0 ? '#dc3545' : '#555'));

                let weightDiffStr = row.weight_diff;
                let weightDiffVal = weightDiffStr ? parseFloat(weightDiffStr.replace('%', '')) : 0;
                let weightDiffColor = weightDiffStr === "" ? '#555' : (weightDiffVal > 0 ? '#198754' : (weightDiffVal < 0 ? '#dc3545' : '#555'));

                tr.innerHTML = `
                    <td style="font-weight:bold;">${row.strike}</td>
                    <td style="color:#0d6efd;font-weight:bold;">${row.moneyness}</td>
                    <td>${row.prev_mid}</td>
                    <td>${row.curr_mid}</td>
                    <td style="font-family:monospace; color:#888;">${row.prev_spread_ratio}</td>
                    <td style="font-family:monospace;">${row.curr_spread_ratio}</td>
                    <td style="font-family:monospace; color:#888;">${row.prev_contrib}</td>
                    <td style="font-family:monospace;">${row.curr_contrib}</td>
                    <td style="font-family:monospace; color:#888;">${row.prev_weight}</td>
                    <td style="font-family:monospace;">${row.curr_weight}</td>
                    <td style="color:${weightDiffColor}; font-weight:bold; font-family:monospace;">${weightDiffStr === "" ? "-" : weightDiffStr}</td>
                    <td style="color:${diffColor}; font-weight:bold; font-family:monospace;">${diffPctStr === "" ? "-" : diffPctStr}</td>
                `;
                tbody.appendChild(tr);
            });
        }
        if (tbody.innerHTML === '') {
            tbody.innerHTML = '<tr><td colspan="12" style="color:#999; padding:20px;">無明細資料或無變化</td></tr>';
        }
    }

    renderContribTable('Near', 'alert-near-tbody');
    renderContribTable('Next', 'alert-next-tbody');

    // 顯示 Modal
    document.getElementById('alert-modal').style.display = 'flex';
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

    // 加入更明顯的載入中樣式於表格內
    document.getElementById('snapshot-near-tbody').innerHTML = '<tr><td colspan="8" style="padding: 40px; font-size: 16px; font-weight: bold; color: #0d6efd; text-align: center;">🔄 讀取與計算排列中，請稍候...</td></tr>';
    document.getElementById('snapshot-next-tbody').innerHTML = '<tr><td colspan="8" style="padding: 40px; font-size: 16px; font-weight: bold; color: #198754; text-align: center;">🔄 讀取與計算排列中，請稍候...</td></tr>';

    try {
        // 加入視覺緩衝時間確保畫面渲染，避免資料庫或本地瞬間回傳導致閃爍而不自知
        await new Promise(r => setTimeout(r, 300));

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

        // 點擊事件：下鑽看行情河流 
        tr.style.cursor = 'pointer';
        tr.onclick = function (e) {
            let targetCp = 'Call';
            if (row.is_atm) {
                // 若為價平，透過點擊的欄位(td)索引來判斷使用者想看 Call 還是 Put
                let clickedTd = e.target.closest('td');
                if (clickedTd) {
                    // index 0~2 是 Call, 3 是 Strike, 4~6 是 Put, 7 是 Contrib
                    if (clickedTd.cellIndex >= 4) {
                        targetCp = 'Put';
                    } else {
                        targetCp = 'Call';
                    }
                }
            } else {
                // 非價平：預設嘗試開啟有報價的那一邊
                if (row['c.bid'] != null && row['c.bid'] !== 'X') {
                    targetCp = 'Call';
                } else if (row['p.bid'] != null && row['p.bid'] !== 'X') {
                    targetCp = 'Put';
                }
            }
            openStreamModal(term, row.strike, row.time.toString(), targetCp);
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

function openStreamModal(term, strike, time_int, targetCp = 'Call') {
    const date = document.getElementById('date-selector').value;
    if (!date) return;

    currentModalStream = { date, term, strike, time_int };

    let formattedTime = `${time_int.substring(0, 2)}:${time_int.substring(2, 4)}:${time_int.substring(4, 6)}`;
    document.getElementById('modal-stream-meta').innerText = `(${term} Term, Strike: ${strike}, 基期時間: ${formattedTime})`;

    document.getElementById('tick-stream-modal').style.display = 'flex';
    // 每次打開時重置回中央位置與原本的尺寸 (清掉 dragging 造成的 inline 污染)
    document.getElementById('tick-stream-modal').style.top = '50%';
    document.getElementById('tick-stream-modal').style.left = '50%';
    document.getElementById('tick-stream-modal').style.transform = 'translate(-50%, -50%)';

    document.getElementById('modal-stream-header').style.display = 'flex';

    // 清空並載入
    const container = document.getElementById('modal-tick-stream');
    container.innerHTML = '<div style="padding: 20px; text-align: center; color: #888;">載入中...</div>';

    document.getElementById('modal-btn-load-earlier').style.display = 'none';
    document.getElementById('modal-btn-load-later').style.display = 'none';

    fetchStreamDataForModal(targetCp);
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

            // The backend returns { ticks: [], snapshots: [], range: [min, max] }
            let ticks = data.ticks || [];
            let snapshots = data.snapshots || [];
            let fragments = [];

            const snapMap = {};
            snapshots.forEach(s => { snapMap[s.sysid] = s; });
            const snapSysids = snapshots.map(s => s.sysid).sort((a, b) => a - b);
            let snapIdx = 0;

            ticks.forEach(tick => {
                while (snapIdx < snapSysids.length && snapSysids[snapIdx] <= tick.seqno) {
                    const snap = snapMap[snapSysids[snapIdx]];
                    // 注意：renderSnapDivider 需要配合 ExploreState.activeSnapSysid 高亮
                    // 這裡先簡單複用，可能會因為探索模式未啟用而沒黃色，但不影響顯示
                    if (snap) fragments.push(renderSnapDivider(snap));
                    snapIdx++;
                }
                fragments.push(renderTickRow(tick));
            });
            while (snapIdx < snapSysids.length) {
                const snap = snapMap[snapSysids[snapIdx]];
                if (snap) fragments.push(renderSnapDivider(snap));
                snapIdx++;
            }

            let htmlContent = fragments.join("");
            if (!htmlContent) {
                htmlContent = '<div style="padding: 20px; text-align: center; color: #888;">查無報價行情資料</div>';
            }

            if (prependSysId) {
                // 往上增加
                const oldScroll = document.getElementById('modal-tick-stream').scrollHeight;
                document.getElementById('modal-tick-stream').insertAdjacentHTML('afterbegin', htmlContent);
                const newScroll = document.getElementById('modal-tick-stream').scrollHeight;
                document.getElementById('modal-tick-stream').scrollTop = newScroll - oldScroll;
            } else if (appendSysId) {
                // 往下增加
                document.getElementById('modal-tick-stream').insertAdjacentHTML('beforeend', htmlContent);
            } else {
                // 初次載入
                document.getElementById('modal-tick-stream').innerHTML = htmlContent;
                // 自動轉向距離目前設定時間最近的 divider
                setTimeout(() => {
                    const snapDivs = Array.from(document.querySelectorAll('#modal-tick-stream .snapshot-divider'));
                    let bestDiv = null;
                    let minDiff = Infinity;
                    let targetTime = parseInt(time_int, 10);

                    snapDivs.forEach(div => {
                        let divTime = parseInt(div.dataset.timeInt, 10);
                        if (!isNaN(divTime) && Math.abs(divTime - targetTime) < minDiff) {
                            minDiff = Math.abs(divTime - targetTime);
                            bestDiv = div;
                        }
                    });

                    if (bestDiv) {
                        bestDiv.scrollIntoView({ block: 'center', behavior: 'smooth' });
                        // 使該 divider 高亮
                        document.querySelectorAll('#modal-tick-stream .snapshot-divider').forEach(el => el.classList.remove('active-divider'));
                        bestDiv.classList.add('active-divider');
                    }
                }, 100);
            }

            // 更新按鈕狀態
            const btnEarly = document.getElementById('modal-btn-load-earlier');
            const btnLater = document.getElementById('modal-btn-load-later');

            // 後端回傳的是 {"range": [min_sysid, max_sysid]}
            let range = data.range || [0, 0];
            let minSysid = range[0];
            let maxSysid = range[1];

            if (minSysid && minSysid > 0) {
                btnEarly.style.display = 'block';
                btnEarly.onclick = () => fetchStreamDataForModal(cp, minSysid - 1, null);
            } else {
                btnEarly.style.display = 'none';
            }

            if (maxSysid && maxSysid > 0) {
                btnLater.style.display = 'block';
                btnLater.onclick = () => fetchStreamDataForModal(cp, null, maxSysid + 1);
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

/* ===================================================
   浮動視窗拖曳邏輯 (Draggable Floating Window)
   =================================================== */
function makeDraggable(elmnt, header) {
    let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;

    if (header) {
        // 如果有傳入 header，則只有點擊 header 才能拖曳
        header.onmousedown = dragMouseDown;
    } else {
        elmnt.onmousedown = dragMouseDown;
    }

    function dragMouseDown(e) {
        e = e || window.event;

        // 修正：如果視窗尚未被拖曳過（存在 transform 置中屬性），
        // 必須先鎖定它當前畫面上的真實絕對座標，然後再把 transform 移除，否則一拖曳就會往右下方瞬間閃現 (偏移 50% 的自身寬高)。
        if (window.getComputedStyle(elmnt).transform !== 'none') {
            const rect = elmnt.getBoundingClientRect();
            elmnt.style.transform = 'none';
            elmnt.style.left = rect.left + 'px';
            elmnt.style.top = rect.top + 'px';
        }

        // 取消原生的反白與拖曳行為
        e.preventDefault();

        // 取得滑鼠按下時的初始位置
        pos3 = e.clientX;
        pos4 = e.clientY;
        document.onmouseup = closeDragElement;
        // 綁定滑鼠移動事件
        document.onmousemove = elementDrag;
    }

    function elementDrag(e) {
        e = e || window.event;
        e.preventDefault();
        // 計算游標的新位置
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;

        // 設定元素的新位置
        let newTop = elmnt.offsetTop - pos2;
        let newLeft = elmnt.offsetLeft - pos1;

        // 防止防出螢幕上方
        if (newTop < 0) newTop = 0;

        elmnt.style.top = newTop + "px";
        elmnt.style.left = newLeft + "px";
    }

    function closeDragElement() {
        // 釋放滑鼠按鈕時停止移動
        document.onmouseup = null;
        document.onmousemove = null;
    }
}

// 初始化拖曳功能
document.addEventListener('DOMContentLoaded', () => {
    const modalEl = document.getElementById("tick-stream-modal");
    const headerEl = document.getElementById("modal-drag-header");
    if (modalEl && headerEl) {
        makeDraggable(modalEl, headerEl);
    }

    // Alert Modal
    const alertModalEl = document.getElementById("alert-modal");
    const alertHeaderEl = document.getElementById("alert-drag-header");
    if (alertModalEl && alertHeaderEl) {
        makeDraggable(alertModalEl, alertHeaderEl);
    }
});
