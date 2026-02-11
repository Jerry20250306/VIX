"""
找出除了 0.0 vs NaN 以外的 Next Term 差異
"""
import pandas as pd
import numpy as np

prod_df = pd.read_csv(r'資料來源\20251231\NextPROD_20251231.tsv', sep='\t', dtype=str)
our_df = pd.read_csv('output/驗證20251231_NextPROD.csv')

prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)

# 檢查 c.min_bid
prod_valid['c.min_bid'] = pd.to_numeric(prod_valid['c.min_bid'], errors='coerce')
our_df['time'] = our_df['time'].astype(int)
our_df['strike'] = our_df['strike'].astype(int)

merged = pd.merge(
    our_df, prod_valid[['time', 'strike', 'c.min_bid']],
    on=['time', 'strike'], how='inner', suffixes=('_OUR', '_PROD')
)

diff = (merged['c.min_bid_OUR'].fillna(-999) - merged['c.min_bid_PROD'].fillna(-999)).abs() > 0.01

# 排除 PROD=0.0 且 OUR=NaN 的情況
# (注意: OUR 讀進來是 numeric, NaN)
real_diff = merged[diff & ~((merged['c.min_bid_PROD'] == 0) & (merged['c.min_bid_OUR'].isna()))]

print(f"排除 0.0/NaN 後的真正差異筆數: {len(real_diff)}")
if len(real_diff) > 0:
    print(real_diff.head())
