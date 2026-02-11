"""查看區間內所有 spread=0.4 的 tick，確認 PROD 是否選最新"""
import pandas as pd

# 讀取原始 tick 資料
near_ticks = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str, nrows=50000)

# 過濾 time=93045, strike=31400, Call
# time 格式可能是 093045 或 93045
target_time = 93045
target_strike = 31400

# 找出這個時間點之前 15 秒內的所有 ticks
# 93045 - 15 秒 = 93030
start_time = target_time - 15
end_time = target_time

print(f"查找 time={start_time}~{end_time}, strike={target_strike}, Call 的所有 ticks\n")

# 過濾資料
filtered = near_ticks[
    (near_ticks['strike'] == str(target_strike)) &
    (near_ticks['time'].notna())
].copy()

# 轉換 time 為整數
filtered['time_int'] = pd.to_numeric(filtered['time'], errors='coerce').astype('Int64')

# 過濾時間範圍
in_range = filtered[
    (filtered['time_int'] >= start_time) &
    (filtered['time_int'] <= end_time)
].copy()

print(f"找到 {len(in_range)} 筆 ticks\n")

if len(in_range) > 0:
    # 計算 Call 的 spread
    in_range['c.bid'] = pd.to_numeric(in_range['c.bid'], errors='coerce')
    in_range['c.ask'] = pd.to_numeric(in_range['c.ask'], errors='coerce')
    in_range['c.spread'] = in_range['c.ask'] - in_range['c.bid']
    
    # 顯示所有 ticks
    print("所有 ticks:")
    for idx, r in in_range.iterrows():
        print(f"  time={r['time_int']}, bid={r['c.bid']}, ask={r['c.ask']}, spread={r['c.spread']:.2f}")
    
    # 找 spread 最小的
    min_spread = in_range['c.spread'].min()
    print(f"\n最小 spread: {min_spread:.2f}")
    
    # 找所有 spread=min_spread 的 ticks
    min_ticks = in_range[in_range['c.spread'] == min_spread].copy()
    print(f"\nspread={min_spread:.2f} 的 ticks 有 {len(min_ticks)} 筆:")
    for idx, r in min_ticks.iterrows():
        print(f"  time={r['time_int']}, bid={r['c.bid']}, ask={r['c.ask']}")
    
    # 最新的是哪一筆？
    if len(min_ticks) > 0:
        newest = min_ticks.iloc[-1]  # 最後一筆
        print(f"\n最新的 tick (最後一筆):")
        print(f"  time={newest['time_int']}, bid={newest['c.bid']}, ask={newest['c.ask']}")
        
        # PROD 選了哪一筆？
        prod_min_bid = 7.3
        prod_min_ask = 7.7
        
        print(f"\nPROD 選了: bid={prod_min_bid}, ask={prod_min_ask}")
        
        # 我們選了哪一筆？
        our_min_bid = 7.4
        our_min_ask = 7.8
        
        print(f"我們選了: bid={our_min_bid}, ask={our_min_ask}")
