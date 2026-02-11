"""
VIX Step 0 差異分析腳本（PROD 格式版）
直接比對我們的 PROD 格式輸出 vs 官方 PROD 資料
兩邊欄位名稱一致（c.bid, c.ask, c.ema, c.gamma, ...），可直接比較
"""
import pandas as pd
import numpy as np

pd.set_option('display.width', 400)
pd.set_option('display.max_columns', None)

# ======================================================================
# 要比對的欄位清單（對應 docs/output_format_spec.md）
# ======================================================================

# 數值型欄位：使用容差比對
NUMERIC_COMPARE_COLS = [
    # Call
    'c.ema', 'c.gamma',
    'c.last_bid', 'c.last_ask',
    'c.min_bid', 'c.min_ask',
    'c.bid', 'c.ask',
    # Put
    'p.ema', 'p.gamma',
    'p.last_bid', 'p.last_ask',
    'p.min_bid', 'p.min_ask',
    'p.bid', 'p.ask',
]

# 字串型欄位：使用完全比對
STRING_COMPARE_COLS = [
    'c.last_outlier', 'c.min_outlier',
    'p.last_outlier', 'p.min_outlier',
]


def main():
    print("=" * 80)
    print("VIX Step 0 差異分析 - PROD 格式直接比對")
    print("=" * 80)
    
    # ======================================================================
    # 1. 載入資料
    # ======================================================================
    print("\n>>> 載入資料...")
    
    # 官方 PROD 資料
    prod_df = pd.read_csv(
        r'資料來源\20251231\NearPROD_20251231.tsv', 
        sep='\t', dtype=str
    )
    
    # 我們的計算結果（已是 PROD 格式）
    our_df = pd.read_csv('output/驗證20251231_NearPROD.csv')
    
    print(f"    PROD: {len(prod_df)} 筆")
    print(f"    我們: {len(our_df)} 筆")
    
    # ======================================================================
    # 2. 準備 PROD 資料
    # ======================================================================
    # 篩選有效列（有 strike 的行）
    prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
    prod_valid['time'] = prod_valid['time'].astype(int)
    prod_valid['strike'] = prod_valid['strike'].astype(int)
    
    # 轉換 PROD 數值欄位
    for col in NUMERIC_COMPARE_COLS:
        if col in prod_valid.columns:
            prod_valid[col] = pd.to_numeric(prod_valid[col], errors='coerce')
    
    # 確保我們的資料型別正確
    our_df['time'] = our_df['time'].astype(int)
    our_df['strike'] = our_df['strike'].astype(int)
    
    # ======================================================================
    # 3. Merge：以 (time, strike) 為 key 合併
    # ======================================================================
    # 先加前綴避免衝突
    prod_renamed = prod_valid.rename(
        columns={c: f'PROD_{c}' for c in NUMERIC_COMPARE_COLS + STRING_COMPARE_COLS 
                 if c in prod_valid.columns}
    )
    our_renamed = our_df.rename(
        columns={c: f'OUR_{c}' for c in NUMERIC_COMPARE_COLS + STRING_COMPARE_COLS 
                 if c in our_df.columns}
    )
    
    merged = pd.merge(
        our_renamed, prod_renamed,
        on=['time', 'strike'],
        how='inner'
    )
    
    print(f"    合併後: {len(merged)} 筆可比較")
    
    # ======================================================================
    # 4. 向量化比較
    # ======================================================================
    diff_flags = {}
    
    # 數值型比對：容差 0.01（價格整數比對給容差以防浮點誤差）
    for col in NUMERIC_COMPARE_COLS:
        our_col = f'OUR_{col}'
        prod_col = f'PROD_{col}'
        if our_col in merged.columns and prod_col in merged.columns:
            # EMA 使用更嚴格的容差
            tol = 1e-4 if 'ema' in col else 0.01
            diff_flags[col] = (
                merged[our_col].fillna(-999) - merged[prod_col].fillna(-999)
            ).abs() > tol
    
    # 字串型比對：直接比較
    for col in STRING_COMPARE_COLS:
        our_col = f'OUR_{col}'
        prod_col = f'PROD_{col}'
        if our_col in merged.columns and prod_col in merged.columns:
            diff_flags[col] = (
                merged[our_col].fillna('').astype(str).str.strip() != 
                merged[prod_col].fillna('').astype(str).str.strip()
            )
    
    # 合併所有差異
    merged['has_diff'] = False
    for col, flag in diff_flags.items():
        merged[f'diff_{col}'] = flag
        merged['has_diff'] = merged['has_diff'] | flag
    
    # ======================================================================
    # 5. 依時間順序分析差異
    # ======================================================================
    print("\n" + "=" * 80)
    print("依時間順序分析差異")
    print("=" * 80)
    
    our_times = sorted(merged['time'].unique())
    
    for time_int in our_times:
        time_data = merged[merged['time'] == time_int]
        strikes = len(time_data['strike'].unique())
        
        print(f"\n>>> 時間點: {time_int} ({strikes} 個 Strike)")
        
        diff_rows = time_data[time_data['has_diff']]
        
        if len(diff_rows) == 0:
            print(f"    [OK] 無差異")
            continue
        
        # 列出所有差異欄位統計
        diff_summary = {}
        for col in diff_flags:
            cnt = time_data[f'diff_{col}'].sum()
            if cnt > 0:
                diff_summary[col] = int(cnt)
        
        print(f"    [差異] 共 {len(diff_rows)} 筆不一致")
        for col, cnt in diff_summary.items():
            print(f"        {col}: {cnt} 筆")
        
        # 顯示第一筆差異的詳細資訊
        first = diff_rows.iloc[0]
        strike = first['strike']
        print(f"\n    首筆差異 Strike={strike}:")
        print(f"    {'欄位':<20} {'PROD':>15} {'我們':>15} {'差異':>6}")
        print(f"    {'-'*56}")
        
        for col in NUMERIC_COMPARE_COLS + STRING_COMPARE_COLS:
            if f'diff_{col}' in merged.columns and first.get(f'diff_{col}', False):
                prod_val = first.get(f'PROD_{col}', 'N/A')
                our_val = first.get(f'OUR_{col}', 'N/A')
                print(f"    {col:<20} {str(prod_val):>15} {str(our_val):>15}   <<<")
        
        print("\n" + "=" * 80)
        print("分析結束：已找到差異")
        print("=" * 80)
        return  # 找到差異就停止
    
    print("\n" + "=" * 80)
    print("[OK] 全部時間點驗證通過，無任何差異！")
    print("=" * 80)


if __name__ == "__main__":
    main()
