"""
比對 PROD 格式輸出與 PROD 資料
"""
import pandas as pd
import numpy as np

print("=" * 80)
print("VIX Step 0 PROD 格式比對")
print("=" * 80)

# 讀取我們的輸出
near_ours = pd.read_csv("output/step0_Near_PROD格式_前30時點.csv")
next_ours = pd.read_csv("output/step0_Next_PROD格式_前30時點.csv")

print(f"\n我們的輸出:")
print(f"  Near Term: {len(near_ours)} 筆")
print(f"  Next Term: {len(next_ours)} 筆")

# 讀取 PROD 資料
prod_near = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
prod_next = pd.read_csv(r'資料來源\20251231\NextPROD_20251231.tsv', sep='\t', dtype=str)

# 篩選相同時間點
our_times = near_ours['time'].unique()
prod_near_filtered = prod_near[prod_near['time'].astype(int).isin(our_times)]
prod_next_filtered = prod_next[prod_next['time'].astype(int).isin(our_times)]

print(f"\nPROD 資料 (前 {len(our_times)} 個時間點):")
print(f"  Near Term: {len(prod_near_filtered)} 筆")
print(f"  Next Term: {len(prod_next_filtered)} 筆")

def compare_term(ours_df, prod_df, term_name):
    """比對單一 Term 的結果"""
    print(f"\n{'='*60}")
    print(f"【{term_name} Term 比對結果】")
    print(f"{'='*60}")
    
    # 準備 PROD 資料
    prod_df = prod_df.copy()
    prod_df['time_int'] = prod_df['time'].astype(int)
    prod_df['strike_int'] = prod_df['strike'].astype(int)
    
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
    
    # 比對欄位
    comparisons = [
        # (我們的欄位, PROD欄位, 容錯, 說明)
        ('c.ema', 'c.ema', 1e-4, 'EMA (Call)'),
        ('p.ema', 'p.ema', 1e-4, 'EMA (Put)'),
        ('c.bid', 'c.bid', 1, 'Q_hat Bid (Call)'),
        ('c.ask', 'c.ask', 1, 'Q_hat Ask (Call)'),
        ('p.bid', 'p.bid', 1, 'Q_hat Bid (Put)'),
        ('p.ask', 'p.ask', 1, 'Q_hat Ask (Put)'),
        ('c.last_bid', 'c.last_bid', 1, 'Q_Last Bid (Call)'),
        ('c.last_ask', 'c.last_ask', 1, 'Q_Last Ask (Call)'),
        ('p.last_bid', 'p.last_bid', 1, 'Q_Last Bid (Put)'),
        ('p.last_ask', 'p.last_ask', 1, 'Q_Last Ask (Put)'),
        ('c.gamma', 'c.gamma', 0.01, 'Gamma (Call)'),
        ('p.gamma', 'p.gamma', 0.01, 'Gamma (Put)'),
    ]
    
    results = {}
    for ours_col, prod_col, tolerance, desc in comparisons:
        # 找正確的欄位名稱
        ours_col_name = f'{ours_col}_OURS' if f'{ours_col}_OURS' in merged.columns else ours_col
        prod_col_name = f'{prod_col}_PROD' if f'{prod_col}_PROD' in merged.columns else prod_col
        
        if ours_col_name not in merged.columns or prod_col_name not in merged.columns:
            print(f"  [SKIP] {desc}: 欄位不存在")
            continue
        
        # 轉換為數值
        ours_val = pd.to_numeric(merged[ours_col_name], errors='coerce')
        prod_val = pd.to_numeric(merged[prod_col_name], errors='coerce')
        
        # 計算差異
        valid_mask = ours_val.notna() & prod_val.notna()
        diff = (ours_val - prod_val).abs()
        match_count = ((diff <= tolerance) | ~valid_mask).sum()
        total = len(merged)
        
        rate = match_count / total * 100
        results[desc] = rate
        
        status = "[OK]" if rate >= 99 else "[WARN]" if rate >= 95 else "[FAIL]"
        print(f"  {status} {desc}: {match_count}/{total} = {rate:.2f}%")
    
    # Outlier 比對
    print(f"\n  --- Outlier 標記比對 ---")
    for prefix in ['c', 'p']:
        cp_name = 'Call' if prefix == 'c' else 'Put'
        
        ours_col = f'{prefix}.last_outlier_OURS' if f'{prefix}.last_outlier_OURS' in merged.columns else f'{prefix}.last_outlier'
        prod_col = f'{prefix}.last_outlier_PROD' if f'{prefix}.last_outlier_PROD' in merged.columns else f'{prefix}.last_outlier'
        
        if ours_col in merged.columns and prod_col in merged.columns:
            # 轉換為布林值比對
            ours_is_outlier = merged[ours_col].apply(lambda x: x == 'V')
            prod_is_outlier = merged[prod_col].apply(lambda x: x == 'V')
            
            match_count = (ours_is_outlier == prod_is_outlier).sum()
            total = len(merged)
            rate = match_count / total * 100
            
            status = "[OK]" if rate >= 99 else "[WARN]" if rate >= 95 else "[FAIL]"
            print(f"  {status} Outlier 判定 ({cp_name}): {match_count}/{total} = {rate:.2f}%")
    
    return results

# 執行比對
near_results = compare_term(near_ours, prod_near_filtered, 'Near')
next_results = compare_term(next_ours, prod_next_filtered, 'Next')

print("\n" + "=" * 80)
print("比對完成!")
print("=" * 80)
