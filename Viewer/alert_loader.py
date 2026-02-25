import os
import glob
import re
import pandas as pd

class AlertLoader:
    """讀取與解析資料來源/Alert 目錄下產生的 Alert Report TSV"""
    
    def __init__(self, source_dir):
        self.alert_dir = os.path.join(source_dir, "Alert")
        
    def get_alerts_by_date(self, date):
        """讀取指定日期所有的 Alert Reports，並回傳解析後的 JSON 結構列表"""
        if not os.path.exists(self.alert_dir):
            return []
            
        pattern = os.path.join(self.alert_dir, f"{date}_alert_report.*.tsv")
        files = glob.glob(pattern)
        
        alerts = []
        for f in files:
            # 從檔名解析出時間 HHMMSS
            match = re.search(r'_alert_report\.(\d{6})\.tsv$', f)
            if not match:
                continue
            
            time_str = match.group(1)
            time_display = f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
            
            parsed = self._parse_alert_file(f, time_str, time_display)
            if parsed:
                alerts.append(parsed)
                
        # 依照時間排序
        alerts.sort(key=lambda x: x["time"])
        return alerts

    def _parse_alert_file(self, filepath, time_str, time_display):
        """解析單一 Alert 檔案的三大區塊: Header / Summary / Contributions"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            if not lines:
                return None
                
            # 尋找 Summary 區塊 (date, time, nearT...) 的起點
            summary_header_idx = -1
            for i, line in enumerate(lines):
                if line.startswith("date\ttime\tnearT"):
                    summary_header_idx = i
                    break
                    
            if summary_header_idx == -1:
                return None
                
            # --- 解析區塊 A: Header (觸發條件) ---
            trigger_line = lines[1].strip() if len(lines) > 1 else ""
            conditions = []
            if "triggered by condition" in trigger_line:
                cond_str = trigger_line.split("triggered by condition")[1].strip()
                conditions = [int(c.strip()) for c in cond_str.split('&') if c.strip().isdigit()]
                
            # 建立 condition 對照字典 (Line 3 ~ summary_header_idx前一行的空白行)
            condition_desc = {}
            for i in range(2, summary_header_idx):
                line = lines[i].strip()
                if line.startswith("condition"):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        num = int(parts[0].replace("condition", ""))
                        condition_desc[str(num)] = parts[1].strip()
                        
            # --- 解析區塊 B: Summary (前一筆與當前筆 VIX 摘要) ---
            # Line + 1 是 prev, Line + 2 是 current
            summary_data = {"prev": {}, "current": {}}
            if len(lines) > summary_header_idx + 2:
                headers = [h.strip() for h in lines[summary_header_idx].split('\t')]
                prev_vals = [v.strip() for v in lines[summary_header_idx+1].split('\t')]
                curr_vals = [v.strip() for v in lines[summary_header_idx+2].split('\t')]
                
                # 對應前端預期的欄位名稱
                key_map = {
                    'nearSigma^2': 'nearSigma2',
                    'No of nearSeries': 'nearSeriesCount',
                    'nextSigma^2': 'nextSigma2',
                    'No of nextSeries': 'nextSeriesCount'
                }
                
                def _map_row(vals):
                    row_dict = {}
                    for i, h in enumerate(headers):
                        if i < len(vals) and vals[i] != '':
                            k = key_map.get(h, h)
                            row_dict[k] = vals[i]
                    return row_dict
                    
                summary_data["prev"] = _map_row(prev_vals)
                summary_data["current"] = _map_row(curr_vals)
                
            # --- 解析區塊 C: Contributions 明細 ---
            # 尋找 "month\ttime\tmoneyness..." 行
            contrib_header_idx = -1
            for i in range(summary_header_idx + 3, len(lines)):
                if lines[i].startswith("month\ttime\tmoneyness"):
                    contrib_header_idx = i
                    break
                    
            contributions = {"Near": [], "Next": []}
            if contrib_header_idx != -1:
                # 讀取剩餘表格，因左右不平衡，手動解析
                c_headers = [h.strip() for h in lines[contrib_header_idx].split('\t')]
                
                # 判斷 Near / Next 依據
                all_months = set()
                rows = []
                for i in range(contrib_header_idx + 1, len(lines)):
                    line = lines[i].rstrip('\n')
                    if not line:
                        continue
                    vals = line.split('\t')
                    month = vals[0]
                    rows.append(vals)
                    if month.isdigit():
                        all_months.add(int(month))
                        
                sorted_months = sorted(list(all_months))
                near_month = str(sorted_months[0]) if sorted_months else None
                next_month = str(sorted_months[1]) if len(sorted_months) > 1 else None
                
                for vals in rows:
                    if len(vals) < 8:
                        continue
                        
                    month = vals[0]
                    # 左側資料 (必定存在)
                    strike = vals[3]
                    moneyness = vals[2].strip()
                    prev_mid = vals[4]
                    prev_spread_ratio = vals[5]
                    prev_contrib = vals[6]
                    prev_weight = vals[7]
                    
                    # 決定 term
                    term = "Near" if month == near_month else ("Next" if month == next_month else None)
                    if not term:
                        continue
                        
                    # 檢查右側是否有資料 (len >= 17)
                    if len(vals) >= 17 and vals[8].strip() != "":
                        # 有變化
                        curr_mid = vals[11]
                        curr_spread_ratio = vals[12]
                        curr_contrib = vals[13]
                        curr_weight = vals[14]
                        weight_diff = vals[15]
                        contrib_diff_pct = vals[16].rstrip('\n')
                    else:
                        # 無變化，顯示空白 (依據使用者要求)
                        curr_mid = ""
                        curr_spread_ratio = ""
                        curr_contrib = ""
                        curr_weight = ""
                        weight_diff = ""
                        contrib_diff_pct = ""
                        
                    # 只有保留「右側有資料」或是「有顯示的序列」，為減少 payload 大小
                    # 依據 spec，我們需要高亮「有變化」的，所以保留 diff 相關欄位
                    item = {
                        "strike": strike,
                        "moneyness": moneyness,
                        "prev_mid": prev_mid,
                        "prev_spread_ratio": prev_spread_ratio,
                        "prev_contrib": prev_contrib,
                        "prev_weight": prev_weight,
                        "curr_mid": curr_mid,
                        "curr_spread_ratio": curr_spread_ratio,
                        "curr_contrib": curr_contrib,
                        "curr_weight": curr_weight,
                        "weight_diff": weight_diff,
                        "contrib_diff_pct": contrib_diff_pct,
                        # 一個標記，讓前端好判斷是否要高亮
                        "has_changed": len(vals) >= 17 and vals[8].strip() != ""
                    }
                    contributions[term].append(item)
                    
            # 依照 contrib_diff_pct 絕對值大小排序
            def _sort_key(item):
                pct_str = item["contrib_diff_pct"].replace("%", "") if item["contrib_diff_pct"] else "0"
                try:
                    return abs(float(pct_str))
                except:
                    return 0
                    
            contributions["Near"].sort(key=_sort_key, reverse=True)
            contributions["Next"].sort(key=_sort_key, reverse=True)

            return {
                "time": time_str,
                "time_display": time_display,
                "triggered_conditions": conditions,
                "condition_descriptions": condition_desc,
                "summary": summary_data,
                "contributions": contributions
            }
        except Exception as e:
            print(f"解析 Alert 檔案時發生錯誤 {filepath}: {str(e)}")
            return None
