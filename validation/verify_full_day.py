"""
VIX Step 0 驗證腳本（優化版 - 產出詳細差異報告）
使用 pandas merge 取代逐筆比對，並產出詳細差異報表
"""
import pandas as pd
import numpy as np
from datetime import datetime
import os

pd.set_option('display.width', 400)
pd.set_option('display.max_columns', None)

def convert_outlier(prod_value):
    """將 PROD 異常值標記轉換為布林值"""
    # 統一轉字串處理
    s = str(prod_value).strip()
    if s == 'V':
        return True
    elif s == '-' or s == 'nan' or s == '':
        return None
    else:
        return False

def main():
    import sys
    print("=" * 80)
    print("VIX Step 0 驗證（詳細差異報告版）")
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # ========== 設定目標日期 ==========
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        target_date = "20251231"
    
    print(f"目標日期: {target_date}")
    
    # ========== 載入資料 ==========
    print("\n>>> 載入資料...")
    
    # PROD 資料
    prod_near_path = f'資料來源/{target_date}/NearPROD_{target_date}.tsv'
    prod_next_path = f'資料來源/{target_date}/NextPROD_{target_date}.tsv'
    
    try:
        near_prod = pd.read_csv(prod_near_path, sep='\t', dtype=str)
        next_prod = pd.read_csv(prod_next_path, sep='\t', dtype=str)
    except FileNotFoundError as e:
        print(f"錯誤: 找不到 PROD 檔案 - {e}")
        return

    # 我們的計算結果
    calc_near_path = f'output/驗證{target_date}_NearPROD.csv'
    calc_next_path = f'output/驗證{target_date}_NextPROD.csv'
    
    try:
        near_calc = pd.read_csv(calc_near_path, dtype=str)
        next_calc = pd.read_csv(calc_next_path, dtype=str)
    except FileNotFoundError as e:
        print(f"錯誤: 找不到計算結果檔案 - {e}")
        return
    
    print(f"    PROD Near: {len(near_prod)} 筆")
    print(f"    PROD Next: {len(next_prod)} 筆")
    print(f"    我們 Near: {len(near_calc)} 筆")
    print(f"    我們 Next: {len(next_calc)} 筆")
    
    # ========== 驗證並收集差異 ==========
    all_diffs = []
    
    print("\n" + "=" * 80)
    print("驗證 Near Term")
    print("=" * 80)
    diffs_near = verify_term_detailed(near_prod, near_calc, 'Near', target_date)
    all_diffs.extend(diffs_near)
    
    print("\n" + "=" * 80)
    print("驗證 Next Term")
    print("=" * 80)
    diffs_next = verify_term_detailed(next_prod, next_calc, 'Next', target_date)
    all_diffs.extend(diffs_next)
    
    # ========== 輸出差異報告 ==========
    output_file = f'output/validation_diff_{target_date}.csv'
    
    # 確保 output 資料夾存在
    if not os.path.exists('output'):
        os.makedirs('output')

    if all_diffs:
        diff_df = pd.DataFrame(all_diffs)
        # 調整欄位順序
        cols = ['Date', 'Time', 'Term', 'Strike', 'CP', 'Column', 'Ours', 'PROD', 'SysID', 'Prev_SysID']
        # 確保所有需要的欄位都存在
        for col in cols:
             if col not in diff_df.columns:
                 diff_df[col] = ''
        
        diff_df = diff_df[cols]
        
        diff_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n差異報告已儲存至: {output_file}")
        print(f"總差異筆數: {len(diff_df)}")
    else:
        print("\n恭喜！未發現任何差異。")
        # 產生空檔案以示完成
        pd.DataFrame(columns=['Date', 'Time', 'Term', 'Strike', 'CP', 'Column', 'Ours', 'PROD', 'SysID', 'Prev_SysID']).to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"已建立空報告: {output_file}")

def verify_term_detailed(prod_df, calc_df, term_name, target_date):
    """執行詳細比對並回傳差異列表"""
    
    diff_list = []
    
    print(f"  正在準備 {term_name} 資料...")
    
    # 1. 準備 PROD 資料（展開為 Call/Put 兩列）並保留 SysID
    prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
    
    # time_sysid_map 已棄用，改用 DataFrame 直接計算 Prev_SysID
    # time_sysid_map logic removed
    
    # 取得由時間排序的唯一時間列表，用來找 Prev_SysID
    # get_sysid_info 已棄用，改用 DataFrame 內建欄位
    # get_sysid_info removed

    # 展開 PROD Call/Put
    prod_valid['Time'] = prod_valid['time']
    prod_valid['Strike'] = prod_valid['strike']
    
    # 欄位映射
    prod_cols_base = ['Time', 'Strike']
    
    # Call Columns
    prod_call_cols = prod_cols_base + [
        'c.ema', 'c.gamma', 'c.last_outlier', 'c.min_outlier',
        'c.bid', 'c.ask', 'c.last_bid', 'c.last_ask', 'c.min_bid', 'c.min_ask',
        'c.last_sysID'
    ]
    # 檢查欄位是否存在
    prod_call_cols = [c for c in prod_call_cols if c in prod_valid.columns]
    
    prod_call = prod_valid[prod_call_cols].copy()
    prod_call['CP'] = 'Call'
    
    # 重新命名欄位以便統一處理 (需小心對應)
    rename_map_c = {
        'c.ema': 'PROD_EMA', 'c.gamma': 'PROD_Gamma', 
        'c.last_outlier': 'PROD_Last_Outlier', 'c.min_outlier': 'PROD_Min_Outlier',
        'c.bid': 'PROD_Q_hat_Bid', 'c.ask': 'PROD_Q_hat_Ask',
        'c.last_bid': 'PROD_Last_Bid', 'c.last_ask': 'PROD_Last_Ask',
        'c.min_bid': 'PROD_Min_Bid', 'c.min_ask': 'PROD_Min_Ask',
        'c.last_sysID': 'SysID'
    }
    prod_call = prod_call.rename(columns=rename_map_c)

    # Put Columns
    prod_put_cols = prod_cols_base + [
        'p.ema', 'p.gamma', 'p.last_outlier', 'p.min_outlier',
        'p.bid', 'p.ask', 'p.last_bid', 'p.last_ask', 'p.min_bid', 'p.min_ask',
        'p.last_sysID'
    ]
    # 檢查欄位是否存在
    prod_put_cols = [c for c in prod_put_cols if c in prod_valid.columns]
    
    prod_put = prod_valid[prod_put_cols].copy()
    prod_put['CP'] = 'Put'
    
    rename_map_p = {
        'p.ema': 'PROD_EMA', 'p.gamma': 'PROD_Gamma', 
        'p.last_outlier': 'PROD_Last_Outlier', 'p.min_outlier': 'PROD_Min_Outlier',
        'p.bid': 'PROD_Q_hat_Bid', 'p.ask': 'PROD_Q_hat_Ask',
        'p.last_bid': 'PROD_Last_Bid', 'p.last_ask': 'PROD_Last_Ask',
        'p.min_bid': 'PROD_Min_Bid', 'p.min_ask': 'PROD_Min_Ask',
        'p.last_sysID': 'SysID'
    }
    prod_put = prod_put.rename(columns=rename_map_p)
    
    prod_long = pd.concat([prod_call, prod_put], ignore_index=True)
    
    # 計算 Prev_SysID
    # 1. 確保 SysID 為數值 (可能有空值)
    prod_long['SysID'] = pd.to_numeric(prod_long['SysID'], errors='coerce').fillna(0).astype(int)
    
    # 2. 排序: Strike, CP, Time
    # 假設 Time 是 HH:MM:SS 字串，可直接排序
    prod_long = prod_long.sort_values(['Strike', 'CP', 'Time'])
    
    # 3. GroupBy shift
    prod_long['Prev_SysID'] = prod_long.groupby(['Strike', 'CP'])['SysID'].shift(1)
    
    # 第一筆的 Prev_SysID 設為 0
    prod_long['Prev_SysID'] = prod_long['Prev_SysID'].fillna(0).astype(int)

    # 2. 準備我們的計算結果 (Wide Format -> Long Format)
    print(f"  正在準備我們的計算結果 (轉為 Long Format)...")
    
    # 標準化 Time/Strike
    calc_df['Time'] = calc_df['time']
    calc_df['Strike'] = calc_df['strike']
    
    # 準備 Call 部份
    # 欄位映射: 原始 CSV 欄位 -> 統一欄位名稱
    # 注意: CSV 欄位名稱需與 step 127 看到的完全一致 (全小寫 c.bid, c.ask...)
    
    # 定義需要的欄位與重新命名映射 (Call)
    # 檢查 calc_df 的欄位名稱 (有些是 c.bid, 有些可能是 Q_Last... 取決於產生來源)
    # 查看 step 127: c.bid, p.bid, c.last_bid, c.last_sysID, c.last_outlier, c.ema, c.gamma
    
    map_c = {
        'c.ema': 'EMA',
        'c.gamma': 'Q_Last_Valid_Gamma', # 假設檢核報告輸出的是最終 Gamma
        'c.bid': 'Q_hat_Bid',    # PROD 格式的 c.bid 對應我們的 Q_hat
        'c.ask': 'Q_hat_Ask',
        'c.last_bid': 'Q_Last_Valid_Bid',
        'c.last_ask': 'Q_Last_Valid_Ask',
        'c.last_outlier': 'OURS_Last_Outlier_Str',
        # 'c.min_outlier': 'OURS_Min_Outlier_Str' # 有些檔案可能沒有 min_outlier
    }
    
    # 確保欄位存在
    cols_c = ['Time', 'Strike'] + [c for c in map_c.keys() if c in calc_df.columns]
    calc_call = calc_df[cols_c].copy()
    calc_call['CP'] = 'Call'
    calc_call = calc_call.rename(columns=map_c)
    
    # 準備 Put 部份
    map_p = {
        'p.ema': 'EMA',
        'p.gamma': 'Q_Last_Valid_Gamma',
        'p.bid': 'Q_hat_Bid', 
        'p.ask': 'Q_hat_Ask',
        'p.last_bid': 'Q_Last_Valid_Bid',
        'p.last_ask': 'Q_Last_Valid_Ask',
        'p.last_outlier': 'OURS_Last_Outlier_Str',
    }
    
    cols_p = ['Time', 'Strike'] + [c for c in map_p.keys() if c in calc_df.columns]
    calc_put = calc_df[cols_p].copy()
    calc_put['CP'] = 'Put'
    calc_put = calc_put.rename(columns=map_p)
    
    # 合併 Call 與 Put
    calc_subset = pd.concat([calc_call, calc_put], ignore_index=True)
    
    # 確保所有必要欄位存在 (若來源無該欄位則補 NaN)
    required_cols = ['EMA', 'Q_Last_Valid_Gamma', 'Q_hat_Bid', 'Q_hat_Ask', 'Q_Last_Valid_Bid', 'Q_Last_Valid_Ask', 'OURS_Last_Outlier_Str']
    for col in required_cols:
        if col not in calc_subset.columns:
            calc_subset[col] = np.nan

    # 3. 合併比對
    # 轉換型別以確保 merge 正確 (統一使用 int，避免前導零問題)
    # 處理可能非數字的情況 (雖然理論上不應發生)
    prod_long['Time_int'] = pd.to_numeric(prod_long['Time'], errors='coerce').fillna(0).astype(int)
    prod_long['Strike_int'] = pd.to_numeric(prod_long['Strike'], errors='coerce').fillna(0).astype(int)
    
    calc_subset['Time_int'] = pd.to_numeric(calc_subset['Time'], errors='coerce').fillna(0).astype(int)
    calc_subset['Strike_int'] = pd.to_numeric(calc_subset['Strike'], errors='coerce').fillna(0).astype(int)
    
    print(f"  開始合併資料...")
    # 使用 int 欄位進行合併
    merged = pd.merge(prod_long, calc_subset, left_on=['Time_int', 'Strike_int', 'CP'], right_on=['Time_int', 'Strike_int', 'CP'], how='inner')
    print(f"  成功配對: {len(merged)} 筆")
    
    # 處理 merge 後的欄位後綴 (Time_x, Time_y 等)
    if 'Time_x' in merged.columns:
        merged['Time'] = merged['Time_x']
    elif 'Time' not in merged.columns:
        # Fallback if Time was used as key (shouldn't happen here)
        merged['Time'] = merged['Time_int'].astype(str)
        
    if 'Strike_x' in merged.columns:
        merged['Strike'] = merged['Strike_x']
    elif 'Strike' not in merged.columns:
        merged['Strike'] = merged['Strike_int'].astype(str)
    
    # 4. 定義比較邏輯
    
    # Helper to check float diff
    def is_diff_float(series_prod, series_ours, tol=1e-4):
        v_prod = pd.to_numeric(series_prod, errors='coerce')
        v_ours = pd.to_numeric(series_ours, errors='coerce')
        
        # 兩者皆 NaN 視為相同
        mask_both_nan = v_prod.isna() & v_ours.isna()
        
        # 處理一方有值一方無值
        mask_mismatch_nan = v_prod.isna() ^ v_ours.isna()
        
        # 兩者皆有值才比較數值
        mask_valid = v_prod.notna() & v_ours.notna()
        diff = (v_prod - v_ours).abs()
        
        # 差異條件：(有值且差異過大) 或 (NaN 狀態不一致)
        return mask_mismatch_nan | (mask_valid & (diff > tol))

    # Helper to check string/int diff
    def is_diff_str(series_prod, series_ours):
        # 統一轉字串比較，處理 NaN
        v_prod = series_prod.fillna('').astype(str).str.strip()
        v_ours = series_ours.fillna('').astype(str).str.strip()
        
        # 處理 .0 結尾的差異 (e.g. "100" vs "100.0")
        v_prod = v_prod.apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
        v_ours = v_ours.apply(lambda x: x.replace('.0', '') if x.endswith('.0') else x)
        
        # 特殊處理 Outlier: "-" 等同於空字串或 NaN
        v_prod = v_prod.replace('-', '')
        v_ours = v_ours.replace('-', '')
        
        return v_prod != v_ours

    # 定義檢查項目 (Display Name, Prod Col, Ours Col, Method)
    checks = [
        ('EMA', 'PROD_EMA', 'EMA', is_diff_float),
        ('Gamma', 'PROD_Gamma', 'Q_Last_Valid_Gamma', is_diff_float),
        ('Q_hat_Bid', 'PROD_Q_hat_Bid', 'Q_hat_Bid', is_diff_float),
        ('Q_hat_Ask', 'PROD_Q_hat_Ask', 'Q_hat_Ask', is_diff_float),
        ('Q_Last_Bid', 'PROD_Last_Bid', 'Q_Last_Valid_Bid', is_diff_float),
        ('Q_Last_Ask', 'PROD_Last_Ask', 'Q_Last_Valid_Ask', is_diff_float),
        ('Last_Outlier', 'PROD_Last_Outlier', 'OURS_Last_Outlier_Str', is_diff_str),
        # Min Outlier 暫時不比對，因為 PROD 似乎沒有嚴格輸出？先保留
        # ('Min_Outlier', 'PROD_Min_Outlier', 'OURS_Min_Outlier_Str', is_diff_str),
    ]
    
    print(f"  開始逐項檢查差異...")
    
    for col_name, prod_col, ours_col, diff_func in checks:
        if prod_col not in merged.columns or ours_col not in merged.columns:
            print(f"  警告: 缺少欄位 {prod_col} 或 {ours_col}，跳過比對")
            continue
            
        mask = diff_func(merged[prod_col], merged[ours_col])
        diff_rows = merged[mask]
        
        if not diff_rows.empty:
            print(f"  發現差異: {col_name} - {len(diff_rows)} 筆")
            
            # 批量獲取 SysID 資訊 (優化效能)
            # 這裡簡單處理，逐筆查詢
            # 若效能不足，可考慮向量化 map
            
            for idx, row in diff_rows.iterrows():
                time_val = row['Time']
                curr_sysid = row.get('SysID', 0)
                prev_sysid = row.get('Prev_SysID', 0)
                
                diff_list.append({
                    'Date': target_date,
                    'Time': time_val,
                    'Term': term_name,
                    'Strike': row['Strike'],
                    'CP': row['CP'],
                    'Column': col_name,
                    'Ours': row[ours_col],
                    'PROD': row[prod_col],
                    'SysID': curr_sysid,
                    'Prev_SysID': prev_sysid
                })
        else:
            # print(f"  {col_name}: 無差異")
            pass
                
    return diff_list

if __name__ == "__main__":
    main()
