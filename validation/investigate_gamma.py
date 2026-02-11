"""
調查原始 Ticks - Strike 30000 Call
搜尋區間: 22934 < SeqNo <= 57695 (084515 的正確範圍)
"""
import pandas as pd
import glob
import os
import sys

# 加入父目錄以引用 vix_utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from vix_utils import get_vix_config

config = get_vix_config()
raw_dir = config["raw_dir"]
if not raw_dir:
    print("Error: Could not resolve raw_dir")
    sys.exit(1)

all_files = glob.glob(os.path.join(raw_dir, "*.csv"))

prev_sys_id = 22934  # Line 2 (054500)
target_sys_id = 57695  # 084515

print(f"搜尋原始資料: Strike=30000, Call (Near Term = A6)")
print(f"SeqNo 範圍: {prev_sys_id} < SeqNo <= {target_sys_id}")

# 只讀 Near Term Call (TXO...A6)
for f in all_files:
    if "TXOA6" not in f:
        continue
    try:
        df = pd.read_csv(f, sep='\t', dtype={'svel_i081_prod_id': str})
        
        # 篩選商品 (Strike 30000 Call = TXO30000A6)
        mask_prod = df['svel_i081_prod_id'] == 'TXO30000A6'
        df = df[mask_prod]
        
        # 篩選 SeqNo 區間
        df = df[(df['svel_i081_seqno'] > prev_sys_id) & (df['svel_i081_seqno'] <= target_sys_id)]
        
        if not df.empty:
            df['Spread'] = df['svel_i081_best_sell_price1'] - df['svel_i081_best_buy_price1']
            
            print(f"\nFile: {os.path.basename(f)}")
            print(f"共 {len(df)} 筆報價")
            print(df[['svel_i081_seqno', 'svel_i081_best_buy_price1', 'svel_i081_best_sell_price1', 'Spread']].to_string())
            
            # 找 Min Spread
            min_spread = df['Spread'].min()
            min_row = df[df['Spread'] == min_spread].iloc[0]
            print(f"\nMin Spread: {min_spread}")
            print(f"  Bid: {min_row['svel_i081_best_buy_price1']}, Ask: {min_row['svel_i081_best_sell_price1']}")
    except Exception as e:
        print(f"Error: {e}")

