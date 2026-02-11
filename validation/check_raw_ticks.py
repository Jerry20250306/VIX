"""查看原始行情檔案中 strike=31400, time=093030~093045 的所有 ticks"""
import pandas as pd
import os
import sys
import glob

# 加入父目錄以引用 vix_utils
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from vix_utils import get_vix_config

config = get_vix_config()
raw_dir = config["raw_dir"]
if not raw_dir:
    print("Error: Could not resolve raw_dir")
    sys.exit(1)

# 自動尋找包含 TXOA6 的 CSV 檔案
files = glob.glob(os.path.join(raw_dir, "*TXOA6.csv"))
if not files:
    print(f"Error: No *TXOA6.csv found in {raw_dir}")
    sys.exit(1)
target_file = files[0]
print(f"Reading file: {target_file}")

# 讀取原始行情檔案
df = pd.read_csv(target_file, sep='\t', dtype=str) # 修正：恢復使用 Tab 分隔，因為原始檔案雖名為 CSV 但內容為 Tab 分隔
# 原本程式碼用 sep='\t' 但 check_raw_ticks.py 原文用 sep='\t'? 
# 查看原文：df = pd.read_csv(..., sep='\t', ...)
# 但如果是 .csv 通常是逗號？ 
# 讓我們檢查一下 raw_data_loader 怎麼讀的：pd.read_csv(f) -> default comma.
# 但這裡原文寫 sep='\t'。可能之前作者測試時用了 tab 分隔？
# 不過 raw_data_loader 用預設 (comma)，所以這裡我們改回預設（去掉 sep）或者用 comma
# 為了保險，先不指定 sep，讓它預設 (comma)，因為副檔名是 csv

print(f"總筆數: {len(df)}")
print(f"欄位: {df.columns.tolist()}\n")

# 找 strike=31400 (TXO31400A6) 的所有 ticks
df_filtered = df[df['svel_i081_prod_id'].str.contains('TXO31400A6', na=False)].copy()
print(f"strike=31400 的總 ticks: {len(df_filtered)}")

# 提取時間、bid、ask
df_filtered['time'] = df_filtered['svel_i081_time'].str[:6]  # 取前6位作為時間
df_filtered['bid'] = pd.to_numeric(df_filtered['svel_i081_best_buy_price1'], errors='coerce')
df_filtered['ask'] = pd.to_numeric(df_filtered['svel_i081_best_sell_price1'], errors='coerce')
df_filtered['seqno'] = pd.to_numeric(df_filtered['svel_i081_seqno'], errors='coerce')

# 過濾時間範圍 093030~093045
in_range = df_filtered[(df_filtered['time'] >= '093030') & (df_filtered['time'] <= '093045')].copy()
print(f"\ntime=093030~093045 的 ticks: {len(in_range)} 筆\n")

# 計算 spread
in_range['spread'] = in_range['ask'] - in_range['bid']

# 顯示所有 ticks
print("所有 ticks:")
for idx, r in in_range.iterrows():
    print(f"  time={r['time']}, bid={r['bid']:.1f}, ask={r['ask']:.1f}, spread={r['spread']:.1f}, seqno={r['seqno']:.0f}")

# 找 spread 最小的
if len(in_range) > 0:
    min_spread = in_range['spread'].min()
    print(f"\n最小 spread: {min_spread:.1f}")
    
    # 找所有 spread=min_spread 的 ticks
    min_ticks = in_range[in_range['spread'] == min_spread].copy()
    print(f"\nspread={min_spread:.1f} 的 ticks 有 {len(min_ticks)} 筆:")
    for idx, r in min_ticks.iterrows():
        print(f"  time={r['time']}, bid={r['bid']:.1f}, ask={r['ask']:.1f}, seqno={r['seqno']:.0f}")
    
    # 找 seqno 最大的（最新）
    if len(min_ticks) > 0:
        newest = min_ticks.loc[min_ticks['seqno'].idxmax()]
        print(f"\nSeqNo 最大（最新）的 tick:")
        print(f"  time={newest['time']}, bid={newest['bid']:.1f}, ask={newest['ask']:.1f}, seqno={newest['seqno']:.0f}")
        
        print(f"\nPROD 選了: bid=7.3, ask=7.7")
        print(f"我們選了: bid=7.4, ask=7.8")
        
        # 檢查 7.3/7.7 是否存在
        match = min_ticks[(min_ticks['bid'] == 7.3) & (min_ticks['ask'] == 7.7)]
        if len(match) > 0:
            print(f"\n[OK] 找到 bid=7.3, ask=7.7 的 tick!")
            print(f"  seqno={match.iloc[0]['seqno']:.0f}")
        else:
            print(f"\n[FAIL] 沒有找到 bid=7.3, ask=7.7 的 tick")
