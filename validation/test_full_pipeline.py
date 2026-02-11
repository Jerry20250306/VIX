"""
完整測試：從 Step 0 開始計算 → PROD 格式輸出 → 比對
"""
import pandas as pd
import numpy as np
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

print("=" * 80)
print("VIX Step 0 完整測試（從頭計算 + PROD 格式比對）")
print("=" * 80)

# ============================================================================
# Step 1: 執行 step0_valid_quotes.py（步驟一）
# ============================================================================
print("\n" + "=" * 80)
print("【步驟一】獲取序列有效報價")
print("=" * 80)

from step0_valid_quotes import main as step1_main

# 執行前 30 個時間點
step1_main(max_time_points=30)

# ============================================================================
# Step 2: 執行 step0_2_ema_calculation.py（步驟二與步驟三）
# ============================================================================
print("\n" + "=" * 80)
print("【步驟二與步驟三】EMA 計算 + 異常值判定 + 篩選報價")
print("=" * 80)

from step0_2_ema_calculation import add_ema_and_outlier_detection, convert_to_prod_format

# 讀取步驟一結果
near_csv = "output/step0_1_valid_quotes_Near_測試前30個.csv"
next_csv = "output/step0_1_valid_quotes_Next_測試前30個.csv"

print(f"\n>>> 讀取步驟一結果...")
near_df = pd.read_csv(near_csv)
next_df = pd.read_csv(next_csv)

print(f"    Near Term: {len(near_df)} 筆")
print(f"    Next Term: {len(next_df)} 筆")

# 執行步驟二與步驟三
print(f"\n>>> 處理 Near Term...")
near_with_ema = add_ema_and_outlier_detection(near_df, 'Near')

print(f"\n>>> 處理 Next Term...")
next_with_ema = add_ema_and_outlier_detection(next_df, 'Next')

# ============================================================================
# Step 3: 轉換為 PROD 格式並儲存
# ============================================================================
print("\n" + "=" * 80)
print("【轉換為 PROD 格式】")
print("=" * 80)

# 轉換
near_prod = convert_to_prod_format(near_with_ema)
next_prod = convert_to_prod_format(next_with_ema)

# 儲存
near_prod.to_csv("output/step0_Near_PROD格式_前30時點.csv", index=False, encoding="utf-8-sig")
next_prod.to_csv("output/step0_Next_PROD格式_前30時點.csv", index=False, encoding="utf-8-sig")

print(f"Near Term PROD 格式: {len(near_prod)} 筆")
print(f"Next Term PROD 格式: {len(next_prod)} 筆")

# ============================================================================
# Step 4: 與 PROD 資料比對
# ============================================================================
print("\n" + "=" * 80)
print("【與 PROD 資料比對】")
print("=" * 80)

# 讀取 PROD 資料
prod_near = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
prod_next = pd.read_csv(r'資料來源\20251231\NextPROD_20251231.tsv', sep='\t', dtype=str)

# 篩選相同時間點
our_times = near_prod['time'].unique()
prod_near_filtered = prod_near[prod_near['time'].astype(int).isin(our_times)]
prod_next_filtered = prod_next[prod_next['time'].astype(int).isin(our_times)]

print(f"\n比對範圍: {len(our_times)} 個時間點")
print(f"PROD Near 筆數: {len(prod_near_filtered)}")
print(f"PROD Next 筆數: {len(prod_next_filtered)}")

def compare_term(ours_df, prod_df, term_name):
    """比對單一 Term 的結果"""
    print(f"\n--- {term_name} Term ---")
    
    # 準備 PROD 資料
    prod_df = prod_df.copy()
    prod_df['time_int'] = prod_df['time'].astype(int)
    prod_df['strike_int'] = prod_df['strike'].astype(int)
    
    # 比對欄位對照
    comparisons = [
        ('c.ema', 'c.ema', 1e-4, 'EMA (Call)'),
        ('p.ema', 'p.ema', 1e-4, 'EMA (Put)'),
        ('c.bid', 'c.bid', 0.5, 'Q_hat Bid (Call)'),
        ('c.ask', 'c.ask', 0.5, 'Q_hat Ask (Call)'),
        ('p.bid', 'p.bid', 0.5, 'Q_hat Bid (Put)'),
        ('p.ask', 'p.ask', 0.5, 'Q_hat Ask (Put)'),
        ('c.last_bid', 'c.last_bid', 0.5, 'Q_Last Bid (Call)'),
        ('c.last_ask', 'c.last_ask', 0.5, 'Q_Last Ask (Call)'),
        ('p.last_bid', 'p.last_bid', 0.5, 'Q_Last Bid (Put)'),
        ('p.last_ask', 'p.last_ask', 0.5, 'Q_Last Ask (Put)'),
    ]
    
    # 合併資料進行比對
    merged = pd.merge(
        ours_df,
        prod_df,
        left_on=['time', 'strike'],
        right_on=['time_int', 'strike_int'],
        how='inner',
        suffixes=('_OURS', '_PROD')
    )
    
    print(f"成功配對: {len(merged)} 筆")
    
    results = {}
    for ours_col, prod_col, tolerance, desc in comparisons:
        ours_col_name = f'{ours_col}_OURS' if f'{ours_col}_OURS' in merged.columns else ours_col
        prod_col_name = f'{prod_col}_PROD' if f'{prod_col}_PROD' in merged.columns else prod_col
        
        # 處理欄位名稱
        if ours_col_name not in merged.columns:
            # 嘗試直接使用欄位名
            if ours_col in merged.columns:
                ours_col_name = ours_col
            else:
                print(f"  找不到欄位: {ours_col}")
                continue
        
        if prod_col_name not in merged.columns:
            if prod_col in merged.columns:
                prod_col_name = prod_col
            else:
                print(f"  找不到欄位: {prod_col}")
                continue
        
        # 轉換為數值
        ours_val = pd.to_numeric(merged[ours_col_name], errors='coerce')
        prod_val = pd.to_numeric(merged[prod_col_name], errors='coerce')
        
        # 計算差異
        valid_mask = ours_val.notna() & prod_val.notna()
        diff = (ours_val - prod_val).abs()
        match_count = ((diff < tolerance) | ~valid_mask).sum()
        total = len(merged)
        
        rate = match_count / total * 100
        results[desc] = rate
        
        status = "[OK]" if rate >= 99 else "[WARN]" if rate >= 95 else "[FAIL]"
        print(f"  {status} {desc}: {match_count}/{total} = {rate:.2f}%")
    
    return results

# 執行比對
print("\n>>> 比對 Near Term...")
comp_near_prod = prod_near_filtered.copy()
near_results = compare_term(near_prod, comp_near_prod, 'Near')

print("\n>>> 比對 Next Term...")
comp_next_prod = prod_next_filtered.copy()
next_results = compare_term(next_prod, comp_next_prod, 'Next')

# ============================================================================
# 總結
# ============================================================================
print("\n" + "=" * 80)
print("【測試總結】")
print("=" * 80)

print("\n輸出檔案:")
print("  - output/step0_1_valid_quotes_Near_測試前30個.csv (步驟一)")
print("  - output/step0_1_valid_quotes_Next_測試前30個.csv (步驟一)")
print("  - output/step0_Near_PROD格式_前30時點.csv (PROD 格式)")
print("  - output/step0_Next_PROD格式_前30時點.csv (PROD 格式)")

print("\n" + "=" * 80)
print("測試完成!")
print("=" * 80)
