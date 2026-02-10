import pandas as pd
import numpy as np
import glob
import os
import sys
from datetime import datetime, timedelta

class DataPathManager:
    """
    負責管理資料來源路徑 (Configuration of Data Paths)
    
    功能：
    1. 指定 Raw Data 與 Prod Data 的基礎目錄 (Base Directory)
    2. 根據目標日期 (Target Date) 自動尋找對應的資料夾
    """
    def __init__(self, raw_base_dir="資料來源", prod_base_dir="資料來源"):
        """
        Args:
            raw_base_dir: 原始 Tick 資料的基礎目錄 (預設: "資料來源")
            prod_base_dir: PROD 驗證資料的基礎目錄 (預設: "資料來源")
        """
        # 處理相對路徑，確保從專案根目錄開始
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.raw_base_dir = os.path.join(self.project_root, raw_base_dir)
        self.prod_base_dir = os.path.join(self.project_root, prod_base_dir)
        
    def resolve_raw_path(self, target_date):
        """
        解析原始資料路徑
        邏輯：在 raw_base_dir 中搜尋包含 target_date 的資料夾
        
        Args:
            target_date: 目標日期字串 (e.g., "20251231")
            
        Returns:
            str: 找到的原始資料目錄路徑
        """
        if not os.path.exists(self.raw_base_dir):
            raise FileNotFoundError(f"找不到基礎目錄: {self.raw_base_dir}")
            
        # 搜尋模式：包含日期的資料夾
        pattern = os.path.join(self.raw_base_dir, f"*{target_date}*")
        all_candidates = [d for d in glob.glob(pattern) if os.path.isdir(d)]
        
        if not all_candidates:
            raise FileNotFoundError(f"在 {self.raw_base_dir} 中找不到包含 {target_date} 的資料夾")
            
        # 過濾掉完全等於 target_date 的資料夾 (因為那是 PROD 資料夾的命名慣例)
        candidates = [d for d in all_candidates if os.path.basename(d) != target_date]
        
        # 如果過濾後沒了，就只好用原本的 (可能 raw folder 真的就是那個名字，或者沒有分)
        if not candidates:
            candidates = all_candidates
            
        # 若有多個，優先選擇長度最長或最短？
        # 目前假設只有一個匹配，若有多個則取第一個並印出警告
        if len(candidates) > 1:
            print(f"警告: 找到多個符合 {target_date} 的原始資料夾，使用第一個: {os.path.basename(candidates[0])}")
            print(f"候選列表: {[os.path.basename(d) for d in candidates]}")
            
        # 特別處理：如果資料夾內有 temp 子目錄（目前結構），則指向 temp
        # 根據這幾次的結構: J002.../temp/*.csv
        target_dir = candidates[0]
        temp_dir = os.path.join(target_dir, "temp")
        if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
            return temp_dir
            
        return target_dir

    def resolve_prod_path(self, target_date):
        """
        解析 PROD 資料路徑
        邏輯：在 prod_base_dir 中尋找名稱完全符合 target_date 的資料夾
        
        Args:
            target_date: 目標日期字串 (e.g., "20251231")
            
        Returns:
            str: 找到的 PROD 資料目錄路徑
        """
        if not os.path.exists(self.prod_base_dir):
            raise FileNotFoundError(f"找不到基礎目錄: {self.prod_base_dir}")
            
        # 直接路徑匹配
        target_dir = os.path.join(self.prod_base_dir, target_date)
        
        if not os.path.exists(target_dir):
            # 嘗試模糊搜尋? 暫時不，PROD 通常路徑較固定
            raise FileNotFoundError(f"找不到 PROD 資料夾: {target_dir}")
            
        return target_dir


class RawDataLoader:
    """負責讀取與初步處理原始 Tick 資料"""
    def __init__(self, raw_dir, target_date):
        self.raw_dir = raw_dir
        self.target_date = target_date
        
    def load_and_filter(self):
        # 1. 搜尋所有 CSV
        all_files = glob.glob(os.path.join(self.raw_dir, "*.csv"))
        if not all_files:
            print(f"錯誤: 找不到 CSV 檔案於 {self.raw_dir}")
            return None, None, None
            
        print(f"找到 {len(all_files)} 個原始檔案，開始讀取...")
        
        df_list = []
        for f in all_files:
            try:
                # 只讀取必要欄位以節省記憶體
                # 假設欄位順序: Date(0), Prod(1), Time(2), Bid(3), Ask(4), Seq(5)
                # 需根據 check 檔案確認
                # 根據之前 check_product_id_parsing.py:
                # Header: svel_i081_yymmdd, svel_i081_prod_id, svel_i081_time, svel_i081_best_buy_price1, svel_i081_best_sell_price1, svel_i081_seqno
                
                chunk = pd.read_csv(f)
                
                # 欄位重新命名方便處理
                chunk.columns = [c.strip() for c in chunk.columns]
                
                # 日期過濾
                chunk = chunk[chunk['svel_i081_yymmdd'].astype(str) == self.target_date]
                
                df_list.append(chunk)
            except Exception as e:
                print(f"讀取 {os.path.basename(f)} 失敗: {e}")
                
        if not df_list:
            return None, None, None
            
        full_df = pd.concat(df_list, ignore_index=True)
        print(f"總資料筆數: {len(full_df)}")
        
        # 2. 解析商品代號 (Product ID Parsing)
        # 格式: TXO + 履約價(5碼) + 月份碼(2碼)
        # 例如: TXO15800A6
        
        def parse_prod(pid):
            pid = pid.strip()
            if len(pid) < 10: return None, None, None
            
            # 判斷是否為 TXO (前3碼)
            if not pid.startswith("TXO"): return None, None, None
            
            # 判斷是否為週選 (第4碼) - 標準依照 A, B, C... 
            # 假設第4碼若為數字或特殊代碼則為週選?
            # 根據 spec: 第4碼 'A'-'Z' 為非週選 (雖然 A6 的 A 是 Call Month)
            # 修正: 結構 PP T AAAAA CC
            # TX O 15800 A6
            # PP=TX, T=O, AAAAA=15800, CC=A6
            
            strike_str = pid[3:8]
            term_code = pid[8:] # A6
            
            try:
                strike = int(strike_str)
            except:
                return None, None, None
                
            return strike, term_code, "TXO"

        # 應用解析
        parsed = full_df['svel_i081_prod_id'].apply(parse_prod)
        
        # 將 tuple 拆分
        full_df['Strike'] = parsed.apply(lambda x: x[0] if x else None)
        full_df['TermCode'] = parsed.apply(lambda x: x[1] if x else None)
        full_df['Type'] = parsed.apply(lambda x: x[2] if x else None)
        
        # 過濾無效解析
        full_df = full_df.dropna(subset=['Strike']).copy()
        
        # 3. 判斷 Call/Put 與 月份
        # C1: A-L = Call Jan-Dec
        #     M-X = Put Jan-Dec
        
        code_map = {
            'A':('Call', 1), 'B':('Call', 2), 'C':('Call', 3), 'D':('Call', 4), 'E':('Call', 5), 'F':('Call', 6),
            'G':('Call', 7), 'H':('Call', 8), 'I':('Call', 9), 'J':('Call', 10), 'K':('Call', 11), 'L':('Call', 12),
            'M':('Put', 1), 'N':('Put', 2), 'O':('Put', 3), 'P':('Put', 4), 'Q':('Put', 5), 'R':('Put', 6),
            'S':('Put', 7), 'T':('Put', 8), 'U':('Put', 9), 'V':('Put', 10), 'W':('Put', 11), 'X':('Put', 12)
        }
        
        def parse_cp_month(code):
            c1 = code[0] # 月份碼
            c2 = code[1] # 年份碼 (e.g. 6 -> 2026)
            
            if c1 not in code_map: return None, None, None
            
            cp, month = code_map[c1]
            
            # 年份處理: 假設資料為 2025/2026
            # 6 -> 2026, 5 -> 2025
            year = 2020 + int(c2) # 簡單用 202x
            
            ym = year * 100 + month
            return cp, ym
            
        cp_month = full_df['TermCode'].apply(parse_cp_month)
        full_df['CP'] = cp_month.apply(lambda x: x[0] if x else None)
        full_df['YM'] = cp_month.apply(lambda x: x[1] if x else None)
        
        full_df = full_df.dropna(subset=['CP']).copy()
        
        # 4. 區分 Near / Next Term
        # 找出所有出現的月份，排序
        unique_yms = sorted(full_df['YM'].unique())
        print(f"找到的到期月份: {unique_yms}")
        
        if len(unique_yms) < 2:
            print("錯誤: 資料中不足兩個到期月份")
            return full_df, None, None
            
        near_ym = unique_yms[0]
        next_ym = unique_yms[1]
        
        print(f"動態判斷結果: 近月(Near)={near_ym}, 次近月(Next)={next_ym}")
        
        near_df = full_df[full_df['YM'] == near_ym].copy()
        next_df = full_df[full_df['YM'] == next_ym].copy()
        
        # 預先處理 datetime 提升效能
        near_df['temp_datetime'] = pd.to_datetime(near_df['svel_i081_time'].astype(str).str.zfill(12), format='%H%M%S%f')
        next_df['temp_datetime'] = pd.to_datetime(next_df['svel_i081_time'].astype(str).str.zfill(12), format='%H%M%S%f')
        
        return near_df, next_df, (near_ym, next_ym)

class SnapshotScheduler:
    """負責讀取 PROD 排程檔與解析快照時間"""
    def __init__(self, prod_path):
        self.prod_path = prod_path
        
    def load_schedule(self):
        # 讀取 PROD 檔
        # 需要 Line 2 的 Time/SysID
        # 以及 Line 3+ 的 Time/SysID (去重)
        
        snapshots = []
        
        with open(self.prod_path, 'r', encoding='utf-8') as f:
            header = f.readline() # Line 1
            start_row = f.readline().strip().split('\t') # Line 2
            
            # Line 2: start_time, start_sys_id
            # 格式: 84500 (HHMMSS) or 84500000000? -> 通常是 simplified
            # 觀察 NearPROD: 84500	22934	...
            
            t_str = start_row[0]
            if len(t_str) == 5: t_str = "0" + t_str # 84500 -> 084500
            t_full = t_str.ljust(12, '0') # padding to microseconds if needed
            
            snapshots.append({
                'orig_time_str': t_str, # Keep original string for matching
                'time_obj': datetime.strptime(t_full[:6], "%H%M%S").replace(year=2025, month=12, day=31), # Mock date
                'sys_id': int(start_row[1])
            })
            
            # Line 3+
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) < 2: continue
                
                # Check for duplicate times? The file has many rows per time (one per strike)
                # We want unique Times
                t_val = parts[1] # Time column
                # SysID? PROD columns 12/13/18?
                # 根據先前的 grep: Last col is snapshot_sysID
                # 14745778
                
                # 我們假設檔案最後一欄是 snapshot_sysID
                # 但為了精確，我們應該用之前 grep 看到的 header index
                # 但為求簡化，我們只紀錄唯一的時間點
                pass # 我們改用讀取 dataframe 方式比較快且不重複?
                
        # 上面的 loop 太慢且複雜，改用 pandas read csv 只讀 time, snapshot_sysID (last col)
        # 用 header 判斷
        df = pd.read_csv(self.prod_path, sep='\t', header=0)
        # Line 2 is actually data in pandas? No, header=0 reads line 1 as header.
        # Check header names
        # Headers: date time ... ... sysID
        # We want to extract unique (Time, sysID) pairs
        
        # 為了更準確，我們直接讀取並去重
        # 注意: PROD 檔案第一列是 header, 第二列是 start info, 第三列開始是 data
        # Pandas 可能會把第二列當 data 讀入，導致 type error
        
        # 手動處理比較穩
        schedule_data = {} # Time -> SysID
        
        # Add Line 2 manually
        schedule_data[snapshots[0]['orig_time_str']] = snapshots[0]['sys_id']
        
        with open(self.prod_path, 'r', encoding='utf-8') as f:
            f.readline() # Header
            f.readline() # Line 2
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) > 1:
                    t = parts[1]
                    # SysID is usually the last one or close to end.
                    # Based on user check: 14745778 is at the end.
                    sysid = int(parts[-1]) 
                    schedule_data[t] = sysid
                    
        # Convert to list
        final_list = []
        for t, sid in schedule_data.items():
            t_pad = t.zfill(6)
            final_list.append({
                'orig_time_str': t,
                'time_obj': datetime.strptime(t_pad, "%H%M%S").replace(year=2025, month=12, day=31),
                'sys_id': sid
            })
            
        return pd.DataFrame(final_list)
