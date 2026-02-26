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

    def query(self, date, term, strike, cp, sys_id, prev_sys_id=None,
              curr_start=None, curr_end=None, prev_start=None, prev_end=None):
        """查詢 Tick 資料。
        若提供 curr_start/curr_end/prev_start/prev_end，則以手動指定範圍篩選；
        否則使用預設邏輯 (prev_sys_id < seqno <= sys_id)。
        """
        try:
            tick_dir = self._find_tick_dir(date)
            # 確保找到正確的 csv 目錄 (有的在 temp)
            if not glob.glob(os.path.join(tick_dir, "*.csv")):
                tick_dir = os.path.join(tick_dir, "temp")

            month, year_digit = self._determine_month_and_year(date, term)
            prod_id = self._build_prod_id(strike, cp, month, year_digit)
            
            # 找檔名符合的 CSV
            tick_file = None
            code = CALL_MONTH_CODES[month] if cp.capitalize() == "Call" else PUT_MONTH_CODES[month]
            pattern = os.path.join(tick_dir, f"*TXO{code}{year_digit}.csv")
            files = glob.glob(pattern)
            if files:
                tick_file = files[0]
            
            if not tick_file:
                return {"error": f"找不到 Tick 檔 (TXO*{year_digit}.csv)", "prod_id": prod_id}

            current_ticks = []
            prev_ticks = []
            
            # 參數處理
            sys_id = int(float(sys_id)) if sys_id else 0
            prev_sys_id = int(float(prev_sys_id)) if prev_sys_id else None
            
            # 手動指定範圍 (覆蓋預設邏輯)
            if curr_start is not None:
                curr_start = int(float(curr_start))
            if curr_end is not None:
                curr_end = int(float(curr_end))
            if prev_start is not None:
                prev_start = int(float(prev_start))
            if prev_end is not None:
                prev_end = int(float(prev_end))
            
            # 決定最終的篩選範圍
            # 當前區間
            final_curr_start = curr_start if curr_start is not None else (prev_sys_id if prev_sys_id else 0)
            final_curr_end = curr_end if curr_end is not None else sys_id
            # 前一區間
            final_prev_start = prev_start if prev_start is not None else ((prev_sys_id - 500) if prev_sys_id else None)
            final_prev_end = prev_end if prev_end is not None else prev_sys_id
            
            # 讀取 CSV (TSV)
            chunk_iter = pd.read_csv(tick_file, sep="\t", chunksize=100000, encoding="utf-8", engine="c")
            
            for chunk in chunk_iter:
                chunk.columns = [c.strip() for c in chunk.columns]
                
                # 簡易欄位識別
                id_col = next((c for c in chunk.columns if 'prod_id' in c), None)
                seq_col = next((c for c in chunk.columns if 'seqno' in c), None)
                time_col = next((c for c in chunk.columns if 'time' in c), None)
                bid_col = next((c for c in chunk.columns if 'buy_price' in c or 'best_bid' in c), None)
                ask_col = next((c for c in chunk.columns if 'sell_price' in c or 'best_ask' in c), None)
                
                if not (id_col and seq_col): continue

                # 篩選 prod_id
                chunk[id_col] = chunk[id_col].astype(str).str.strip()
                matched = chunk[chunk[id_col] == prod_id].copy()
                if matched.empty: continue
                
                # 篩選 seqno
                matched[seq_col] = pd.to_numeric(matched[seq_col], errors='coerce')
                
                # Current Interval: (final_curr_start, final_curr_end]
                curr_mask = (matched[seq_col] > final_curr_start) & (matched[seq_col] <= final_curr_end)
                if curr_mask.any():
                    for _, row in matched[curr_mask].iterrows():
                        current_ticks.append(self._format_row(row, time_col, bid_col, ask_col, seq_col))
                
                # Prev Interval: (final_prev_start, final_prev_end]
                if final_prev_start is not None and final_prev_end is not None:
                    prev_mask = (matched[seq_col] > final_prev_start) & (matched[seq_col] <= final_prev_end)
                    if prev_mask.any():
                        for _, row in matched[prev_mask].iterrows():
                            prev_ticks.append(self._format_row(row, time_col, bid_col, ask_col, seq_col))
            
            return {
                "prod_id": prod_id,
                "current_interval": {
                    "sys_id_range": [final_curr_start, final_curr_end],
                    "ticks": sorted(current_ticks, key=lambda x: x["seqno"]),
                    "count": len(current_ticks)
                },
                "prev_interval": {
                    "sys_id_range": [final_prev_start, final_prev_end],
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
                disp = f"{t[0:1]}:{t[1:3]}:{t[3:5]}.{t[5:8]}"
            else:
                disp = f"{t[0:2]}:{t[2:4]}:{t[4:6]}.{t[6:9]}"
        
        bid = float(row[bid_col]) if bid_col and pd.notnull(row[bid_col]) else 0
        ask = float(row[ask_col]) if ask_col and pd.notnull(row[ask_col]) else 0
        return {
            "time": t,
            "time_display": disp,
            "bid": bid,
            "ask": ask,
            "seqno": int(row[seq_col])
        }

    # ===================================================================
    # 連續河流查詢（探勘面板用）
    # ===================================================================


    def query_stream(self, date, term, strike, cp,
                     sysid_map,
                     center_sysid, lookback=1, lookforward=1,
                     prepend_sysid=None, append_sysid=None):
        """連續河流查詢

        參數:
            sysid_map   : {time_int: snapshot_sysID} 字典（由 ProdLoader.build_sysid_map() 提供）
            center_sysid: 目標 Snapshot 的 SysID
            lookback    : 在 center_sysid 之前載入幾個區間 (預設 1)
            lookforward : 在 center_sysid 之後載入幾個區間 (預設 1)
            prepend_sysid: 指定更早的起始 SysID（用於「載入更早」擴充）
            append_sysid : 指定更晚的結束 SysID（用於「載入更晚」擴充）

        回傳:
            {
              "prod_id": "TXO22000X5",
              "ticks": [...],
              "snapshots": [...],
              "range": [min_sysid, max_sysid]
            }
        """
        try:
            tick_dir = self._find_tick_dir(date)
            if not glob.glob(os.path.join(tick_dir, "*.csv")):
                tick_dir = os.path.join(tick_dir, "temp")

            month, year_digit = self._determine_month_and_year(date, term)
            prod_id = self._build_prod_id(strike, cp, month, year_digit)

            # 找 Tick 檔
            tick_file = None
            code = CALL_MONTH_CODES[month] if cp.capitalize() == "Call" else PUT_MONTH_CODES[month]
            pattern = os.path.join(tick_dir, f"*TXO{code}{year_digit}.csv")
            files = glob.glob(pattern)
            if files:
                tick_file = files[0]

            if not tick_file:
                return {"error": f"找不到 Tick 檔", "prod_id": prod_id,
                        "ticks": [], "snapshots": [], "range": [0, 0]}

            # 建立已排序的 Snapshot 清單（sysid 升序）
            sorted_snaps = sorted(sysid_map.items(), key=lambda x: x[1])  # [(time_int, sysid), ...]
            snap_sysids  = [s[1] for s in sorted_snaps]

            # ---------------------------------------------------------------
            # 動態 Anchor 定位：
            #   - prepend_sysid → 找最接近的 snap 作為右邊界，往前擴 lookback+lookforward 個區間
            #   - append_sysid  → 找最接近的 snap 作為左邊界，往後擴 lookback+lookforward 個區間
            #   - 否則以 center_sysid 為中心
            # ---------------------------------------------------------------
            total_req_intervals = int(lookback) + int(lookforward)
            
            if prepend_sysid is not None:
                # 找不超過 prepend_sysid 的最後一個 snap 作為右邊界
                anchor_idx = 0
                for i, s in enumerate(snap_sysids):
                    if s <= prepend_sysid:
                        anchor_idx = i
                    else:
                        break
                end_idx   = anchor_idx
                start_idx = max(0, end_idx - total_req_intervals)
            elif append_sysid is not None:
                # 找不小於 append_sysid 的第一個 snap 作為左邊界
                anchor_idx = len(snap_sysids) - 1
                for i, s in enumerate(snap_sysids):
                    if s >= append_sysid:
                        anchor_idx = i
                        break
                start_idx = anchor_idx
                end_idx   = min(len(sorted_snaps) - 1, start_idx + total_req_intervals)
            else:
                # 一般搜尋：以 center_sysid 為基準
                try:
                    center_idx = snap_sysids.index(center_sysid)
                except ValueError:
                    center_idx = min(range(len(snap_sysids)),
                                     key=lambda i: abs(snap_sysids[i] - center_sysid))
                
                # 這裡是核心優化：如果 lookforward=0，則當前 snapshot 就是視窗的結束
                start_idx = max(0, center_idx - int(lookback))
                end_idx   = min(len(sorted_snaps) - 1, center_idx + int(lookforward))

            # 本次視窗的實際 SysID 範圍（以 snap 邊界對齊）
            range_start_sysid = (
                sorted_snaps[start_idx - 1][1] if start_idx > 0 else 0
            )
            range_end_sysid = sorted_snaps[end_idx][1]

            # 收集本次載入的 Snapshots（供前端插入金色分界線）
            snapshots = [
                {"time_int": t, "sysid": s}
                for t, s in sorted_snaps[start_idx:end_idx + 1]
            ]

            # 區間陣列：[start_idx : end_idx+1]，每個 snap 是該 15s 區間的右邊界
            interval_snaps = sorted_snaps[start_idx:end_idx + 1]

            # 一次性讀入、公用檔案內所有 matched
            all_matched = []
            for chunk in pd.read_csv(tick_file, sep="\t", chunksize=100000,
                                     encoding="utf-8", engine="c"):
                chunk.columns = [c.strip() for c in chunk.columns]
                id_col  = next((c for c in chunk.columns if 'prod_id' in c), None)
                seq_col = next((c for c in chunk.columns if 'seqno' in c), None)
                time_col= next((c for c in chunk.columns if 'time' in c and 'yymmdd' not in c), None)
                bid_col = next((c for c in chunk.columns if 'buy_price' in c or 'best_bid' in c), None)
                ask_col = next((c for c in chunk.columns if 'sell_price' in c or 'best_ask' in c), None)

                if not (id_col and seq_col): continue

                chunk[id_col] = chunk[id_col].astype(str).str.strip()
                matched = chunk[chunk[id_col] == prod_id].copy()
                if matched.empty: continue

                matched[seq_col] = pd.to_numeric(matched[seq_col], errors='coerce')
                # 只保留範圍內的資料
                in_range = matched[
                    (matched[seq_col] > range_start_sysid) &
                    (matched[seq_col] <= range_end_sysid)
                ].copy()

                for _, row in in_range.iterrows():
                    bid = float(row[bid_col]) if bid_col and pd.notnull(row[bid_col]) else 0.0
                    ask = float(row[ask_col]) if ask_col and pd.notnull(row[ask_col]) else 0.0
                    seqno = int(row[seq_col])
                    t = str(row[time_col]).strip()

                    # 結構化資料
                    base = self._format_row(row, time_col, bid_col, ask_col, seq_col)
                    base["interval_idx"] = self._find_interval(seqno, interval_snaps, range_start_sysid)
                    all_matched.append(base)

            all_matched.sort(key=lambda x: x["seqno"])

            # 對每個區間標記 LAST / MIN
            # 先按 interval_idx 分組
            from collections import defaultdict
            by_interval = defaultdict(list)
            for tick in all_matched:
                by_interval[tick["interval_idx"]].append(tick)

            for iidx, ticks in by_interval.items():
                # 判斷各筆 valid/invalid、錯誤碼
                for tk in ticks:
                    tk["is_valid"], tk["error_codes"] = self._check_valid(tk["bid"], tk["ask"])
                    tk["tags"] = []

                valid_ticks = [tk for tk in ticks if tk["is_valid"]]

                # LAST = 這個區間內 seqno 最大的有效報價
                if valid_ticks:
                    last_tick = max(valid_ticks, key=lambda x: x["seqno"])
                    last_tick["tags"].append("LAST")

                    # MIN = spread 最小的有效報價
                    min_tick = min(valid_ticks, key=lambda x: x["ask"] - x["bid"])
                    min_tick["tags"].append("MIN")

            # 剛再清除 interval_idx (UI 不需要)
            for tk in all_matched:
                tk.pop("interval_idx", None)

            return {
                "prod_id": prod_id,
                "ticks": all_matched,
                "snapshots": snapshots,
                "range": [range_start_sysid, range_end_sysid]
            }

        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e), "ticks": [], "snapshots": [], "range": [0, 0]}

    def _find_interval(self, seqno, interval_snaps, range_start_sysid):
        """回傳 seqno 屬於哪個區間索引
        區間 0: (range_start_sysid, interval_snaps[0].sysid]
        區間 1: (interval_snaps[0].sysid, interval_snaps[1].sysid]
        以此類推
        """
        prev = range_start_sysid
        for i, (t, s) in enumerate(interval_snaps):
            if prev < seqno <= s:
                return i
            prev = s
        return len(interval_snaps) - 1

    def _check_valid(self, bid, ask):
        """判斷一筆 Tick 是否為有效報價 (Valid Quote)
        對齊計算引擎 step0_valid_quotes.py 的 check_valid_quote 邏輯：
          1. 買價、賣價須為數字 (上游 _format_row 已處理)
          2. 買價 >= 0
          3. 賣價 > 買價
        
        E1: Bid < 0
        E2: Ask ≤ Bid (包含 Ask=0 且 Bid=0 的情況)
        """
        error_codes = []
        if bid < 0:
            error_codes.append("E1")
        if ask <= bid:
            error_codes.append("E2")
        is_valid = len(error_codes) == 0
        return is_valid, error_codes
