"""診斷 Q_Min SeqNo 範圍問題"""
import pandas as pd

# 讀取我們的 step1 輸出
step1 = pd.read_csv('output/驗證20251231_Near_step1.csv', low_memory=False)

# 看 time=93045, strike=31400, Call
row = step1[(step1['Time'] == 93045) & (step1['Strike'] == 31400) & (step1['CP'] == 'Call')]

if len(row) > 0:
    r = row.iloc[0]
    print("=== step1 輸出 (time=93045, strike=31400, Call) ===")
    print(f"Snapshot_SysID: {r['Snapshot_SysID']}")
    print(f"Q_Min_Valid_Bid: {r['Q_Min_Valid_Bid']}")
    print(f"Q_Min_Valid_Ask: {r['Q_Min_Valid_Ask']}")
    print(f"Q_Last_Valid_Bid: {r['Q_Last_Valid_Bid']}")
    print(f"Q_Last_Valid_Ask: {r['Q_Last_Valid_Ask']}")
    
    # 看前一個時間點
    prev_row = step1[(step1['Time'] == 93030) & (step1['Strike'] == 31400) & (step1['CP'] == 'Call')]
    if len(prev_row) > 0:
        p = prev_row.iloc[0]
        print(f"\n=== 前一時間點 (time=93030) ===")
        print(f"Snapshot_SysID: {p['Snapshot_SysID']}")
        print(f"Q_Min_Valid_Bid: {p['Q_Min_Valid_Bid']}")
        print(f"Q_Min_Valid_Ask: {p['Q_Min_Valid_Ask']}")
        print(f"Q_Last_Valid_Bid: {p['Q_Last_Valid_Bid']}")
        print(f"Q_Last_Valid_Ask: {p['Q_Last_Valid_Ask']}")

# 讀取原始 tick 資料
print("\n=== 原始 tick 資料 ===")
raw = pd.read_csv(r'資料來源\J002-11300041_20251231\temp\J002-11300041_20251231_TXOA6.csv', 
                  sep='\t', dtype=str)

# 找 strike=31400
raw_filtered = raw[raw['svel_i081_prod_id'].str.contains('TXO31400A6', na=False)].copy()
raw_filtered['time'] = raw_filtered['svel_i081_time'].str[:6]
raw_filtered['bid'] = pd.to_numeric(raw_filtered['svel_i081_best_buy_price1'], errors='coerce')
raw_filtered['ask'] = pd.to_numeric(raw_filtered['svel_i081_best_sell_price1'], errors='coerce')
raw_filtered['seqno'] = pd.to_numeric(raw_filtered['svel_i081_seqno'], errors='coerce')
raw_filtered['spread'] = raw_filtered['ask'] - raw_filtered['bid']

# 找 bid=7.4, ask=7.8 的 tick
tick_74_78 = raw_filtered[(raw_filtered['bid'] == 7.4) & (raw_filtered['ask'] == 7.8)]
print(f"\nbid=7.4, ask=7.8 的 ticks: {len(tick_74_78)} 筆")
if len(tick_74_78) > 0:
    print("前 5 筆:")
    for idx, t in tick_74_78.head(5).iterrows():
        print(f"  time={t['time']}, seqno={t['seqno']:.0f}, spread={t['spread']:.1f}")

# 找 bid=7.3, ask=7.7 的 tick
tick_73_77 = raw_filtered[(raw_filtered['bid'] == 7.3) & (raw_filtered['ask'] == 7.7)]
print(f"\nbid=7.3, ask=7.7 的 ticks: {len(tick_73_77)} 筆")
if len(tick_73_77) > 0:
    print("所有筆:")
    for idx, t in tick_73_77.iterrows():
        print(f"  time={t['time']}, seqno={t['seqno']:.0f}, spread={t['spread']:.1f}")

# 看 time=093030 附近的所有 ticks
print("\n=== time=093025~093035 的所有 ticks ===")
nearby = raw_filtered[(raw_filtered['time'] >= '093025') & (raw_filtered['time'] <= '093035')].copy()
nearby = nearby.sort_values('seqno')
for idx, t in nearby.iterrows():
    print(f"  time={t['time']}, bid={t['bid']:.1f}, ask={t['ask']:.1f}, spread={t['spread']:.1f}, seqno={t['seqno']:.0f}")
