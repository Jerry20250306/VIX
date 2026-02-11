"""
使用 RawDataLoader 直接讀取並檢查 32500 Put 的資料
"""
import sys
import os
import pandas as pd

# 加入專案路徑
sys.path.insert(0, os.getcwd())
from vix_utils import get_vix_config
from step0_valid_quotes import RawDataLoader

# 取得設定
config = get_vix_config("20251231")
item = config['target_date']
print(f"Target Date: {item}")
print(f"Raw Dir: {config['raw_dir']}")

loader = RawDataLoader(config['raw_dir'], item)
near_df, next_df, terms = loader.load_and_filter()

print(f"Near: {len(near_df)} ticks")
print(f"Next: {len(next_df)} ticks")

# Convert time to int
next_df['svel_i081_time'] = pd.to_numeric(next_df['svel_i081_time'], errors='coerce')

# 檢查 Next Term 中的 32500 Put (不濾時間，只看前 10 筆)
target = next_df[
    (next_df['Strike'] == 32500) & 
    (next_df['CP'] == 'Put')
].copy()

print(f"=== Raw Ticks (32500 Put) Found: {len(target)} ===")
if len(target) > 0:
    for i, row in target.head(10).iterrows():
        print(f"Time: {row['svel_i081_time']}")
        print(f"  Prod: {row['svel_i081_prod_id']}")
        print(f"  Bid: {row['svel_i081_best_buy_price1']}")
        print(f"  Ask: {row['svel_i081_best_sell_price1']}")
        print(f"  Seq: {row['svel_i081_seqno']}")
        print("-" * 20)
else:
    print("No ticks found for 32500 Put in Next Term.")
    # Check if they are in Near Term?
    target_near = near_df[(near_df['Strike'] == 32500) & (near_df['CP'] == 'Put')]
    print(f"In Near Term? {len(target_near)} ticks")
    
    # Check raw prod id in full df?
    # Cannot access full_df here, but we can sample next_df
    print("Sample Next Term Data:")
    print(next_df[['svel_i081_prod_id', 'Strike', 'CP', 'YM']].head())
