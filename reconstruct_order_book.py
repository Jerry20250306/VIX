# -*- coding: utf-8 -*-
"""
VIX 委託簿重建程式 (Order Book Reconstruction)

本程式負責從原始 Tick 資料重建出符合 VIX 計算所需的「委託簿快照」(Snapshot)。
對應設計文件: order_book_reconstruction_design.md

主要功能：
1. 資料載入 (Data Ingestion): 讀取原始 CSV 行情檔。
2. 商品解析 (Product Parsing): 解析 Product ID，區分履約價、買賣權、到期年月。
3. 期限區分 (Term Separation): 動態判斷近月 (Near) 與次近月 (Next)。
4. 篩選機制 (Filtering): 根據 Snapshot SysID 回溯 15 秒尋找最佳價差報價。

作者: Antigravity Agent
日期: 2026/02/05
"""

import pandas as pd
import numpy as np
import glob
import os
import sys

# 設定 pandas 顯示選項，方便除錯
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

class ProductParser:
    """
    負責解析商品代號 (Product ID) 的類別。
    遵循規則: PP + T + AAAAA + CC (共 10 碼)
    """
    
    def __init__(self, target_product='TXO'):
        """
        初始化解析器。
        :param target_product: 目標商品代碼，預設為 'TXO' (台指選擇權)。
        """
        self.target_product = target_product
        # 建立月份代碼對應表
        # Call: A-L (1-12月)
        # Put: M-X (1-12月)
        self.call_month_map = {c: i+1 for i, c in enumerate("ABCDEFGHIJKL")}
        self.put_month_map = {c: i+1 for i, c in enumerate("MNOPQRSTUVWX")}
        
    def parse(self, prod_id):
        """
        解析單一商品代號。
        
        :param prod_id: 商品代號字串 (如 'TXO22400A6')
        :return: 字典，包含解析後的欄位 (Product, Strike, CP, Year, Month, YYYYMM)，若解析失敗返回 None。
        """
        try:
            prod_id = prod_id.strip()
            if len(prod_id) != 10:
                return None
            
            # 1. 拆解結構
            pp = prod_id[0:2]      # 商品代碼 (如 TX)
            t = prod_id[2]         # 類別 (O=標準)
            aaaaa = prod_id[3:8]   # 履約價 (如 22400)
            cc = prod_id[8:10]     # 年月碼 (如 A6)
            
            # 判斷是否為目標商品 (這裡先假設要是標準商品 'O')
            # 使用者需求: 只有 'O' 是標準商品，其他可能是週選或調整
            # 我們先只鎖定 'O' (標準月選)，除非未來需要納入週選
            product_code = pp + t
            if product_code != self.target_product:
                return None
                
            # 2. 解析履約價
            strike = int(aaaaa)
            
            # 3. 解析月份與買賣權
            month_code = cc[0]
            year_digit = cc[1]
            
            cp = None
            month = None
            
            if month_code in self.call_month_map:
                cp = 'Call'
                month = self.call_month_map[month_code]
            elif month_code in self.put_month_map:
                cp = 'Put'
                month = self.put_month_map[month_code]
            else:
                return None # 無效的月份代碼
                
            # 4. 解析年份 (特殊邏輯: 6 -> 2026)
            # 這裡我們採取簡單策略：預設為 2020 年代
            # 根據使用者指示: "年份6要對應為2026" (基於 20251231 資料)
            # 為了通用性，我們可以假設: 
            # 如果尾數 < 5 (如 0,1,2...), 且當前是 2025，可能是 2030? 
            # 但目前簡單處理：直接拼成 202x
            year = int("202" + year_digit)
            
            yyyymm = year * 100 + month
            
            return {
                'Product': product_code,
                'Strike': strike,
                'CP': cp,
                'Year': year,
                'Month': month,
                'YYYYMM': yyyymm,
                'ProdID': prod_id
            }
            
        except Exception:
            return None

class RawDataLoader:
    """
    負責讀取與前處理原始Tick資料的類別。
    """
    
    def __init__(self, raw_data_dir, target_date):
        """
        :param raw_data_dir: 原始 CSV 檔案所在的資料夾路徑。
        :param target_date: 目標交易日期字串 (如 '20251231')，用於嚴格過濾。
        """
        self.raw_data_dir = raw_data_dir
        self.target_date = str(target_date)
        self.parser = ProductParser()
        
    def load_and_filter(self):
        """
        執行讀取、篩選、並區分近月/次近月資料。
        :return: (near_df, next_df, term_info)
            - near_df: 近月合約的 Ticks DataFrame
            - next_df: 次近月合約的 Ticks DataFrame
            - term_info: 字典，紀錄判斷出的近月與次近月月份 (YYYYMM)
        """
        all_files = glob.glob(os.path.join(self.raw_data_dir, "*.csv"))
        if not all_files:
            print(f"錯誤: 在 {self.raw_data_dir} 找不到任何 CSV 檔案。")
            return None, None, None
            
        print(f"找到 {len(all_files)} 個原始資料檔，開始讀取...")
        
        df_list = []
        for f in all_files:
            print(f"讀取: {os.path.basename(f)}")
            try:
                # 僅讀取必要欄位以節省記憶體
                # 欄位依據: svel_i081_yymmdd, svel_i081_prod_id, svel_i081_time, 
                #          svel_i081_best_buy_price1, svel_i081_best_sell_price1, svel_i081_seqno
                # 嘗試使用 \t 分隔符號，若失敗則退回預設
                temp_df = pd.read_csv(f, sep='\t', dtype={
                    'svel_i081_yymmdd': str, 
                    'svel_i081_prod_id': str,
                    'svel_i081_time': str, # 保持字串以免前導零消失
                    'svel_i081_seqno': int
                })
                
                # 1. 嚴格日期檢查 (Strict Date Check)
                # 只保留日期與 target_date 完全一致的資料
                original_count = len(temp_df)
                temp_df = temp_df[temp_df['svel_i081_yymmdd'] == self.target_date]
                filtered_count = len(temp_df)
                
                if filtered_count < original_count:
                    print(f"  - 日期過濾: 剔除 {original_count - filtered_count} 筆非 {self.target_date} 的資料")
                
                # 去除商品代號的空白，以免影響 Parsing 與 Merging
                temp_df['svel_i081_prod_id'] = temp_df['svel_i081_prod_id'].str.strip()
                
                df_list.append(temp_df)
                
            except Exception as e:
                print(f"  - 讀取失敗: {e}")
        
        if not df_list:
            return None, None, None
            
        full_df = pd.concat(df_list, ignore_index=True)
        print(f"原始資料合併完成，共 {len(full_df)} 筆 Ticks。")
        
        # 2. 解析 Product ID 並增加欄位
        print("開始解析商品代號...")
        
        # 為了效能，我們對「唯一」的 ProdID 進行解析，再 Merge 回去
        unique_ids = full_df['svel_i081_prod_id'].unique()
        parsed_results = []
        
        for pid in unique_ids:
            res = self.parser.parse(pid)
            if res:
                parsed_results.append(res)
                
        # 轉成 DataFrame 方便 Merge
        meta_df = pd.DataFrame(parsed_results)
        
        if meta_df.empty:
            print("錯誤: 無法解析任何 Product ID。")
            return None, None, None

        # 將解析結果併回原始資料
        full_df = full_df.merge(meta_df, left_on='svel_i081_prod_id', right_on='ProdID', how='inner')
        print(f"商品解析完成，剩餘有效 Ticks: {len(full_df)}")
        
        # 3. 動態判斷 Near/Next Term (Dynamic Term Sorting)
        # 掃描所有出現的 YYYYMM，排序
        all_months = sorted(full_df['YYYYMM'].unique())
        print(f"偵測到的到期月份: {all_months}")
        
        if len(all_months) < 2:
            print("錯誤: 資料中不足兩個到期月份，無法區分近月與次近月。")
            return None, None, None
            
        near_term = all_months[0]
        next_term = all_months[1]
        
        term_info = {'Near': near_term, 'Next': next_term}
        print(f"動態判斷結果: 近月(Near)={near_term}, 次近月(Next)={next_term}")
        
        # 4. 分割資料
        near_df = full_df[full_df['YYYYMM'] == near_term].copy()
        next_df = full_df[full_df['YYYYMM'] == next_term].copy()
        
        # 建立索引以加速後續搜尋 (Strike, SeqNo)
        # 後續篩選邏輯: 找 Time/SeqNo <= Snapshot Time/SeqNo
        # 這裡我們主要依 sequence number 排序
        near_df.sort_values('svel_i081_seqno', inplace=True)
        next_df.sort_values('svel_i081_seqno', inplace=True)
        
        return near_df, next_df, term_info

        return near_df, next_df, term_info

class SnapshotScheduler:
    """
    負責讀取 PROD 檔案並建立快照排程 (Schedule)。
    """
    def __init__(self, prod_file_path):
        self.prod_file_path = prod_file_path
        
    def load_schedule(self):
        """
        讀取 NearPROD 或 NextPROD，提取 Snapshot 觸發點。
        
        :return: tuple (schedule_df, initial_sys_id)
            - schedule_df: DataFrame (columns: ['time_obj', 'sys_id', 'orig_time_str'])
            - initial_sys_id: Line 2 的 SysID (054500 的 Target_SysID)，作為計算 084515 的 prev_sys_id
        """
        if not os.path.exists(self.prod_file_path):
            print(f"錯誤: 找不到 PROD 檔案: {self.prod_file_path}")
            return pd.DataFrame(), 0
            
        print(f"讀取排程檔: {os.path.basename(self.prod_file_path)}")
        
        schedule_list = []
        initial_sys_id = 0  # Line 2 的 SysID，作為第一筆的 prev_sys_id
        
        with open(self.prod_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        if len(lines) < 2:
            return pd.DataFrame(), 0
            
        # 1. 處理 Line 2 特例 (054500 Start Row)
        # 格式: 84500 <tab> 22934
        # 這個 SysID 是計算第一筆 (084515) 時的 prev_sys_id
        line2_parts = lines[1].strip().split('\t')
        if len(line2_parts) >= 2:
            start_time_str = line2_parts[0].zfill(6) # 補零: 84500 -> 084500
            initial_sys_id = int(line2_parts[1])
            print(f"  初始 SysID (Line 2, {start_time_str}): {initial_sys_id}")
        
        # 2. 處理 Line 3+ 標準列
        # 抓取 Header 索引
        header_parts = lines[0].strip().split('\t')
        try:
            time_idx = header_parts.index('time')
            sys_id_idx = header_parts.index('snapshot_sysID')
        except ValueError:
            print("錯誤: PROD 檔缺少 time 或 snapshot_sysID 欄位")
            return pd.DataFrame(), initial_sys_id
            
        # 遍歷剩餘行數
        # 注意: PROD 檔是每個 Strike 一行，所以 Time/SysID 會重複
        # 我們需要去重 (Deduplicate)，只取每個時間點一次
        seen_times = set()
        if schedule_list:
            seen_times.add(schedule_list[0]['orig_time_str'])
            
        for line in lines[2:]:
            parts = line.strip().split('\t')
            if len(parts) <= max(time_idx, sys_id_idx):
                continue
                
            t_str = parts[time_idx].strip()
            # PROD 檔 Time 可能是 084515
            if t_str not in seen_times:
                s_id = int(parts[sys_id_idx])
                t_obj = datetime.strptime(t_str, "%H%M%S")
                
                schedule_list.append({
                    'time_obj': t_obj,
                    'sys_id': s_id,
                    'orig_time_str': t_str
                })
                seen_times.add(t_str)
                
        df = pd.DataFrame(schedule_list)
        print(f"排程載入完成，共 {len(df)} 個快照時間點。")
        return df, initial_sys_id

class SnapshotReconstructor:
    """
    核心類別：根據排程與原始 Ticks 重建委託簿。
    """
    def __init__(self, ticks_df):
        """
        :param ticks_df: 已過濾好 (Near 或 Next) 且已排序的 Raw Ticks DataFrame
        """
        self.ticks_df = ticks_df
        
    def reconstruct_at(self, target_time_obj, target_sys_id, prev_sys_id=0):
        """
        重建特定時間點的委託簿快照 (Dual Strategy)。
        
        ========================================================================
        【SeqNo 區間邏輯】(per-product, 每個商品獨立計算)
        ========================================================================
        
        區間定義：[prev_last_seq, target_last_seq]（兩端都包含）
        
        - prev_last_seq = 該商品在 SeqNo <= prev_sys_id 中的「最後一筆」的 SeqNo
        - target_last_seq = 該商品在 SeqNo <= target_sys_id 中的「最後一筆」的 SeqNo
        
        ========================================================================
        【舉例】
        ========================================================================
        
        假設某商品 TXO27000A6 有以下報價：
        
            SeqNo   Bid    Ask    Spread
            -----   ----   ----   ------
            20000   100    105    5
            25000   101    106    5       <-- prev_sys_id=22934 時，這筆 SeqNo > 22934
            35000   102    104    2       <-- 最小 Spread
            50000   103    108    5       <-- target_sys_id=57695 時的最後一筆
        
        情況 1: prev_sys_id=22934, target_sys_id=57695
        
            - prev_last_seq = 20000 (SeqNo <= 22934 的最後一筆)
            - target_last_seq = 50000 (SeqNo <= 57695 的最後一筆)
            - 區間 = [20000, 50000]，包含 4 筆報價
            - Q_Last = SeqNo 50000 (Bid=103, Ask=108)
            - Q_Min = SeqNo 35000 (Bid=102, Ask=104, Spread=2)
        
        情況 2: prev_sys_id=57695, target_sys_id=87592 (下一個時間點)
        
            - prev_last_seq = 50000 (SeqNo <= 57695 的最後一筆)
            - 如果 57695~87592 間沒有新報價，區間只有 SeqNo=50000 這一筆
            - Q_Last = Q_Min = 都是 SeqNo 50000 那筆
        
        ========================================================================
        
        策略 1: My_Last (Latest Quote)
            - 在區間 [prev_last_seq, target_last_seq] 內，取 SeqNo 最大的報價
            - 即 target_last_seq 那一筆
            
        策略 2: My_Min (Min Spread)
            - 在區間 [prev_last_seq, target_last_seq] 內，取 Spread 最小的報價
            - 若 Spread 相同，取 SeqNo 最大的（最新的）
            
        Args:
            target_time_obj: 目標時間 (datetime)
            target_sys_id: 當前快照的 SysID (SeqNo 上限)
            prev_sys_id: 前一個快照的 SysID (用於計算區間起始，預設為 0)
            
        Returns:
            DataFrame with columns:
            - Strike, CP: 商品識別
            - My_Last_Bid/Ask/SysID/Time/ProdID: 最新報價資訊
            - My_Min_Bid/Ask/Spread: 最小 Spread 報價資訊
        """
        
        # =====================================================================
        # Step 1: 篩選 SeqNo <= target_sys_id 的所有報價
        # =====================================================================
        # 這是搜尋的基礎資料集，包含截至 target_sys_id 為止的所有歷史報價
        all_leq_target = self.ticks_df[self.ticks_df['svel_i081_seqno'] <= target_sys_id].copy()
        
        if all_leq_target.empty:
            return pd.DataFrame(columns=['Strike', 'CP', 'My_Last_Bid', 'My_Last_Ask', 
                                         'My_Last_SysID', 'My_Last_Time', 'My_Last_ProdID',
                                         'My_Min_Bid', 'My_Min_Ask', 'My_Min_Spread'])

        # 計算 Spread = Ask - Bid
        # 單邊報價 (Bid=0 或 Ask=0) 視為無效，給予極大 Spread 值
        all_leq_target['Spread'] = all_leq_target['svel_i081_best_sell_price1'] - all_leq_target['svel_i081_best_buy_price1']
        no_quote_mask = (all_leq_target['svel_i081_best_buy_price1'] == 0) | (all_leq_target['svel_i081_best_sell_price1'] == 0)
        all_leq_target.loc[no_quote_mask, 'Spread'] = 999999
        
        # =====================================================================
        # Step 2: 找每個 Strike/CP 在 SeqNo <= prev_sys_id 的「最後一筆」SeqNo
        # =====================================================================
        # 這個 SeqNo 就是區間的起始點 (包含)
        # 例如: prev_sys_id=22934，某商品在 SeqNo=20000 有報價，則 prev_last_seq=20000
        all_leq_prev = self.ticks_df[self.ticks_df['svel_i081_seqno'] <= prev_sys_id].copy()
        
        if all_leq_prev.empty:
            # 沒有 prev 之前的報價 → 區間起始 = 0 (該商品的所有報價都算)
            prev_last_seq_map = {}
        else:
            # 對每個 Strike/CP 找最後一筆 (SeqNo 最大)
            prev_sorted = all_leq_prev.sort_values(by=['svel_i081_seqno'], ascending=False)
            prev_last = prev_sorted.drop_duplicates(subset=['Strike', 'CP'], keep='first')
            # 建立 (Strike, CP) -> prev_last_seq 的 mapping
            # 例如: {('27000', 'Call'): 20000, ('27100', 'Put'): 18500, ...}
            prev_last_seq_map = prev_last.set_index(['Strike', 'CP'])['svel_i081_seqno'].to_dict()
        
        # =====================================================================
        # Step 3: 對每個商品，在區間 [prev_last_seq, target_last_seq] 內搜尋
        # =====================================================================
        last_results = []  # 儲存 Q_Last 結果
        min_results = []   # 儲存 Q_Min 結果
        
        for (strike, cp), group in all_leq_target.groupby(['Strike', 'CP']):
            # 取得該商品的區間起始 (prev_last_seq)
            # 如果這個商品在 prev_sys_id 之前沒有報價，則從 0 開始 (所有報價都算)
            prev_last_seq = prev_last_seq_map.get((strike, cp), 0)
            
            # 篩選區間內的報價: SeqNo >= prev_last_seq
            # 注意: 這裡是 >= 不是 >，因為要「包含」prev_last_seq 那一筆
            in_range = group[group['svel_i081_seqno'] >= prev_last_seq]
            
            if in_range.empty:
                # 理論上不應該發生，因為 prev_last_seq 本身就在 group 內
                continue
            
            # -----------------------------------------------------------------
            # Q_Last: 區間內 SeqNo 最大的報價 (即 target_last_seq 那筆)
            # -----------------------------------------------------------------
            last_row = in_range.sort_values(by=['svel_i081_seqno'], ascending=False).iloc[0]
            last_results.append({
                'Strike': strike,
                'CP': cp,
                'My_Last_Bid': last_row['svel_i081_best_buy_price1'],
                'My_Last_Ask': last_row['svel_i081_best_sell_price1'],
                'My_Last_SysID': last_row['svel_i081_seqno'],
                'My_Last_Time': last_row['svel_i081_time'],
                'My_Last_ProdID': last_row['svel_i081_prod_id']
            })
            
            # -----------------------------------------------------------------
            # Q_Min: 區間內 Spread 最小的報價
            # 若 Spread 相同，取 SeqNo 最大的 (最新的)
            # -----------------------------------------------------------------
            in_range_sorted = in_range.sort_values(
                by=['Spread', 'svel_i081_seqno'], 
                ascending=[True, False]  # Spread 升序, SeqNo 降序
            )
            min_row = in_range_sorted.iloc[0]
            
            min_results.append({
                'Strike': strike,
                'CP': cp,
                'My_Min_Bid': min_row['svel_i081_best_buy_price1'],
                'My_Min_Ask': min_row['svel_i081_best_sell_price1'],
                'My_Min_Spread': min_row['Spread'],
                'My_Min_SysID': min_row['svel_i081_seqno']  # 新增：Q_Min 的系統序號
            })
        
        # =====================================================================
        # Step 4: 合併 Q_Last 和 Q_Min 結果
        # =====================================================================
        snapshot_last = pd.DataFrame(last_results)
        snapshot_min = pd.DataFrame(min_results)
        
        if snapshot_last.empty:
            return pd.DataFrame(columns=['Strike', 'CP', 'My_Last_Bid', 'My_Last_Ask', 
                                         'My_Last_SysID', 'My_Last_Time', 'My_Last_ProdID',
                                         'My_Min_Bid', 'My_Min_Ask', 'My_Min_Spread', 'My_Min_SysID'])
        
        if snapshot_min.empty:
            result = snapshot_last
            result['My_Min_Bid'] = np.nan
            result['My_Min_Ask'] = np.nan
            result['My_Min_Spread'] = np.nan
            result['My_Min_SysID'] = np.nan
        else:
            result = pd.merge(snapshot_last, snapshot_min, on=['Strike', 'CP'], how='outer')
        
        return result

    def reconstruct_all(self, schedule_times, initial_sys_id):
        """
        【增量式】一次重建所有時間點的委託簿快照。
        
        比逐個呼叫 reconstruct_at 快 10-50x，因為：
        1. 只做一次排序和預處理（NumPy 陣列）
        2. 每個時間點只處理新增的 ticks（np.searchsorted 二分搜尋）
        3. 用字典維護 Q_Last 狀態，增量更新
        4. 全部時間點的結果累積為 flat list，最後一次建 DataFrame
        
        Args:
            schedule_times: list of (time_obj, sys_id, time_str) tuples，依時間排序
            initial_sys_id: 初始 SysID（排程的第一個 SysID，用作第一個時間點的 prev）
            
        Returns:
            單一 DataFrame，包含所有時間點的快照（含 Time, Snapshot_SysID 欄位）
        """
        from collections import defaultdict
        
        # =================================================================
        # 預處理：排序 + 轉為 NumPy 陣列（只做一次）
        # =================================================================
        print("增量重建：預處理資料中...")
        
        # 確保按 SeqNo 排序
        ticks_sorted = self.ticks_df.sort_values('svel_i081_seqno').reset_index(drop=True)
        
        # 轉為 NumPy 陣列（避免每次存取時的 pandas overhead）
        seqnos = ticks_sorted['svel_i081_seqno'].values
        bids = ticks_sorted['svel_i081_best_buy_price1'].values.astype(float)
        asks = ticks_sorted['svel_i081_best_sell_price1'].values.astype(float)
        strikes_arr = ticks_sorted['Strike'].values
        cps_arr = ticks_sorted['CP'].values
        times_arr = ticks_sorted['svel_i081_time'].values
        prod_ids_arr = ticks_sorted['svel_i081_prod_id'].values
        
        # 預計算 Spread
        spreads = asks - bids
        no_quote = (bids == 0) | (asks == 0)
        spreads[no_quote] = 999999
        
        # 預計算有效性（bid >= 0, ask > 0, ask > bid）
        valid_mask = (bids >= 0) & (asks > 0) & (asks > bids)
        
        n_ticks = len(seqnos)
        n_times = len(schedule_times)
        print(f"  總 ticks 數: {n_ticks}, 時間點數: {n_times}")
        
        # =================================================================
        # 有效報價判定（inline，避免函式呼叫開銷）
        # =================================================================
        # valid_mask[i] = True 代表 tick i 是有效報價
        
        # =================================================================
        # 增量處理：累積所有結果到 flat list
        # =================================================================
        q_last = {}         # (Strike, CP) -> 最新報價狀態（Raw）
        q_last_valid = {}   # (Strike, CP) -> 最新有效報價狀態
        all_rows = []       # 所有時間點的結果，flat list of dicts
        
        # Step A: 處理 initial_sys_id 之前的所有 ticks
        init_end_idx = int(np.searchsorted(seqnos, initial_sys_id, side='right'))
        for i in range(init_end_idx):
            key = (strikes_arr[i], cps_arr[i])
            tick_info = {
                'bid': bids[i], 'ask': asks[i], 'seqno': seqnos[i],
                'time': times_arr[i], 'prod_id': prod_ids_arr[i], 'spread': spreads[i]
            }
            q_last[key] = tick_info
            # 若有效，同步更新 q_last_valid
            if valid_mask[i]:
                q_last_valid[key] = tick_info.copy()
        
        global_processed_up_to = init_end_idx
        
        for t_idx, (time_obj, target_sys_id, time_str) in enumerate(schedule_times):
            # Step B: 二分搜尋找新增 ticks 範圍
            target_end_idx = int(np.searchsorted(seqnos, target_sys_id, side='right'))
            
            # 保存 prev 狀態（用於 Q_Min）
            q_last_at_prev = {k: dict(v) for k, v in q_last.items()}
            
            # 處理新增 ticks
            products_with_new_ticks = set()
            new_ticks_by_product = defaultdict(list)
            
            for i in range(global_processed_up_to, target_end_idx):
                key = (strikes_arr[i], cps_arr[i])
                tick_info = {
                    'bid': bids[i], 'ask': asks[i], 'seqno': seqnos[i],
                    'time': times_arr[i], 'prod_id': prod_ids_arr[i], 'spread': spreads[i]
                }
                q_last[key] = tick_info
                products_with_new_ticks.add(key)
                new_ticks_by_product[key].append(i)
                
                # 【Q_Last Valid Fallback】若有效，更新 q_last_valid
                # 效能：O(1)，只在 tick 迴圈中多一個 if
                if valid_mask[i]:
                    q_last_valid[key] = tick_info.copy()
            
            global_processed_up_to = target_end_idx
            
            # Step C: 建立該時間點所有商品的結果（直接寫入 flat list）
            for key, last_info in q_last.items():
                strike, cp = key
                
                # ========== Q_Last Valid ==========
                # 使用 q_last_valid（已在 tick 迴圈中增量維護）
                valid_info = q_last_valid.get(key)
                if valid_info:
                    last_valid_bid = valid_info['bid']
                    last_valid_ask = valid_info['ask']
                    last_valid_seqno = valid_info['seqno']
                    last_valid_time = valid_info['time']
                    last_valid_prod_id = valid_info['prod_id']
                else:
                    # 該商品從頭到現在都沒有有效報價 → null
                    last_valid_bid = np.nan
                    last_valid_ask = np.nan
                    last_valid_seqno = np.nan
                    last_valid_time = np.nan
                    last_valid_prod_id = np.nan
                
                # ========== Q_Min（有效報價版）==========
                # Q_Min 定義：t時點前15秒內買賣價差最小且最接近t時點(latest)報價
                # 
                # 重要概念：
                # 1. SeqNo 是跨商品的全局序號（Near/Next, 所有 Strike, Call/Put 共用）
                # 2. 處理單一商品時，該商品的 SeqNo 會不連續（中間穿插其他商品的 ticks）
                # 3. q_last_at_prev = 前一個時間點處理完後，該商品的最新報價
                #    = 小於當前區間起始 SeqNo 的最後一個報價（該商品的區間起始狀態）
                # 
                # Q_Min 候選來源：
                # - q_last_at_prev（區間起始時該商品的報價狀態）
                # - 區間內該商品的所有新 ticks（只考慮有效報價）
                # 
                # 選擇規則：
                # 1. 從候選中選 spread 最小的
                # 2. 若 spread 相同，選 SeqNo 最大的（最新）
                # 3. 若 Q_Last 的 spread 等於 min_spread，優先使用 Q_Last（tie-breaking）
                if key in products_with_new_ticks:
                    # 收集候選 ticks（q_last_at_prev + 區間新增），只保留有效的
                    prev_info = q_last_at_prev.get(key)
                    
                    # 初始化為 prev（若 prev 有效）
                    min_spread = float('inf')
                    min_seqno = -1
                    min_bid = np.nan
                    min_ask = np.nan
                    
                    if prev_info:
                        p_bid, p_ask = prev_info['bid'], prev_info['ask']
                        # 用 Python 原生判斷（不是 NumPy bool），避免型別問題
                        if p_bid >= 0 and p_ask > 0 and p_ask > p_bid:
                            min_spread = prev_info['spread']
                            min_seqno = prev_info['seqno']
                            min_bid = p_bid
                            min_ask = p_ask
                    
                    # 掃描區間內的新 ticks，只看有效的
                    for i in new_ticks_by_product[key]:
                        if not valid_mask[i]:
                            continue  # 跳過無效 tick
                        s = spreads[i]
                        seq = seqnos[i]
                        # 找 spread 最小，若 spread 相同則選 SeqNo 最大（最新）
                        # 注意：用容差比較 spread（避免浮點數誤差，如 7.8-7.4=0.3999...947 vs 7.7-7.3=0.4000...036）
                        spread_diff = s - min_spread
                        if spread_diff < -1e-9 or (abs(spread_diff) <= 1e-9 and seq > min_seqno):
                            min_spread = s
                            min_seqno = seq
                            min_bid = bids[i]
                            min_ask = asks[i]
                    
                    # 【Tie-breaking】若 Q_Last 的 spread 等於 min_spread，優先使用 Q_Last
                    # 因為 Q_Last 是最新的報價，符合「spread 最小且最新」的定義
                    if valid_info and not np.isnan(min_spread):
                        last_spread = valid_info['ask'] - valid_info['bid']
                        # 用容差比較（避免浮點數誤差）
                        if abs(last_spread - min_spread) < 1e-9:
                            min_bid = valid_info['bid']
                            min_ask = valid_info['ask']
                            min_spread = last_spread
                            min_seqno = valid_info['seqno']
                else:
                    # 沒有新 tick → 沿用 prev 的 Q_Min（若 prev 有效）
                    prev_info = q_last_at_prev.get(key, last_info)
                    p_bid, p_ask = prev_info['bid'], prev_info['ask']
                    if p_bid >= 0 and p_ask > 0 and p_ask > p_bid:
                        min_bid = p_bid
                        min_ask = p_ask
                        min_spread = prev_info['spread']
                        min_seqno = prev_info['seqno']
                    else:
                        min_bid = np.nan
                        min_ask = np.nan
                        min_spread = np.nan
                        min_seqno = np.nan
                
                # 直接寫入 flat row（含時間點資訊）
                all_rows.append({
                    'Time': time_str,
                    'Snapshot_SysID': target_sys_id,
                    'Strike': strike,
                    'CP': cp,
                    # Raw Q_Last（原始最新值，可能無效）
                    'My_Last_Raw_Bid': last_info['bid'],
                    'My_Last_Raw_Ask': last_info['ask'],
                    # Valid Q_Last（經過 fallback 的有效值）
                    'My_Last_Bid': last_valid_bid,
                    'My_Last_Ask': last_valid_ask,
                    'My_Last_SysID': last_valid_seqno,
                    'My_Last_Time': last_valid_time,
                    'My_Last_ProdID': last_valid_prod_id,
                    # Q_Min（只取有效報價）
                    'My_Min_Bid': min_bid,
                    'My_Min_Ask': min_ask,
                    'My_Min_Spread': min_spread,
                    'My_Min_SysID': min_seqno
                })
            
            # 進度報告
            if (t_idx + 1) % 100 == 0 or t_idx == 0:
                print(f"  增量重建進度: {t_idx + 1}/{n_times} ({time_str})")
        
        # 最後一次性建 DataFrame（避免每個時間點都建一次）
        result_df = pd.DataFrame(all_rows)
        print(f"  增量重建完成: 共 {n_times} 個時間點, {len(result_df)} 筆")
        return result_df

from datetime import datetime, timedelta

def get_official_data(prod_path, target_time):
    """
    讀取 PROD 檔中特定時間的 'snapshot' 欄位報價
    用以驗證 My_Last 是否與官方最終輸出一致
    """
    off_calls = []
    off_puts = []
    
    with open(prod_path, 'r', encoding='utf-8') as f:
        # Header: ... snapshot_call_bid(42) snapshot_call_ask(43) snapshot_put_bid(44) snapshot_put_ask(45) ...
        # 注意: Python split 0-based index. 
        # 假設 PROD 欄位非常多，直接依賴順序可能有風險，最好動態抓 Header
        # 但為了此次驗證，我們使用 view_file 確認過的結構
        
        header_line = f.readline().strip()
        headers = header_line.split('\t')
        
        try:
            # 動態抓取 index，避免硬編碼出錯
            idx_c_bid = headers.index('snapshot_call_bid')
            idx_c_ask = headers.index('snapshot_call_ask')
            idx_p_bid = headers.index('snapshot_put_bid')
            idx_p_ask = headers.index('snapshot_put_ask')
            # 輔助用的 sysID (為了 debug) - 注意 snapshot_sysID 只有一個 (Col 46 probably)
            # 但我們也需要 c.last_sysID 或類似的來比對?
            # 暫時只比對價格，因為 SysID 可能沒有 snapshot 版的分開紀錄?
            # 根據 grep output: 最後一欄是 snapshot_sysID (14745778)，這是 Time Point SysID
            # 這不是個別 Quote 的 SysID。個別 Quote 的 SysID 可能在 c.last_sysID (Col 18?)
            # 不過使用者目前只要求比對 "數值" (Price)
            
        except ValueError as e:
            print(f"錯誤: 找不到 snapshot 欄位 ({e})")
            return pd.DataFrame(), pd.DataFrame()

        f.readline() # line 2
        
        for line in f:
            parts = line.strip().split('\t')
            # 確保長度足夠
            if len(parts) > max(idx_c_bid, idx_p_ask) and parts[1] == target_time:
                # Call
                off_calls.append({
                    'Strike': int(parts[2]),
                    'Off_Bid': float(parts[idx_c_bid]),
                    'Off_Ask': float(parts[idx_c_ask]),
                    # 'Off_SysID': ... snapshot 沒這欄
                })
                # Put
                off_puts.append({
                    'Strike': int(parts[5]),
                    'Off_Bid': float(parts[idx_p_bid]),
                    'Off_Ask': float(parts[idx_p_ask]),
                })
    return pd.DataFrame(off_calls), pd.DataFrame(off_puts)

def compare_data(my_df, off_df, label):
    """比對重建資料 (My_Last) 與官方資料"""
    if my_df.empty or off_df.empty:
        print(f"[{label}] 無法比對 (資料為空)")
        return
        
    merged = pd.merge(off_df, my_df, on='Strike', how='inner')
    
    diff_bid = merged['My_Last_Bid'] - merged['Off_Bid']
    diff_ask = merged['My_Last_Ask'] - merged['Off_Ask']
    
    diff_count = len(merged[(diff_bid != 0) | (diff_ask != 0)])
    
    if diff_count == 0:
        print(f"[{label}] \t PASS (差異數=0, 筆數={len(merged)})")
    else:
        print(f"[{label}] \t FAIL (差異數={diff_count})")
        # 顯示差異 (含 SysID 和 ProdID 和 My_Min)
        merged['SysID_Diff'] = merged['My_Last_SysID'] - merged['Off_SysID']
        cols = ['Strike', 'Off_Bid', 'My_Last_Bid', 'My_Min_Bid', 'Off_Ask', 'My_Last_Ask', 'My_Min_Ask', 'My_Min_Spread', 'SysID_Diff']
        diffs = merged[(diff_bid != 0) | (diff_ask != 0)][cols]
        print(diffs.to_string(index=False))

def investigate_strike(ticks, target_time_obj, target_sys_id, strike, cp, label):
    """詳細條列特定履約價在快照視窗內的原始 Ticks，以解釋選擇邏輯"""
    print(f"\n[{label}] 詳細稽核 - Strike {strike} {cp}")
    print(f"  Target Time: {target_time_obj.time()}, Target SysID: {target_sys_id}")
    
    # 1. 篩選商品
    df = ticks[(ticks['Strike'] == strike) & (ticks['CP'] == cp)].copy()
    
    # 補上時間與格式轉換
    df['temp_datetime'] = pd.to_datetime(df['svel_i081_time'], format='%H%M%S%f')
    
    # 2. 篩選視窗 (T - 15s)
    start_time = target_time_obj - timedelta(seconds=15)
    
    # 顯示 15秒內的資料 (含稍微前面一點的以供參考)
    # 寬鬆一點，取 T-20s
    lookback = target_time_obj - timedelta(seconds=20)
    
    window_df = df[
        (df['svel_i081_seqno'] <= target_sys_id) & 
        (df['temp_datetime'] >= lookback)
    ].copy()
    
    if window_df.empty:
        print("  找不到區間資料")
        return

    window_df['Spread'] = window_df['svel_i081_best_sell_price1'] - window_df['svel_i081_best_buy_price1']
    # 標記
    window_df['Is_In_15s'] = window_df['temp_datetime'] >= start_time
    
    # 選出 My_Last
    last_tick = window_df.sort_values('svel_i081_seqno', ascending=False).iloc[0]
    
    # 選出 My_Min (只看 15s 內)
    in_window = window_df[window_df['Is_In_15s']]
    if not in_window.empty:
        min_tick = in_window.sort_values(['Spread', 'svel_i081_seqno'], ascending=[True, False]).iloc[0]
    else:
        min_tick = None
        
    print(f"  區間行情列表 (Lookback 20s):")
    cols = ['svel_i081_seqno', 'svel_i081_time', 'svel_i081_prod_id', 'svel_i081_best_buy_price1', 'svel_i081_best_sell_price1', 'Spread', 'Is_In_15s']
    
    # 格式化輸出
    pd.set_option('display.max_rows', 50)
    print(window_df[cols].sort_values('svel_i081_seqno').to_string(index=False))
    
    print("\n  [Logic Result]")
    print(f"  > My_Last Selected (SeqNo {last_tick['svel_i081_seqno']}): Bid={last_tick['svel_i081_best_buy_price1']}, Spread={last_tick['Spread']}")
    if min_tick is not None:
        print(f"  > My_Min  Selected (SeqNo {min_tick['svel_i081_seqno']}): Bid={min_tick['svel_i081_best_buy_price1']}, Spread={min_tick['Spread']}")
    else:
        print("  > My_Min: No valid tick in 15s window")


def main():
    """主程式：執行完整四面向驗證 (Near/Next x Call/Put)"""
    raw_dir = r"c:\Users\jerry1016\.gemini\antigravity\VIX\資料來源\J002-11300041_20251231\temp" 
    prod_dir = r"c:\Users\jerry1016\.gemini\antigravity\VIX\資料來源\20251231"
    target_date = "20251231"
    TARGET_TIME = "120015"
    
    print(f"=== 開始完整驗證 (Target Time: {TARGET_TIME}) ===")
    
    # 1. 載入原始資料
    print(">>> 載入原始 Ticks...")
    loader = RawDataLoader(raw_dir, target_date)
    near_ticks, next_ticks, terms = loader.load_and_filter()
    
    if near_ticks is None: return

    # 定義驗證任務
    tasks = [
        ('Near', near_ticks, f"NearPROD_{target_date}.tsv"),
        ('Next', next_ticks, f"NextPROD_{target_date}.tsv")
    ]
    
    # --- 針對 Call 30800 (Next) 進行詳細稽核 ---
    # 先找到 Snapshot Point
    # scheduler = SnapshotScheduler(os.path.join(prod_dir, f"NextPROD_{target_date}.tsv"))
    # schedule = scheduler.load_schedule()
    # target_row = schedule[schedule['orig_time_str'] == TARGET_TIME].iloc[0]
    # t_obj = target_row['time_obj']
    # sys_id = target_row['sys_id']
    
    # investigate_strike(next_ticks, t_obj, sys_id, 30800, 'Call', 'Next Call Audit')
    
    # 若上一行的稽核已經足夠，下面的全量驗證可以先暫停，或繼續跑
    # 為了回應使用者 "來檢查這一筆"，我們先只跑稽核
    # 為了保持完整性，我還是留著，但或許使用者只想看稽核結果
    # 暫時註解掉全量跑迴圈，專注於稽核
    
    for term_name, ticks, prod_filename in tasks:
        print(f"\n>>> 驗證 {term_name} Term ({prod_filename})")
        prod_path = os.path.join(prod_dir, prod_filename)
        
        # 載入排程找 SysID (回傳 schedule_df 和 initial_sys_id)
        scheduler = SnapshotScheduler(prod_path)
        schedule, _ = scheduler.load_schedule()  # 忽略 initial_sys_id，此處測試用
        target_row = schedule[schedule['orig_time_str'] == TARGET_TIME]
        
        if target_row.empty:
            print(f"  找不到時間點 {TARGET_TIME}")
            continue
            
        t_obj = target_row.iloc[0]['time_obj']
        sys_id = target_row.iloc[0]['sys_id']
        print(f"  Snapshot Point: Time={TARGET_TIME}, SysID={sys_id}")
        
        # 重建 (測試用：使用 prev_sys_id=0，即搜尋從頭到 sys_id 的所有報價)
        print("  Reconstructing Order Book...")
        reconstructor = SnapshotReconstructor(ticks)
        snapshot = reconstructor.reconstruct_at(t_obj, sys_id, prev_sys_id=0)
        
        # 準備官方資料
        off_calls_df, off_puts_df = get_official_data(prod_path, TARGET_TIME)
        
        # 準備我的資料
        # Rename user cols for comparison
        # 這裡 snapshot 已經有 My_Last_Bid 等欄位
        
        # 分離 Call/Put
        my_calls = snapshot[snapshot['CP'] == 'Call'].copy()
        my_puts = snapshot[snapshot['CP'] == 'Put'].copy()
        
        # 執行比對
        compare_data(my_calls, off_calls_df, f"{term_name} Call")
        compare_data(my_puts, off_puts_df, f"{term_name} Put")
    
    print("\n=== 驗證結束 ===")

if __name__ == "__main__":
    main()
