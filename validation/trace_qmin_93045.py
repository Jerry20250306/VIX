"""
從重建報價角度，追蹤 time=93045, strike=31400 (Call) 的 Q_Min 選取過程
顯示該時間區段附近的所有報價資訊
"""
import pandas as pd
import numpy as np

# ==============================
# 1. 讀取原始 tick 資料
# ==============================
raw = pd.read_csv(
    r'資料來源\J002-11300041_20251231\temp\J002-11300041_20251231_TXOA6.csv',
    sep='\t', dtype=str
)

# 篩選 TXO31400A6（Near, Strike=31400, Call）
target_prod = raw[raw['svel_i081_prod_id'].str.contains('TXO31400A6', na=False)].copy()
target_prod['bid'] = pd.to_numeric(target_prod['svel_i081_best_buy_price1'], errors='coerce')
target_prod['ask'] = pd.to_numeric(target_prod['svel_i081_best_sell_price1'], errors='coerce')
target_prod['seqno'] = pd.to_numeric(target_prod['svel_i081_seqno'], errors='coerce').astype(int)
target_prod['time_raw'] = target_prod['svel_i081_time'].str[:6]
target_prod['spread'] = target_prod['ask'] - target_prod['bid']
target_prod['valid'] = (target_prod['bid'] >= 0) & (target_prod['ask'] > 0) & (target_prod['ask'] > target_prod['bid'])

# ==============================
# 2. 讀取 step1 取得 Snapshot_SysID
# ==============================
step1 = pd.read_csv('output/驗證20251231_Near_step1.csv', low_memory=False)
step1_call = step1[(step1['CP'] == 'Call') & (step1['Strike'] == 31400)]

# 取得幾個連續時間點的 sys_id
target_times = [93015, 93030, 93045, 93100, 93115]
print("=== 時間點的 Snapshot_SysID 對照 ===\n")
sys_ids = {}
for t in target_times:
    row = step1_call[step1_call['Time'] == t]
    if len(row) > 0:
        sid = int(row.iloc[0]['Snapshot_SysID'])
        sys_ids[t] = sid
        r = row.iloc[0]
        print(f"time={t}: SysID={sid}")
        print(f"  Q_Last_Valid: bid={r['Q_Last_Valid_Bid']}, ask={r['Q_Last_Valid_Ask']}")
        print(f"  Q_Min_Valid:  bid={r['Q_Min_Valid_Bid']}, ask={r['Q_Min_Valid_Ask']}")
        if not pd.isna(r['Q_Last_Valid_Bid']):
            last_spread = r['Q_Last_Valid_Ask'] - r['Q_Last_Valid_Bid']
            min_spread = r['Q_Min_Valid_Ask'] - r['Q_Min_Valid_Bid']
            print(f"  Q_Last spread={last_spread:.2f}, Q_Min spread={min_spread:.2f}")
        print()

# ==============================
# 3. 從原始 tick 顯示 93030~93045 區間
# ==============================
if 93030 in sys_ids and 93045 in sys_ids:
    sid_start = sys_ids[93030]
    sid_end = sys_ids[93045]
    
    # q_last_at_prev: 小於 sid_start 的最後一個 tick
    before = target_prod[target_prod['seqno'] < sid_start]
    print(f"=== q_last_at_prev（小於 SysID={sid_start} 的最後一個 tick）===")
    if len(before) > 0:
        last = before.iloc[-1]
        print(f"seqno={last['seqno']}, time={last['time_raw']}, bid={last['bid']:.1f}, ask={last['ask']:.1f}, spread={last['spread']:.1f}, valid={last['valid']}")
    else:
        print("沒有找到")
    
    # 區間內的 ticks
    in_range = target_prod[(target_prod['seqno'] >= sid_start) & (target_prod['seqno'] < sid_end)]
    print(f"\n=== SysID {sid_start}~{sid_end} 區間內的 ticks（共 {len(in_range)} 筆）===")
    for _, t in in_range.iterrows():
        marker = " ← spread 最小" if t['spread'] == in_range[in_range['valid']]['spread'].min() else ""
        print(f"seqno={t['seqno']}, time={t['time_raw']}, bid={t['bid']:.1f}, ask={t['ask']:.1f}, spread={t['spread']:.1f}, valid={t['valid']}{marker}")
    
    # 模擬 Q_Min 計算
    print(f"\n=== 模擬 Q_Min 計算 ===")
    
    # 候選 1: q_last_at_prev
    if len(before) > 0:
        prev = before.iloc[-1]
        if prev['valid']:
            min_spread = prev['spread']
            min_seqno = prev['seqno']
            min_bid = prev['bid']
            min_ask = prev['ask']
            print(f"初始化（q_last_at_prev）: bid={min_bid:.1f}, ask={min_ask:.1f}, spread={min_spread:.1f}, seqno={min_seqno}")
        else:
            min_spread = float('inf')
            min_seqno = -1
            min_bid = np.nan
            min_ask = np.nan
            print(f"q_last_at_prev 無效，初始化為 inf")
    
    # 掃描區間內有效 ticks
    for _, t in in_range.iterrows():
        if not t['valid']:
            continue
        s = t['spread']
        seq = t['seqno']
        if s < min_spread or (s == min_spread and seq > min_seqno):
            print(f"  更新: bid={t['bid']:.1f}, ask={t['ask']:.1f}, spread={s:.1f}, seqno={seq} (條件: {'spread更小' if s < min_spread else 'spread相同但更新'})")
            min_spread = s
            min_seqno = seq
            min_bid = t['bid']
            min_ask = t['ask']
    
    print(f"\n最終 Q_Min: bid={min_bid:.1f}, ask={min_ask:.1f}, spread={min_spread:.1f}, seqno={min_seqno}")
    
    # Tie-breaking: 檢查 Q_Last
    last_tick_before_end = target_prod[target_prod['seqno'] < sid_end]
    if len(last_tick_before_end) > 0:
        q_last = last_tick_before_end.iloc[-1]
        if q_last['valid']:
            last_spread = q_last['spread']
            print(f"Q_Last_Valid: bid={q_last['bid']:.1f}, ask={q_last['ask']:.1f}, spread={last_spread:.1f}")
            if abs(last_spread - min_spread) < 1e-9:
                print(f"  → Tie-breaking: Q_Last.spread == Q_Min.spread，用 Q_Last")
                min_bid = q_last['bid']
                min_ask = q_last['ask']
            else:
                print(f"  → Q_Last.spread ({last_spread:.1f}) != Q_Min.spread ({min_spread:.1f})，不觸發 tie-breaking")
    
    print(f"\n最終結果: bid={min_bid:.1f}, ask={min_ask:.1f}")

    # PROD 值
    prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
    prod_valid = prod_df[(prod_df['time'] == '93045') & (prod_df['strike'] == '31400')]
    if len(prod_valid) > 0:
        p = prod_valid.iloc[0]
        print(f"PROD c.min: bid={p['c.min_bid']}, ask={p['c.min_ask']}")
