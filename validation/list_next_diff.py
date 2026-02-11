"""
找出 Next Term 的具體差異案例 (包含 Ask)
"""
import pandas as pd
import numpy as np

prod_df = pd.read_csv(r'資料來源\20251231\NextPROD_20251231.tsv', sep='\t', dtype=str)
our_df = pd.read_csv('output/驗證20251231_NextPROD.csv')

prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)

cols_to_check = ['c.min_bid', 'c.min_ask', 'c.last_bid', 'c.last_ask']
for c in cols_to_check:
    prod_valid[c] = pd.to_numeric(prod_valid[c], errors='coerce')

our_df['time'] = our_df['time'].astype(int)
our_df['strike'] = our_df['strike'].astype(int)

merged = pd.merge(
    our_df, prod_valid[['time', 'strike'] + cols_to_check],
    on=['time', 'strike'], how='inner', suffixes=('_OUR', '_PROD')
)

# 找 c.min_bid 差異
diff = (merged['c.min_bid_OUR'].fillna(-999) - merged['c.min_bid_PROD'].fillna(-999)).abs() > 0.01
diff_rows = merged[diff].copy()

print(f"=== Next Term c.min_bid 差異: {len(diff_rows)} 筆 ===\n")
for idx, row in diff_rows.head(10).iterrows():
    print(f"time={int(row['time'])}, strike={int(row['strike'])}")
    print(f"  PROD c.min: {row['c.min_bid_PROD']:.1f}/{row['c.min_ask_PROD']:.1f}")
    print(f"  OUR  c.min: {row['c.min_bid_OUR']:.1f}/{row['c.min_ask_OUR']:.1f}")
    print()
