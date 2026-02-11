"""
分析 c.gamma 和 p.gamma 的差異案例，並將腳本放在 validation 目錄下。
"""
import pandas as pd
import numpy as np

# 1. 讀取資料
prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
our_df = pd.read_csv('output/驗證20251231_NearPROD.csv')

# 2. 格式化 PROD 資料
prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)

GAMMA_COLS = ['c.gamma', 'p.gamma']
for c in GAMMA_COLS:
    prod_valid[c] = pd.to_numeric(prod_valid[c], errors='coerce')

# 3. 合併資料
merged = pd.merge(
    our_df, prod_valid[['time', 'strike'] + GAMMA_COLS],
    on=['time', 'strike'], how='inner', suffixes=('_OUR', '_PROD')
)

print(f"=== 合併後筆數: {len(merged)} ===")

# 4. 找差異並列出案例
for col in GAMMA_COLS:
    our_c = col + '_OUR'
    prod_c = col + '_PROD'
    
    # 填補空值以利比較
    diff = (merged[our_c].fillna(-999) - merged[prod_c].fillna(-999)).abs() > 0.01
    cnt = diff.sum()
    
    print(f"\n[{col}] 差異筆數: {cnt}")
    if cnt > 0:
        diff_df = merged[diff].copy()
        for idx, row in diff_df.iterrows():
            print(f"  time={int(row['time'])}, strike={int(row['strike'])} | PROD={row[prod_c]}, 我們={row[our_c]}")
