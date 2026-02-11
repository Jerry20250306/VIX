"""詳細診斷 time=93045, strike=31400 的 Q_Min 問題"""
import pandas as pd
import numpy as np

# 讀取原始 tick 資料
raw = pd.read_csv(r'資料來源\J002-11300041_20251231\temp\J002-11300041_20251231_TXOA6.csv', 
                  sep='\t', dtype=str)

# 找 strike=31400 (TXO31400A6) 的所有 ticks
raw_filtered = raw[raw['svel_i081_prod_id'].str.contains('TXO31400A6', na=False)].copy()
raw_filtered['time'] = raw_filtered['svel_i081_time'].str[:6]
raw_filtered['bid'] = pd.to_numeric(raw_filtered['svel_i081_best_buy_price1'], errors='coerce')
raw_filtered['ask'] = pd.to_numeric(raw_filtered['svel_i081_best_sell_price1'], errors='coerce')
raw_filtered['seqno'] = pd.to_numeric(raw_filtered['svel_i081_seqno'], errors='coerce')
raw_filtered['spread'] = raw_filtered['ask'] - raw_filtered['bid']

# 有效性判斷
raw_filtered['valid'] = (raw_filtered['bid'] >= 0) & (raw_filtered['ask'] > 0) & (raw_filtered['ask'] > raw_filtered['bid'])

# 讀取 PROD 的時間點定義
prod_df = pd.read_csv(r'資料來源\20251231\NearPROD_20251231.tsv', sep='\t', dtype=str)
prod_valid = prod_df[prod_df['strike'].notna() & (prod_df['strike'] != '')].copy()
prod_valid['time'] = prod_valid['time'].astype(int)
prod_valid['strike'] = prod_valid['strike'].astype(int)
prod_valid['sys_id'] = pd.to_numeric(prod_valid['sys_id'], errors='coerce')

# 找 time=93030 和 93045 的 sys_id
time_93030 = prod_valid[(prod_valid['time'] == 93030) & (prod_valid['strike'] == 31400)]
time_93045 = prod_valid[(prod_valid['time'] == 93045) & (prod_valid['strike'] == 31400)]

if len(time_93030) > 0 and len(time_93045) > 0:
    sys_id_93030 = time_93030.iloc[0]['sys_id']
    sys_id_93045 = time_93045.iloc[0]['sys_id']
    
    print(f"=== 時間點定義 ===")
    print(f"time=93030: sys_id={sys_id_93030}")
    print(f"time=93045: sys_id={sys_id_93045}")
    
    # 找出 93030 區間的 ticks（小於 sys_id_93030）
    ticks_before_93030 = raw_filtered[raw_filtered['seqno'] < sys_id_93030].copy()
    print(f"\n=== 小於 sys_id={sys_id_93030} 的最後一個 tick (q_last_at_prev for 93030) ===")
    if len(ticks_before_93030) > 0:
        last_before_93030 = ticks_before_93030.iloc[-1]
        print(f"seqno={last_before_93030['seqno']:.0f}, bid={last_before_93030['bid']:.1f}, ask={last_before_93030['ask']:.1f}, spread={last_before_93030['spread']:.1f}, valid={last_before_93030['valid']}")
    
    # 找出 93030~93045 區間的 ticks
    ticks_93030_to_93045 = raw_filtered[
        (raw_filtered['seqno'] >= sys_id_93030) & 
        (raw_filtered['seqno'] < sys_id_93045)
    ].copy()
    print(f"\n=== sys_id={sys_id_93030}~{sys_id_93045} 區間內的 ticks ===")
    print(f"總共 {len(ticks_93030_to_93045)} 筆")
    for idx, t in ticks_93030_to_93045.iterrows():
        print(f"  seqno={t['seqno']:.0f}, bid={t['bid']:.1f}, ask={t['ask']:.1f}, spread={t['spread']:.1f}, valid={t['valid']}, time={t['time']}")
    
    # 找出小於 sys_id_93045 的最後一個 tick (q_last_at_prev for 93045)
    ticks_before_93045 = raw_filtered[raw_filtered['seqno'] < sys_id_93045].copy()
    print(f"\n=== 小於 sys_id={sys_id_93045} 的最後一個 tick (q_last_at_prev for 93045) ===")
    if len(ticks_before_93045) > 0:
        last_before_93045 = ticks_before_93045.iloc[-1]
        print(f"seqno={last_before_93045['seqno']:.0f}, bid={last_before_93045['bid']:.1f}, ask={last_before_93045['ask']:.1f}, spread={last_before_93045['spread']:.1f}, valid={last_before_93045['valid']}")
    
    # 模擬 Q_Min 計算（for 93045）
    print(f"\n=== 模擬 Q_Min 計算 (time=93045) ===")
    
    # 候選 1: q_last_at_prev
    print(f"候選 1 (q_last_at_prev): bid={last_before_93045['bid']:.1f}, ask={last_before_93045['ask']:.1f}, spread={last_before_93045['spread']:.1f}, seqno={last_before_93045['seqno']:.0f}, valid={last_before_93045['valid']}")
    
    # 候選 2~N: 區間內的 ticks
    ticks_in_range = raw_filtered[
        (raw_filtered['seqno'] >= sys_id_93030) & 
        (raw_filtered['seqno'] < sys_id_93045) &
        (raw_filtered['valid'] == True)
    ].copy()
    
    print(f"\n區間內的有效 ticks:")
    for idx, t in ticks_in_range.iterrows():
        print(f"  候選: bid={t['bid']:.1f}, ask={t['ask']:.1f}, spread={t['spread']:.1f}, seqno={t['seqno']:.0f}")
    
    # 找 spread 最小且 seqno 最大的
    all_candidates = []
    
    # 加入 q_last_at_prev（如果有效）
    if last_before_93045['valid']:
        all_candidates.append({
            'bid': last_before_93045['bid'],
            'ask': last_before_93045['ask'],
            'spread': last_before_93045['spread'],
            'seqno': last_before_93045['seqno']
        })
    
    # 加入區間內的有效 ticks
    for idx, t in ticks_in_range.iterrows():
        all_candidates.append({
            'bid': t['bid'],
            'ask': t['ask'],
            'spread': t['spread'],
            'seqno': t['seqno']
        })
    
    if all_candidates:
        # 找 spread 最小
        min_spread = min(c['spread'] for c in all_candidates)
        min_candidates = [c for c in all_candidates if c['spread'] == min_spread]
        
        # 在 spread 最小的候選中，找 seqno 最大
        best = max(min_candidates, key=lambda c: c['seqno'])
        
        print(f"\n最終 Q_Min: bid={best['bid']:.1f}, ask={best['ask']:.1f}, spread={best['spread']:.1f}, seqno={best['seqno']:.0f}")
        
        # 比對 PROD
        prod_row = prod_valid[(prod_valid['time'] == 93045) & (prod_valid['strike'] == 31400)]
        if len(prod_row) > 0:
            p = prod_row.iloc[0]
            print(f"\nPROD c.min: bid={p['c.min_bid']}, ask={p['c.min_ask']}")
            print(f"我們的 Q_Min: bid={best['bid']:.1f}, ask={best['ask']:.1f}")
