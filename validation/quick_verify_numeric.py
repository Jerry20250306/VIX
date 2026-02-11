"""
快速驗證：撇除 outlier 欄位，只比對數值欄位是否一致
支援命令列參數：python quick_verify_numeric.py [Term] [Date]
預設: Near 20251231
"""
import pandas as pd
import numpy as np
import sys
import os

# 預設參數
term = 'Near'
date = '20251231'

if len(sys.argv) > 1:
    term = sys.argv[1]
if len(sys.argv) > 2:
    date = sys.argv[2]

prod_file = rf'資料來源\{date}\{term}PROD_{date}.tsv'
our_file = f'output/驗證{date}_{term}PROD.csv'

print(f"驗證目標: {term} Term, Date={date}")
print(f"PROD: {prod_file}")
print(f"OURS: {our_file}")

if not os.path.exists(prod_file) or not os.path.exists(our_file):
    print("檔案不存在，請檢查路徑")
    sys.exit(1)

prod_df = pd.read_csv(prod_file, sep='\t', dtype=str)
our_df = pd.read_csv(our_file)

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
        # 準備資料，處理 NaN
        # 邏輯：將 OUR 的 NaN 視為 0.0，然後與 PROD (已 fillna 0.0) 比較
        # 這樣 PROD=0.0, OUR=NaN 或是 PROD=0.0, OUR=0.0 都會被視為一致
        # 但 PROD=5.0, OUR=NaN 會是不一致 (5.0 vs 0.0)
        
        val_our = merged[our_c].fillna(0.0)
        val_prod = merged[prod_c].fillna(0.0)
        
        tol = 1e-4 if 'ema' in col else 0.01
        diff = (val_our - val_prod).abs() > tol
        cnt = diff.sum()
        
        if cnt > 0:
            all_ok = False
            first_idx = diff.idxmax()
            r = merged.loc[first_idx]
            # 為了印出原始值 (含 NaN)，我們回去查原始 column
            orig_our = merged.loc[first_idx, our_c]
            orig_prod = merged.loc[first_idx, prod_c]
            
            print(f"[X] {col}: {cnt} 筆不一致")
            print(f"     首筆: time={int(r['time'])}, strike={int(r['strike'])}, PROD={orig_prod}, 我們={orig_our}")
        else:
            print(f"[OK] {col}: 全部一致")

print()
if all_ok:
    print(f"=== {term} Term 全部數值欄位驗證通過！(含 0.0/NaN 容錯) ===")
else:
    print("=== 有差異，請檢查上方細節 ===")
