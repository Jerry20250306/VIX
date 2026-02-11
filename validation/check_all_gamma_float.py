"""
檢查 9 筆 Gamma 差異案例是否皆由浮點數精度導致的 Mid 比較誤判
"""
import pandas as pd
import numpy as np

# 讀取結果
df = pd.read_csv('output/驗證20251231_NearPROD.csv', low_memory=False)

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

print("=== Gamma 差異與浮點數精度分析 ===\n")

for time, strike, prefix in cases:
    rows = df[(df['strike'] == strike) & (df['time'] <= time)].sort_values('time')
    if len(rows) >= 2:
        prev = rows.iloc[-2]
        curr = rows.iloc[-1]
        
        # 前一期 Q_hat_Mid
        ps = prev[f'{prefix}.source']
        p_bid = prev[f'{prefix}.last_bid'] if ps == 'Q_last' else prev[f'{prefix}.min_bid']
        p_ask = prev[f'{prefix}.last_ask'] if ps == 'Q_last' else prev[f'{prefix}.min_ask']
        p_mid = (p_bid + p_ask) / 2
        
        # 當前選中報價的 Mid (或是 Q_Last 與 Q_Min 的 Mid)
        cs = curr[f'{prefix}.source']
        c_bid = curr[f'{prefix}.last_bid'] if cs == 'Q_last' else curr[f'{prefix}.min_bid']
        c_ask = curr[f'{prefix}.last_ask'] if cs == 'Q_last' else curr[f'{prefix}.min_ask']
        c_mid = (c_bid + c_ask) / 2
        
        diff = c_mid - p_mid
        
        print(f"time={time}, strike={strike} ({prefix}):")
        print(f"  Prev Mid: {repr(p_mid)}")
        print(f"  Curr Mid: {repr(c_mid)}")
        print(f"  Diff: {diff}")
        print(f"  Ours Gamma: {curr[f'{prefix}.gamma']}")
        if diff > 0 and diff < 1e-9:
             print("  >>> [判定為上漲，但差值極小] 可能受浮點數影響")
        print()
