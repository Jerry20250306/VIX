"""
快速驗證：撇除 outlier 欄位，只比對數值欄位是否一致
"""
import pandas as pd
import numpy as np

prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
our_df = pd.read_csv('output/驗證20251231_NearPROD.csv')

prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)

# 只比對數值欄位（排除 outlier）
NUM_COLS = [
    'c.ema', 'c.gamma', 'c.last_bid', 'c.last_ask', 'c.min_bid', 'c.min_ask', 'c.bid', 'c.ask',
    'p.ema', 'p.gamma', 'p.last_bid', 'p.last_ask', 'p.min_bid', 'p.min_ask', 'p.bid', 'p.ask',
]

for c in NUM_COLS:
    if c in prod_valid.columns:
        prod_valid[c] = pd.to_numeric(prod_valid[c], errors='coerce')

our_df['time'] = our_df['time'].astype(int)
our_df['strike'] = our_df['strike'].astype(int)

merged = pd.merge(
    our_df, prod_valid[['time', 'strike'] + NUM_COLS],
    on=['time', 'strike'], how='inner', suffixes=('_OUR', '_PROD')
)

print(f"合併後: {len(merged)} 筆")
print()

all_ok = True
for col in NUM_COLS:
    our_c = col + '_OUR'
    prod_c = col + '_PROD'
    if our_c in merged.columns and prod_c in merged.columns:
        tol = 1e-4 if 'ema' in col else 0.01
        diff = (merged[our_c].fillna(-999) - merged[prod_c].fillna(-999)).abs() > tol
        cnt = diff.sum()
        if cnt > 0:
            all_ok = False
            first_idx = diff.idxmax()
            r = merged.loc[first_idx]
            print(f"[X] {col}: {cnt} 筆不一致")
            print(f"     首筆: time={int(r['time'])}, strike={int(r['strike'])}, PROD={r[prod_c]}, 我們={r[our_c]}")
        else:
            print(f"[OK] {col}: 全部一致")

print()
if all_ok:
    print("=== 全部數值欄位驗證通過！ ===")
else:
    print("=== 有差異，請檢查上方細節 ===")
