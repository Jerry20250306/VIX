"""
Step 0 步驟一：獲取序列有效報價 (Valid Quote 資訊)
依據附錄 3 實作有效性檢查並產生稽核報表
"""
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# 載入重建好的快照資料 (使用 reconstruct_order_book.py 的類別)
sys.path.insert(0, os.path.dirname(__file__))
from reconstruct_order_book import RawDataLoader, SnapshotScheduler, SnapshotReconstructor

def check_valid_quote(bid, ask):
    """
    檢查報價是否符合「有效報價 (Valid Quote)」條件
    
    條件：
    1. 買價、賣價須為數字
    2. 買價 >= 0
    3. 賣價 > 買價
    
    Returns:
        (is_valid: bool, reason: str)
    """
    # 檢查 1: 是否為數字
    try:
        bid_val = float(bid)
        ask_val = float(ask)
    except (ValueError, TypeError):
        return False, "Bid或Ask非數值"
    
    # 檢查 2: Bid >= 0
    if bid_val < 0:
        return False, f"Bid({bid_val}) < 0"
    
    # 檢查 3: Ask > Bid
    if ask_val <= bid_val:
        return False, f"Ask({ask_val}) <= Bid({bid_val})"
    
    return True, "符合有效報價條件"

def generate_integrated_html_report(all_results, target_date, output_path):
    """
    產生整合的互動式 HTML 報表
    
    Args:
        all_results: 字典格式 {'Near': [...], 'Next': [...]}
                    每個 list 包含多個時間點的資料 {'time': str, 'sys_id': str, 'data': DataFrame}
        target_date: 目標日期字串
        output_path: 輸出檔案路徑
    """
    # HTML 模板開始
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VIX 整合報表 - {target_date}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: "Microsoft JhengHei", "微軟正黑體", Arial, sans-serif;
            background-color: #f5f5f5;
            padding: 20px;
        }}
        
        h1 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 3px solid #4CAF50;
        }}
        
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }}
        
        .tab-button {{
            padding: 12px 24px;
            border: none;
            background-color: #e0e0e0;
            color: #333;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            border-radius: 5px 5px 0 0;
            transition: all 0.3s;
        }}
        
        .tab-button:hover {{
            background-color: #d0d0d0;
        }}
        
        .tab-button.active {{
            background-color: #4CAF50;
            color: white;
        }}
        
        .term-content {{
            display: none;
            background-color: white;
            padding: 20px;
            border-radius: 0 5px 5px 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .term-content.active {{
            display: block;
        }}
        
        .cp-tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 5px;
        }}
        
        .cp-button {{
            padding: 10px 20px;
            border: 2px solid #4CAF50;
            background-color: white;
            color: #4CAF50;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            border-radius: 5px;
            transition: all 0.3s;
        }}
        
        .cp-button:hover {{
            background-color: #e8f5e9;
        }}
        
        .cp-button.active {{
            background-color: #4CAF50;
            color: white;
        }}
        
        .time-selector {{
            margin: 15px 0;
            padding: 15px;
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 5px;
        }}
        
        .time-selector label {{
            font-weight: bold;
            margin-right: 10px;
        }}
        
        .time-selector select {{
            padding: 8px 12px;
            font-size: 14px;
            border: 1px solid #ddd;
            border-radius: 3px;
            cursor: pointer;
        }}
        
        .cp-content {{
            display: none;
        }}
        
        .cp-content.active {{
            display: block;
        }}
        
        .summary {{
            background-color: #f9f9f9;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            border-left: 4px solid #4CAF50;
        }}
        
        .summary h3 {{
            color: #4CAF50;
            margin-bottom: 10px;
        }}
        
        .summary p {{
            margin: 5px 0;
            line-height: 1.6;
        }}
        
        .warning {{
            background-color: #fff3cd;
            border-left-color: #ffc107;
        }}
        
        .warning h3 {{
            color: #856404;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-top: 20px;
            font-size: 13px;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        th {{
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
            padding: 10px 6px;
            text-align: left;
            position: sticky;
            top: 0;
            z-index: 10;
            white-space: nowrap;
        }}
        
        td {{
            padding: 6px;
            border-bottom: 1px solid #ddd;
            white-space: nowrap;
        }}
        
        tr:hover {{
            background-color: #f5f5f5;
        }}
        
        .invalid-row {{
            background-color: #ffcccc !important;
        }}
        
        .valid {{
            color: green;
            font-weight: bold;
        }}
        
        .invalid {{
            color: red;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <h1>VIX 整合有效性報表 - {target_date}</h1>
    
    <div class="tabs">
        <button class="tab-button active" onclick="switchTerm('Near')">近月 (Near)</button>
        <button class="tab-button" onclick="switchTerm('Next')">次近月 (Next)</button>
    </div>
"""
    
    # 為每個 Term 建立內容
    for term_idx, (term_name, term_results) in enumerate(all_results.items()):
        is_active = "active" if term_idx == 0 else ""
        
        html_content += f"""
    <div id="{term_name}" class="term-content {is_active}">
        <h2>{term_name} Term</h2>
        
        <div class="time-selector">
            <label for="{term_name}-time-select">選擇時間點:</label>
            <select id="{term_name}-time-select" onchange="switchTime('{term_name}', this.value)">
"""
        
        for time_data in term_results:
            html_content += f'                <option value="{time_data["time"]}">{time_data["time"]}</option>\n'
        
        html_content += """            </select>
        </div>
"""
        
        # 為每個時間點建立內容
        for time_idx, time_data in enumerate(term_results):
            time_str = time_data['time']
            sys_id = time_data['sys_id']
            df = time_data['data']
            
            is_time_active = "active" if time_idx == 0 else ""
            
            call_df = df[df['CP'] == 'C'].copy()
            put_df = df[df['CP'] == 'P'].copy()
            
            total = len(df)
            q_last_valid = df['Q_last_Valid'].sum()
            q_min_valid = df['Q_min_Valid'].sum()
            invalid_count = len(df[(~df['Q_last_Valid']) | (~df['Q_min_Valid'])])
            
            html_content += f"""
        <div id="{term_name}-{time_str}" class="time-content {is_time_active}">
            <div class="summary{' warning' if invalid_count > 0 else ''}">
                <h3>時間點: {time_str} (SysID: {sys_id})</h3>
                <p><strong>總序列數:</strong> {total}</p>
                <p><strong>Q_last 有效:</strong> {q_last_valid} ({q_last_valid/total*100:.1f}%)</p>
                <p><strong>Q_min 有效:</strong> {q_min_valid} ({q_min_valid/total*100:.1f}%)</p>
"""
            if invalid_count > 0:
                html_content += f'                <p style="color: #d32f2f; font-weight: bold;">⚠️ 發現 {invalid_count} 筆無效報價</p>\n'
            
            html_content += """            </div>
            
            <div class="cp-tabs">
                <button class="cp-button active" onclick="switchCP('""" + term_name + """', '""" + time_str + """', 'Call')">Call Options</button>
                <button class="cp-button" onclick="switchCP('""" + term_name + """', '""" + time_str + """', 'Put')">Put Options</button>
            </div>
"""
            
            html_content += f"""
            <div id="{term_name}-{time_str}-Call" class="cp-content active">
                <h4>Call Options ({len(call_df)} 筆)</h4>
"""
            html_content += _generate_table_html(call_df)
            html_content += """            </div>
"""
            
            html_content += f"""
            <div id="{term_name}-{time_str}-Put" class="cp-content">
                <h4>Put Options ({len(put_df)} 筆)</h4>
"""
            html_content += _generate_table_html(put_df)
            html_content += """            </div>
        </div>
"""
        
        html_content += """    </div>
"""
    
    html_content += """
    <script>
        function switchTerm(termName) {
            const allTerms = document.querySelectorAll('.term-content');
            allTerms.forEach(term => term.classList.remove('active'));
            
            const allButtons = document.querySelectorAll('.tab-button');
            allButtons.forEach(btn => btn.classList.remove('active'));
            
            document.getElementById(termName).classList.add('active');
            event.target.classList.add('active');
        }
        
        function switchTime(termName, timeStr) {
            const allTimeContents = document.querySelectorAll(`#${termName} .time-content`);
            allTimeContents.forEach(content => content.classList.remove('active'));
            
            const targetContent = document.getElementById(`${termName}-${timeStr}`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        }
        
        function switchCP(termName, timeStr, cpType) {
            const containerId = `${termName}-${timeStr}`;
            const container = document.getElementById(containerId);
            
            const cpButtons = container.querySelectorAll('.cp-button');
            cpButtons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            
            const cpContents = container.querySelectorAll('.cp-content');
            cpContents.forEach(content => content.classList.remove('active'));
            
            const targetContent = document.getElementById(`${containerId}-${cpType}`);
            if (targetContent) {
                targetContent.classList.add('active');
            }
        }
    </script>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def _generate_table_html(df):
    """產生表格 HTML（輔助函式）"""
    if len(df) == 0:
        return '                <p>無資料</p>\n'
    
    html = '                <table>\n'
    html += '                    <thead>\n                        <tr>\n'
    
    for col in df.columns:
        html += f'                            <th>{col}</th>\n'
    
    html += '                        </tr>\n                    </thead>\n'
    html += '                    <tbody>\n'
    
    for _, row in df.iterrows():
        is_invalid = not row['Q_last_Valid'] or not row['Q_min_Valid']
        row_class = ' class="invalid-row"' if is_invalid else ''
        
        html += f'                        <tr{row_class}>\n'
        
        for col in df.columns:
            value = row[col]
            
            if col in ['Q_last_Valid', 'Q_min_Valid']:
                if value:
                    cell_content = '<span class="valid">True</span>'
                else:
                    cell_content = '<span class="invalid">False</span>'
            elif pd.isna(value):
                cell_content = ''
            elif isinstance(value, (int, np.integer)):
                cell_content = str(value)
            elif isinstance(value, (float, np.floating)):
                cell_content = f'{value:.1f}'
            else:
                cell_content = str(value)
            
            html += f'                            <td>{cell_content}</td>\n'
        
        html += '                        </tr>\n'
    
    html += '                    </tbody>\n'
    html += '                </table>\n'
    
    return html


def generate_validity_report(snapshot_df, term_name, target_time, snapshot_sysid, output_path):
    """
    產生有效性檢查報表
    
    Args:
        snapshot_df: 重建的快照資料 (包含 My_Last_Bid, My_Last_Ask 等欄位)
        term_name: 'Near' or 'Next'
        target_time: 快照時間 (例如 '120015')
        snapshot_sysid: 該時間區間對應的 Snapshot SysID
        output_path: 報表輸出路徑
    """
    # 建立報表 DataFrame
    report_rows = []
    
    for _, row in snapshot_df.iterrows():
        strike = row['Strike']
        cp = row['CP']
        
        # 取得候選報價
        q_last_bid = row['My_Last_Bid']
        q_last_ask = row['My_Last_Ask']
        q_last_sysid = row['My_Last_SysID']
        q_last_time = row['My_Last_Time']
        
        q_min_bid = row['My_Min_Bid']
        q_min_ask = row['My_Min_Ask']
        q_min_spread = row['My_Min_Spread']
        
        # 檢查 Q_last 有效性
        q_last_valid, q_last_reason = check_valid_quote(q_last_bid, q_last_ask)
        
        # 檢查 Q_min 有效性
        q_min_valid, q_min_reason = check_valid_quote(q_min_bid, q_min_ask)
        
        # 計算 Q_Last_Valid 欄位（僅在有效時計算）
        if q_last_valid:
            q_last_valid_bid = q_last_bid
            q_last_valid_ask = q_last_ask
            q_last_valid_spread = q_last_ask - q_last_bid
            q_last_valid_mid = (q_last_bid + q_last_ask) / 2
        else:
            q_last_valid_bid = "null"
            q_last_valid_ask = "null"
            q_last_valid_spread = "null"
            q_last_valid_mid = "null"
        
        # 計算 Q_Min_Valid 欄位（僅在有效時計算）
        if q_min_valid:
            q_min_valid_bid = q_min_bid
            q_min_valid_ask = q_min_ask
            q_min_valid_spread = q_min_ask - q_min_bid
            q_min_valid_mid = (q_min_bid + q_min_ask) / 2
        else:
            q_min_valid_bid = "null"
            q_min_valid_ask = "null"
            q_min_valid_spread = "null"
            q_min_valid_mid = "null"

        
        # 組成報表列
        report_rows.append({
            'Term': term_name,
            'Time': target_time,
            'Snapshot_SysID': snapshot_sysid,
            'Strike': strike,
            'CP': cp,
            
            # Q_last 原始資訊
            'Q_last_Bid': q_last_bid,
            'Q_last_Ask': q_last_ask,
            'Q_last_Spread': q_last_ask - q_last_bid if pd.notna(q_last_bid) and pd.notna(q_last_ask) else np.nan,
            'Q_last_SysID': q_last_sysid,
            'Q_last_Time': q_last_time,
            'Q_last_Valid': q_last_valid,
            'Q_last_Reason': q_last_reason,
            
            # Q_Last_Valid 欄位（步驟二使用，僅有效時有值）
            'Q_Last_Valid_Bid': q_last_valid_bid,
            'Q_Last_Valid_Ask': q_last_valid_ask,
            'Q_Last_Valid_Spread': q_last_valid_spread,
            'Q_Last_Valid_Mid': q_last_valid_mid,
            
            # Q_min 原始資訊 (15秒內最小價差)
            'Q_min_Bid': q_min_bid,
            'Q_min_Ask': q_min_ask,
            'Q_min_Spread': q_min_spread,
            'Q_min_Valid': q_min_valid,
            'Q_min_Reason': q_min_reason,
            
            # Q_Min_Valid 欄位（步驟二使用，僅有效時有值）
            'Q_Min_Valid_Bid': q_min_valid_bid,
            'Q_Min_Valid_Ask': q_min_valid_ask,
            'Q_Min_Valid_Spread': q_min_valid_spread,
            'Q_Min_Valid_Mid': q_min_valid_mid,
        })
    
    report_df = pd.DataFrame(report_rows)
    
    # 儲存 CSV 報表
    report_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    # 儲存 HTML 報表
    html_path = output_path.replace('.csv', '.html')
    
    # 產生 HTML（包含自訂 CSS）
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>有效報價驗證報表 - {term_name} {target_time}</title>
    <style>
        body {{
            font-family: "Microsoft JhengHei", "微軟正黑體", Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .summary {{
            background-color: #fff;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary h2 {{
            margin-top: 0;
            color: #4CAF50;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-top: 20px;
            font-size: 13px;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
            padding: 10px 6px;
            text-align: left;
            position: sticky;
            top: 0;
            z-index: 10;
            white-space: nowrap;
        }}
        td {{
            padding: 6px;
            border-bottom: 1px solid #ddd;
            white-space: nowrap;
        }}
        tr:hover {{
            background-color: #f1f1f1;
        }}
        .invalid-row {{
            background-color: #ffcccc;
        }}
        .valid {{
            color: green;
            font-weight: bold;
        }}
        .invalid {{
            color: red;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <h1>有效報價驗證報表</h1>
    <div class="summary">
        <h2>摘要資訊</h2>
        <p><strong>Term:</strong> {term_name}</p>
        <p><strong>時間:</strong> {target_time}</p>
        <p><strong>Snapshot SysID:</strong> {snapshot_sysid}</p>
        <p><strong>總序列數:</strong> {len(report_df)}</p>
        <p><strong>Q_last 有效數:</strong> {report_df['Q_last_Valid'].sum()} ({report_df['Q_last_Valid'].sum()/len(report_df)*100:.1f}%)</p>
        <p><strong>Q_min 有效數:</strong> {report_df['Q_min_Valid'].sum()} ({report_df['Q_min_Valid'].sum()/len(report_df)*100:.1f}%)</p>
    </div>
    <table>
        <thead>
            <tr>
"""
    
    # 加入表頭
    for col in report_df.columns:
        html_content += f"                <th>{col}</th>\n"
    
    html_content += """            </tr>
        </thead>
        <tbody>
"""
    
    # 加入資料列
    for _, row in report_df.iterrows():
        # 判斷是否為無效列
        row_class = ""
        if not row['Q_last_Valid'] or not row['Q_min_Valid']:
            row_class = ' class="invalid-row"'
        
        html_content += f"            <tr{row_class}>\n"
        
        for col in report_df.columns:
            value = row[col]
            
            # 格式化特殊欄位
            if col in ['Q_last_Valid', 'Q_min_Valid']:
                if value:
                    cell_content = '<span class="valid">True</span>'
                else:
                    cell_content = '<span class="invalid">False</span>'
            elif pd.isna(value):
                cell_content = ''
            elif isinstance(value, (int, np.integer)):
                cell_content = str(value)
            elif isinstance(value, (float, np.floating)):
                cell_content = f'{value:.1f}'
            else:
                cell_content = str(value)
            
            html_content += f"                <td>{cell_content}</td>\n"
        
        html_content += "            </tr>\n"
    
    html_content += """        </tbody>
    </table>
</body>
</html>
"""
    
    # 寫入 HTML 檔案
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"HTML 報表已儲存至: {html_path}")

    
    # 列印統計
    total = len(report_df)
    q_last_valid_count = report_df['Q_last_Valid'].sum()
    q_min_valid_count = report_df['Q_min_Valid'].sum()
    
    print(f"\n=== {term_name} Term 有效性檢查統計 ===")
    print(f"總序列數: {total}")
    print(f"Q_last 有效數: {q_last_valid_count} ({q_last_valid_count/total*100:.1f}%)")
    print(f"Q_min 有效數: {q_min_valid_count} ({q_min_valid_count/total*100:.1f}%)")
    
    # 列印不符合範例
    invalid_last = report_df[~report_df['Q_last_Valid']]
    if len(invalid_last) > 0:
        print(f"\nQ_last 不符合範例 (前5筆):")
        print(invalid_last[['Strike', 'CP', 'Q_last_Bid', 'Q_last_Ask', 'Q_last_Reason']].head().to_string(index=False))
    
    invalid_min = report_df[~report_df['Q_min_Valid']]
    if len(invalid_min) > 0:
        print(f"\nQ_min 不符合範例 (前5筆):")
        print(invalid_min[['Strike', 'CP', 'Q_min_Bid', 'Q_min_Ask', 'Q_min_Reason']].head().to_string(index=False))
    
    print(f"\n完整報表已儲存至: {output_path}")
    
    return report_df

def main(process_all_times=False, target_time=None, end_time=None, max_time_points=None):
    """執行 Step 0 步驟一：獲取序列有效報價
    
    Args:
        process_all_times: 處理全天所有時間點（預設 False）
        target_time: 處理單一時間點（格式: "HHMMSS"）
        end_time: 處理從第一筆到指定時間點（格式: "HHMMSS"）
        max_time_points: 限制處理的時間點數量（用於測試，例如: 5 表示只處理前5個時間點）
        
    執行模式：
        1. process_all_times=True: 處理所有時間點，忽略其他參數
        2. max_time_points=N: 處理前 N 個時間點（測試用）
        3. end_time="HHMMSS": 處理從第一個時間點到 end_time（包含）
        4. target_time="HHMMSS": 只處理單一時間點（預設 "120015"）
    """
    # 設定參數
    raw_dir = r"c:\AGY\VIX\VIX\資料來源\J002-11300041_20251231\temp"
    prod_dir = r"c:\AGY\VIX\VIX\資料來源\20251231"
    target_date = "20251231"
    
    # 決定處理模式
    if process_all_times:
        mode = "全天處理"
        print(f"=== Step 0 步驟一：獲取序列有效報價 (全天處理) ===")
    elif max_time_points:
        mode = "測試處理"
        print(f"=== Step 0 步驟一：獲取序列有效報價 (測試：前{max_time_points}個時間點) ===")
    elif end_time:
        mode = "範圍處理"
        print(f"=== Step 0 步驟一：獲取序列有效報價 (範圍處理：第一筆 → {end_time}) ===")
    else:
        mode = "單一時間點"
        if target_time is None:
            target_time = "120015"
        print(f"=== Step 0 步驟一：獲取序列有效報價 (單一時間點) ===")
        print(f"目標時間: {target_time}")
    
    
    
    # 1. 載入原始資料
    print("\n>>> 載入原始 Ticks...")
    loader = RawDataLoader(raw_dir, target_date)
    near_ticks, next_ticks, terms = loader.load_and_filter()
    
    if near_ticks is None:
        print("錯誤: 無法載入資料")
        return
    
    # 2. 定義驗證任務
    tasks = [
        ('Near', near_ticks, f"NearPROD_{target_date}.tsv"),
        ('Next', next_ticks, f"NextPROD_{target_date}.tsv")
    ]
    
    # 用於儲存所有時間點的結果（供整合 HTML 使用）
    all_results = {}
    
    # 3. 對每個 Term 執行重建與驗證
    for term_name, ticks, prod_filename in tasks:
        print(f"\n>>> 處理 {term_name} Term")
        prod_path = os.path.join(prod_dir, prod_filename)
        
        # 載入排程
        scheduler = SnapshotScheduler(prod_path)
        schedule = scheduler.load_schedule()
        
        if process_all_times or end_time or max_time_points:
            # 處理多個時間點（全天、範圍或測試）
            time_points = schedule['orig_time_str'].tolist()
            
            # 根據不同模式篩選時間點
            if max_time_points:
                # 測試模式：只處理前 N 個時間點
                time_points = time_points[:max_time_points]
                print(f"  測試模式：處理前 {max_time_points} 個時間點")
                print(f"  時間範圍: {time_points[0]} → {time_points[-1]}")
            elif end_time:
                # 範圍模式：處理到 end_time
                if end_time in time_points:
                    end_idx = time_points.index(end_time) + 1
                    time_points = time_points[:end_idx]
                    print(f"  範圍處理：第一筆 ({time_points[0]}) → {end_time}")
                else:
                    print(f"  警告: 找不到時間點 {end_time}，處理所有時間點")
            
            print(f"  共 {len(time_points)} 個時間點")
            
            term_results = []
            all_reports = []  # 儲存所有時間點的報表 DataFrame
            
            for idx, time_str in enumerate(time_points, 1):
                target_row = schedule[schedule['orig_time_str'] == time_str].iloc[0]
                t_obj = target_row['time_obj']
                sys_id = target_row['sys_id']
                
                print(f"  處理 {idx}/{len(time_points)}: {time_str} (SysID={sys_id})")
                
                # 重建快照
                reconstructor = SnapshotReconstructor(ticks)
                snapshot = reconstructor.reconstruct_at(t_obj, sys_id)
                
                # 產生報表資料（但不輸出個別 CSV）
                # 建立報表 DataFrame
                report_rows = []
                for _, row in snapshot.iterrows():
                    strike = row['Strike']
                    cp = row['CP']
                    
                    q_last_bid = row['My_Last_Bid']
                    q_last_ask = row['My_Last_Ask']
                    q_last_sysid = row['My_Last_SysID']
                    q_last_time = row['My_Last_Time']
                    
                    q_min_bid = row['My_Min_Bid']
                    q_min_ask = row['My_Min_Ask']
                    q_min_spread = row['My_Min_Spread']
                    
                    
                    q_last_valid, q_last_reason = check_valid_quote(q_last_bid, q_last_ask)
                    q_min_valid, q_min_reason = check_valid_quote(q_min_bid, q_min_ask)
                    
                    # 計算 Q_Last_Valid 欄位
                    if q_last_valid:
                        q_last_valid_bid = q_last_bid
                        q_last_valid_ask = q_last_ask
                        q_last_valid_spread = q_last_ask - q_last_bid
                        q_last_valid_mid = (q_last_bid + q_last_ask) / 2
                    else:
                        q_last_valid_bid = "null"
                        q_last_valid_ask = "null"
                        q_last_valid_spread = "null"
                        q_last_valid_mid = "null"
                    
                    # 計算 Q_Min_Valid 欄位
                    if q_min_valid:
                        q_min_valid_bid = q_min_bid
                        q_min_valid_ask = q_min_ask
                        q_min_valid_spread = q_min_ask - q_min_bid
                        q_min_valid_mid = (q_min_bid + q_min_ask) / 2
                    else:
                        q_min_valid_bid = "null"
                        q_min_valid_ask = "null"
                        q_min_valid_spread = "null"
                        q_min_valid_mid = "null"

                    
                    report_rows.append({
                        'Term': term_name,
                        'Time': time_str,
                        'Snapshot_SysID': sys_id,
                        'Strike': strike,
                        'CP': cp,
                        'Q_last_Bid': q_last_bid,
                        'Q_last_Ask': q_last_ask,
                        'Q_last_Spread': q_last_ask - q_last_bid if pd.notna(q_last_bid) and pd.notna(q_last_ask) else np.nan,
                        'Q_last_SysID': q_last_sysid,
                        'Q_last_Time': q_last_time,
                        'Q_last_Valid': q_last_valid,
                        'Q_last_Reason': q_last_reason,
                        'Q_Last_Valid_Bid': q_last_valid_bid,
                        'Q_Last_Valid_Ask': q_last_valid_ask,
                        'Q_Last_Valid_Spread': q_last_valid_spread,
                        'Q_Last_Valid_Mid': q_last_valid_mid,
                        'Q_min_Bid': q_min_bid,
                        'Q_min_Ask': q_min_ask,
                        'Q_min_Spread': q_min_spread,
                        'Q_min_Valid': q_min_valid,
                        'Q_min_Reason': q_min_reason,
                        'Q_Min_Valid_Bid': q_min_valid_bid,
                        'Q_Min_Valid_Ask': q_min_valid_ask,
                        'Q_Min_Valid_Spread': q_min_valid_spread,
                        'Q_Min_Valid_Mid': q_min_valid_mid,
                    })
                
                report_df = pd.DataFrame(report_rows)
                all_reports.append(report_df)
                
                # 儲存結果（供 HTML 使用）
                term_results.append({
                    'time': time_str,
                    'sys_id': sys_id,
                    'data': report_df
                })
            
            # 合併所有時間點的報表為一個 CSV
            if all_reports:
                combined_df = pd.concat(all_reports, ignore_index=True)
                
                # 根據處理模式決定檔名
                if max_time_points:
                    csv_output = f"step0_1_valid_quotes_{term_name}_測試前{max_time_points}個.csv"
                elif end_time:
                    csv_output = f"step0_1_valid_quotes_{term_name}_範圍_{time_points[0]}至{end_time}.csv"
                else:
                    csv_output = f"step0_1_valid_quotes_{term_name}_全天.csv"
                
                combined_df.to_csv(csv_output, index=False, encoding='utf-8-sig')
                print(f"\n  {term_name} 整合 CSV 已儲存: {csv_output}")
                print(f"  總筆數: {len(combined_df)} (涵蓋 {len(time_points)} 個時間點)")
            
            all_results[term_name] = term_results
        else:
            # 處理單一時間點
            target_row = schedule[schedule['orig_time_str'] == target_time]
            
            if target_row.empty:
                print(f"  找不到時間點 {target_time}")
                continue
            
            t_obj = target_row.iloc[0]['time_obj']
            sys_id = target_row.iloc[0]['sys_id']
            print(f"  Snapshot Point: Time={target_time}, SysID={sys_id}")
            
            # 重建快照 (取得 Q_last 和 Q_latest)
            print("  重建委託簿快照...")
            reconstructor = SnapshotReconstructor(ticks)
            snapshot = reconstructor.reconstruct_at(t_obj, sys_id)
            
            print(f"  重建完成，共 {len(snapshot)} 筆序列")
            
            # 產生有效性報表
            output_path = f"step0_1_valid_quotes_{term_name}_{target_time}.csv"
            generate_validity_report(snapshot, term_name, target_time, sys_id, output_path)
    
    # 4. 如果是多時間點處理（全天、範圍或測試），產生整合 HTML 報表
    if (process_all_times or end_time or max_time_points) and all_results:
        print("\n>>> 產生整合 HTML 報表...")
        integrated_output = f"step0_1_integrated_report_{target_date}.html"
        generate_integrated_html_report(all_results, target_date, integrated_output)
        print(f"整合報表已儲存至: {integrated_output}")

if __name__ == "__main__":
    # 全天處理
    main(process_all_times=True)
    
    # 其他測試模式：
    # main(max_time_points=1)            # 測試第1個時間點
    # main(process_all_times=True)       # 全天處理
    # main(end_time="120015")            # 範圍處理：第一筆到 120015
    # main(target_time="120015")         # 單一時間點
    # main()                             # 預設：單一時間點 120015


