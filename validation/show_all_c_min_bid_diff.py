"""
快速驗證：列出所有 c.min_bid 差異
"""
import pandas as pd
import numpy as np

prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
our_df = pd.read_csv('output/驗證20251231_NearPROD.csv')

prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)

# 轉換數值欄位
for c in ['c.min_bid', 'c.min_ask']:
    if c in prod_valid.columns:
        prod_valid[c] = pd.to_numeric(prod_valid[c], errors='coerce')

our_df['time'] = our_df['time'].astype(int)
our_df['strike'] = our_df['strike'].astype(int)

merged = pd.merge(
    our_df, prod_valid[['time', 'strike', 'c.min_bid', 'c.min_ask']],
    on=['time', 'strike'], how='inner', suffixes=('_OUR', '_PROD')
)

# 找 c.min_bid 差異
diff = (merged['c.min_bid_OUR'].fillna(-999) - merged['c.min_bid_PROD'].fillna(-999)).abs() > 0.01
diff_rows = merged[diff].copy()

print(f"=== c.min_bid 差異：共 {len(diff_rows)} 筆 ===\n")

for idx, row in diff_rows.iterrows():
    print(f"time={int(row['time'])}, strike={int(row['strike'])}")
    print(f"  PROD: bid={row['c.min_bid_PROD']:.1f}, ask={row['c.min_ask_PROD']:.1f}")
    print(f"  我們: bid={row['c.min_bid_OUR']:.1f}, ask={row['c.min_ask_OUR']:.1f}")
    print(f"  差異: {abs(row['c.min_bid_OUR'] - row['c.min_bid_PROD']):.1f}")
    print()
