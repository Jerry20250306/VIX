"""
檢查 9 筆 Gamma 差異案例的前一期 Q_hat_Mid 是否皆為 NaN
"""
import pandas as pd
import numpy as np

# 讀取結果
df_near = pd.read_csv('output/驗證20251231_NearPROD.csv', low_memory=False)

cases = [
    (92845, 31800, 'c'),
    (133530, 31700, 'c'),
    (134400, 31500, 'c'),
    (85830, 24000, 'p'),
    (104015, 25000, 'p'),
    (123615, 23900, 'p'),
    (130530, 23900, 'p'),
    (130915, 24300, 'p'),
    (133845, 24600, 'p'),
]

print("=== 9 筆 Gamma 差異案例分析 ===\n")

for time, strike, prefix in cases:
    # 找出當前與前一期
    target_rows = df_near[(df_near['strike'] == strike) & (df_near['time'] <= time)].sort_values('time')
    
    if len(target_rows) >= 2:
        prev_row = target_rows.iloc[-2]
        curr_row = target_rows.iloc[-1]
        
        # 計算前一期的 Q_hat_Mid
        source_col = f'{prefix}.source'
        bid_col = f'{prefix}.last_bid' if prev_row[source_col] == 'Q_last' else f'{prefix}.min_bid'
        ask_col = f'{prefix}.last_ask' if prev_row[source_col] == 'Q_last' else f'{prefix}.min_ask'
        
        # 注意: 如果 source 是 NaN，則 Q_hat_Mid 是上一期的 Q_hat_Mid
        # 但這裡簡單判斷 source 是否存在
        if pd.isna(prev_row[source_col]):
            prev_q_hat_mid = np.nan
        else:
            bid = prev_row[f'{prefix}.last_bid'] if prev_row[source_col] == 'Q_last' else prev_row[f'{prefix}.min_bid']
            ask = prev_row[f'{prefix}.last_ask'] if prev_row[source_col] == 'Q_last' else prev_row[f'{prefix}.min_ask']
            prev_q_hat_mid = (bid + ask) / 2
            
        print(f"time={time}, strike={strike} ({prefix}):")
        print(f"  Prev Source: {prev_row[source_col]}")
        print(f"  Prev Q_hat_Mid: {prev_q_hat_mid}")
        print(f"  我們的 Gamma: {curr_row[f'{prefix}.gamma']}")
        print()
    else:
        print(f"time={time}, strike={strike} ({prefix}): 找不到前一期資料 (共 {len(target_rows)} 筆)\n")
