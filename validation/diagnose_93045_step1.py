"""使用 step1 輸出來診斷 Q_Min 問題"""
import pandas as pd

# 讀取 step1
step1 = pd.read_csv('output/驗證20251231_Near_step1.csv', low_memory=False)

# 找 time=93030 和 93045
row_93030 = step1[(step1['Time'] == 93030) & (step1['Strike'] == 31400) & (step1['CP'] == 'Call')]
row_93045 = step1[(step1['Time'] == 93045) & (step1['Strike'] == 31400) & (step1['CP'] == 'Call')]

if len(row_93030) > 0:
    r = row_93030.iloc[0]
    print("=== time=93030 ===")
    print(f"Snapshot_SysID: {r['Snapshot_SysID']}")
    print(f"Q_Min: bid={r['Q_Min_Valid_Bid']}, ask={r['Q_Min_Valid_Ask']}")
    print(f"Q_Last: bid={r['Q_Last_Valid_Bid']}, ask={r['Q_Last_Valid_Ask']}")

if len(row_93045) > 0:
    r = row_93045.iloc[0]
    print("\n=== time=93045 ===")
    print(f"Snapshot_SysID: {r['Snapshot_SysID']}")
    print(f"Q_Min: bid={r['Q_Min_Valid_Bid']}, ask={r['Q_Min_Valid_Ask']}")
    print(f"Q_Last: bid={r['Q_Last_Valid_Bid']}, ask={r['Q_Last_Valid_Ask']}")

# 讀取原始 tick 資料
print("\n=== 原始 tick 資料分析 ===")
raw = pd.read_csv(r'資料來源\J002-11300041_20251231\temp\J002-11300041_20251231_TXOA6.csv', 
                  sep='\t', dtype=str)

raw_filtered = raw[raw['svel_i081_prod_id'].str.contains('TXO31400A6', na=False)].copy()
raw_filtered['bid'] = pd.to_numeric(raw_filtered['svel_i081_best_buy_price1'], errors='coerce')
raw_filtered['ask'] = pd.to_numeric(raw_filtered['svel_i081_best_sell_price1'], errors='coerce')
raw_filtered['seqno'] = pd.to_numeric(raw_filtered['svel_i081_seqno'], errors='coerce')
raw_filtered['spread'] = raw_filtered['ask'] - raw_filtered['bid']
raw_filtered['valid'] = (raw_filtered['bid'] >= 0) & (raw_filtered['ask'] > 0) & (raw_filtered['ask'] > raw_filtered['bid'])

if len(row_93030) > 0 and len(row_93045) > 0:
    sys_id_93030 = row_93030.iloc[0]['Snapshot_SysID']
    sys_id_93045 = row_93045.iloc[0]['Snapshot_SysID']
    
    print(f"\nsys_id_93030 = {sys_id_93030}")
    print(f"sys_id_93045 = {sys_id_93045}")
    
    # 找小於 sys_id_93045 的最後一個 tick
    before_93045 = raw_filtered[raw_filtered['seqno'] < sys_id_93045].copy()
    if len(before_93045) > 0:
        last = before_93045.iloc[-1]
        print(f"\n小於 sys_id_93045 的最後一個 tick (q_last_at_prev):")
        print(f"  seqno={last['seqno']:.0f}, bid={last['bid']:.1f}, ask={last['ask']:.1f}, spread={last['spread']:.1f}, valid={last['valid']}")
    
    # 找 sys_id_93030 ~ sys_id_93045 區間的 ticks
    in_range = raw_filtered[
        (raw_filtered['seqno'] >= sys_id_93030) & 
        (raw_filtered['seqno'] < sys_id_93045)
    ].copy()
    
    print(f"\nsys_id_93030 ~ sys_id_93045 區間內的 ticks: {len(in_range)} 筆")
    for idx, t in in_range.iterrows():
        print(f"  seqno={t['seqno']:.0f}, bid={t['bid']:.1f}, ask={t['ask']:.1f}, spread={t['spread']:.1f}, valid={t['valid']}")
    
    # 找有效的 ticks
    valid_in_range = in_range[in_range['valid'] == True]
    print(f"\n區間內有效的 ticks: {len(valid_in_range)} 筆")
    for idx, t in valid_in_range.iterrows():
        print(f"  seqno={t['seqno']:.0f}, bid={t['bid']:.1f}, ask={t['ask']:.1f}, spread={t['spread']:.1f}")
