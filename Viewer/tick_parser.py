import pandas as pd
import os
import glob
import re

# 月份代碼對照表
CALL_MONTH_CODES = {1:'A', 2:'B', 3:'C', 4:'D', 5:'E', 6:'F',
                    7:'G', 8:'H', 9:'I', 10:'J', 11:'K', 12:'L'}
PUT_MONTH_CODES  = {1:'M', 2:'N', 3:'O', 4:'P', 5:'Q', 6:'R',
                    7:'S', 8:'T', 9:'U', 10:'V', 11:'W', 12:'X'}

class TickLoader:
    
    def __init__(self, source_dir):
        self.source_dir = source_dir
    
    def _find_tick_dir(self, date):
        # 尋找 J002*_{date}/temp 目錄
        pattern = os.path.join(self.source_dir, f"J002*_{date}", "temp")
        candidates = glob.glob(pattern)
        if not candidates:
            # 有些環境可能是在根目錄或其他結構，這裡假設規格書路徑正確
            # 但為了容錯，也可以試試看如果不加 temp
            pattern_no_temp = os.path.join(self.source_dir, f"J002*_{date}")
            candidates_no_temp = glob.glob(pattern_no_temp)
            if candidates_no_temp:
                 # 如果找到了但裡面沒有 temp，可能是直接放 csv?
                 # 不過先遵守規格: .../temp/*.csv
                 return candidates_no_temp[0] # 暫時回傳這層試試
                 
            raise FileNotFoundError(f"找不到 Tick 資料目錄 (J002*_{date}/temp)")
        return candidates[0]

    def _determine_month_and_year(self, date, term):
        """根據日期和 Near/Next，決定到期月份和年份"""
        tick_dir = self._find_tick_dir(date)
        tick_files = glob.glob(os.path.join(tick_dir, "*.csv"))
        if not tick_files:
             # 試試看子目錄 temp
             tick_files = glob.glob(os.path.join(tick_dir, "temp", "*.csv"))
        
        ym_set = set()
        for f in tick_files:
            basename = os.path.basename(f)
            # 格式: ...TXO{月份碼}{年碼}.csv
            match = re.search(r'TXO([A-X])(\d)\.csv', basename)
            if match:
                code_char = match.group(1)
                year_digit = match.group(2)
                
                all_codes = {**{v: k for k, v in CALL_MONTH_CODES.items()},
                             **{v: k for k, v in PUT_MONTH_CODES.items()}}
                             
                if code_char in all_codes:
                    month = all_codes[code_char]
                    year = 2020 + int(year_digit)
                    ym = year * 100 + month
                    ym_set.add((ym, month, year_digit))
        
        unique_yms = sorted(list(ym_set), key=lambda x: x[0])
        
        target = None
        if term == "Near":
            target = unique_yms[0] if unique_yms else None
        elif term == "Next":
            target = unique_yms[1] if len(unique_yms) > 1 else None
            
        if not target:
            raise ValueError(f"無法判斷 {term} 的到期月份 (可用: {unique_yms})")
        
        return target[1], target[2] # month, year_digit

    def _build_prod_id(self, strike, cp, month, year_digit):
        if cp == "Call":
            month_code = CALL_MONTH_CODES[month]
        else:
            month_code = PUT_MONTH_CODES[month]
        return f"TXO{strike}{month_code}{year_digit}"

    def query(self, date, term, strike, cp, sys_id, prev_sys_id=None):
        try:
            tick_dir = self._find_tick_dir(date)
            # 確保找到正確的 csv 目錄 (有的在 temp)
            if not glob.glob(os.path.join(tick_dir, "*.csv")):
                tick_dir = os.path.join(tick_dir, "temp")

            month, year_digit = self._determine_month_and_year(date, term)
            prod_id = self._build_prod_id(strike, cp, month, year_digit)
            
            # 找檔名符合的 CSV
            tick_file = None
            # 需搜尋 Call 或 Put 月份碼
            codes_to_search = [CALL_MONTH_CODES[month], PUT_MONTH_CODES[month]]
            
            for code in codes_to_search:
                pattern = os.path.join(tick_dir, f"*TXO{code}{year_digit}.csv")
                files = glob.glob(pattern)
                if files:
                    tick_file = files[0]
                    break
            
            if not tick_file:
                return {"error": f"找不到 Tick 檔 (TXO*{year_digit}.csv)", "prod_id": prod_id}

            current_ticks = []
            prev_ticks = []
            
            # 參數處理
            sys_id = int(float(sys_id)) if sys_id else 0
            prev_sys_id = int(float(prev_sys_id)) if prev_sys_id else None
            
            # 讀取 CSV (TSV)
            chunk_iter = pd.read_csv(tick_file, sep="\t", chunksize=100000, encoding="utf-8", engine="c")
            
            for chunk in chunk_iter:
                chunk.columns = [c.strip() for c in chunk.columns]
                
                # 簡易欄位識別
                id_col = next((c for c in chunk.columns if 'prod_id' in c), None)
                seq_col = next((c for c in chunk.columns if 'seqno' in c), None)
                time_col = next((c for c in chunk.columns if 'time' in c), None)
                bid_col = next((c for c in chunk.columns if 'buy_price' in c or 'best_bid' in c), None) # 根據 spec 是 best_buy_price1
                ask_col = next((c for c in chunk.columns if 'sell_price' in c or 'best_ask' in c), None)
                
                if not (id_col and seq_col): continue

                # 篩選 prod_id
                chunk[id_col] = chunk[id_col].astype(str).str.strip()
                matched = chunk[chunk[id_col] == prod_id].copy()
                if matched.empty: continue
                
                # 篩選 seqno
                matched[seq_col] = pd.to_numeric(matched[seq_col], errors='coerce')
                
                # Current Interval
                if prev_sys_id:
                    curr_mask = (matched[seq_col] > prev_sys_id) & (matched[seq_col] <= sys_id)
                else:
                    curr_mask = (matched[seq_col] <= sys_id)
                
                if curr_mask.any():
                    for _, row in matched[curr_mask].iterrows():
                        current_ticks.append(self._format_row(row, time_col, bid_col, ask_col, seq_col))
                
                # Prev Interval (往前 500 seqno)
                if prev_sys_id:
                    prev_mask = (matched[seq_col] > (prev_sys_id - 500)) & (matched[seq_col] <= prev_sys_id)
                    if prev_mask.any():
                        for _, row in matched[prev_mask].iterrows():
                            prev_ticks.append(self._format_row(row, time_col, bid_col, ask_col, seq_col))
            
            return {
                "prod_id": prod_id,
                "current_interval": {
                    "sys_id_range": [prev_sys_id, sys_id],
                    "ticks": sorted(current_ticks, key=lambda x: x["seqno"]),
                    "count": len(current_ticks)
                },
                "prev_interval": {
                    "ticks": sorted(prev_ticks, key=lambda x: x["seqno"]),
                    "count": len(prev_ticks)
                }
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e), "prod_id": "Error"}

    def _format_row(self, row, time_col, bid_col, ask_col, seq_col):
        t = str(row[time_col]).strip()
        disp = t
        # 時間格式可能是: HMMSSMMM000 (11碼) 或 HHMMSSMMM000 (12碼)
        # 例: 84500107000 → 8:45:00.107, 134500107000 → 13:45:00.107
        if len(t) >= 11:
            if len(t) == 11:
                # H MM SS MMM 000
                disp = f"{t[0:1]}:{t[1:3]}:{t[3:5]}.{t[5:8]}"
            else:
                # HH MM SS MMM 000
                disp = f"{t[0:2]}:{t[2:4]}:{t[4:6]}.{t[6:9]}"
        
        return {
            "time": t,
            "time_display": disp,
            "bid": float(row[bid_col]) if bid_col and pd.notnull(row[bid_col]) else 0,
            "ask": float(row[ask_col]) if ask_col and pd.notnull(row[ask_col]) else 0,
            "seqno": int(row[seq_col])
        }
