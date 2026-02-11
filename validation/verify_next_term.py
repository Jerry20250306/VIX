"""
驗證 Next Term 是否全天一致
"""
import pandas as pd
import numpy as np

# 讀取 PROD 和 OURS
prod_df = pd.read_csv(r'資料來源\20251231\NextPROD_20251231.tsv', sep='\t', dtype=str)
our_df = pd.read_csv('output/驗證20251231_NextPROD.csv')

# 格式化 PROD
prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)

# 數值欄位
NUM_COLS = [
    'c.ema', 'c.gamma', 'c.last_bid', 'c.last_ask', 'c.min_bid', 'c.min_ask', 'c.bid', 'c.ask',
    'p.ema', 'p.gamma', 'p.last_bid', 'p.last_ask', 'p.min_bid', 'p.min_ask', 'p.bid', 'p.ask',
]

for c in NUM_COLS:
    if c in prod_valid.columns:
        prod_valid[c] = pd.to_numeric(prod_valid[c], errors='coerce')

our_df['time'] = our_df['time'].astype(int)
our_df['strike'] = our_df['strike'].astype(int)

# 合併
merged = pd.merge(
    our_df, prod_valid[['time', 'strike'] + NUM_COLS],
    on=['time', 'strike'], how='inner', suffixes=('_OUR', '_PROD')
)

print(f"=== Next Term 全天驗證 (共 {len(merged)} 筆) ===\n")

all_ok = True
for col in NUM_COLS:
    our_c = col + '_OUR'
    prod_c = col + '_PROD'
    
    # 填補 -999 以避免 NaN 比較問題
    diff = (merged[our_c].fillna(-999) - merged[prod_c].fillna(-999)).abs() > 0.01
    cnt = diff.sum()
    
    if cnt > 0:
        all_ok = False
        print(f"[X] {col}: {cnt} 筆不一致")
    else:
        print(f"[OK] {col}: 100% 一致")

if all_ok:
    print("\n🎉 Next Term 也達成 100% 完全一致！")
else:
    print("\n⚠️ Next Term 仍有差異，請檢查。")
