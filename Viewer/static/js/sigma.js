// sigma.js
// 處理 Sigma & VIX 差異總表的資料載入與 UI 渲染

let currentSigmaData = [];

async function loadSigmaDiff() {
    const dateSelect = document.getElementById("date-selector");
    const date = dateSelect ? dateSelect.value : null;
    if (!date) {
        alert("請先選擇日期");
        return;
    }

    const errorDiv = document.getElementById("sigma-error");
    const tbody = document.getElementById("sigma-tbody");
    errorDiv.style.display = "none";
    tbody.innerHTML = '<tr><td colspan="14">資料載入中，請稍候...</td></tr>';

    try {
        const response = await fetch(`/api/sigma_diff?date=${date}`);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        currentSigmaData = data.rows || [];
        renderSigmaTable();
    } catch (err) {
        console.error("載入 Sigma 比對失敗:", err);
        errorDiv.textContent = `載入失敗: ${err.message}`;
        errorDiv.style.display = "block";
        tbody.innerHTML = '<tr><td colspan="14" style="color:red;">載入失敗</td></tr>';
    }
}

function renderSigmaTable() {
    const tbody = document.getElementById("sigma-tbody");
    const diffOnly = document.getElementById("sigma-diff-only").checked;

    if (!currentSigmaData || currentSigmaData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="14">沒有找到比對資料</td></tr>';
        return;
    }

    let html = "";

    // 容許誤差值
    const SIGMA_TOLERANCE = 1e-6;
    const VIX_TOLERANCE = 0.01;

    currentSigmaData.forEach(row => {
        // 取得 Diff，為 null 時當作有差異字串處理
        const nearDiff = row.nearSigma2_diff;
        const nextDiff = row.nextSigma2_diff;
        const vixDiff = row.vix_diff;
        const oriVixDiff = row.ori_vix_diff;

        let hasNearDiff = nearDiff !== null && Math.abs(nearDiff) > SIGMA_TOLERANCE;
        let hasNextDiff = nextDiff !== null && Math.abs(nextDiff) > SIGMA_TOLERANCE;
        let hasVixDiff = vixDiff !== null && Math.abs(vixDiff) > VIX_TOLERANCE;
        let hasOriVixDiff = oriVixDiff !== null && Math.abs(oriVixDiff) > VIX_TOLERANCE;

        // Type 不合也算有差異
        let hasNearTypeDiff = row.nearType_prod !== row.nearType_my;
        let hasNextTypeDiff = row.nextType_prod !== row.nextType_my;

        const isRowDiff = hasNearDiff || hasNextDiff || hasVixDiff || hasOriVixDiff || hasNearTypeDiff || hasNextTypeDiff;

        // 如果開啟「只看差異」且此列沒有差異，則跳過
        if (diffOnly && !isRowDiff) {
            return;
        }

        const formatVal = (val, dec) => val !== null ? Number(val).toFixed(dec) : "-";

        // 幫數字上色
        const diffStyle = (isDiff) => isDiff ? 'style="background-color: #ffcccc;"' : '';
        const typeStyle = (isDiff) => isDiff ? 'style="color: red; font-weight: bold;"' : '';

        html += `
            <tr style="border-bottom: 1px solid #eee;">
                <td>${row.time}</td>
                <!-- Near Sigma2 -->
                <td>${formatVal(row.nearSigma2_prod, 8)}</td>
                <td>${formatVal(row.nearSigma2_my, 8)}</td>
                <td ${diffStyle(hasNearDiff)}>${formatVal(nearDiff, 8)}</td>
                <!-- Next Sigma2 -->
                <td>${formatVal(row.nextSigma2_prod, 8)}</td>
                <td>${formatVal(row.nextSigma2_my, 8)}</td>
                <td ${diffStyle(hasNextDiff)}>${formatVal(nextDiff, 8)}</td>
                <!-- ORI VIX -->
                <td>${formatVal(row.ori_vix_prod, 4)}</td>
                <td>${formatVal(row.ori_vix_my, 4)}</td>
                <td ${diffStyle(hasOriVixDiff)}>${formatVal(oriVixDiff, 4)}</td>
                <!-- VIX -->
                <td>${formatVal(row.vix_prod, 4)}</td>
                <td>${formatVal(row.vix_my, 4)}</td>
                <td ${diffStyle(hasVixDiff)}>${formatVal(vixDiff, 4)}</td>
                <!-- Type -->
                <td ${typeStyle(hasNearTypeDiff)}>${row.nearType_prod || '-'} | ${row.nearType_my || '-'}</td>
                <td ${typeStyle(hasNextTypeDiff)}>${row.nextType_prod || '-'} | ${row.nextType_my || '-'}</td>
            </tr>
        `;
    });

    if (html === "") {
        html = '<tr><td colspan="14" style="color: green; padding: 20px;">🎉 恭喜！目前沒有發現任何超過容許誤差的差異。</td></tr>';
    }

    tbody.innerHTML = html;
}
