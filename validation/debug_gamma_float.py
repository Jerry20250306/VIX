"""
驗證 92845 案例的 Mid 比較是否受浮點數精度影響
"""
import pandas as pd

df = pd.read_csv('output/驗證20251231_NearPROD.csv', low_memory=False)

# 92845, 31800 (c)
time = 92845
strike = 31800

rows = df[(df['strike'] == strike) & (df['time'] <= time)].sort_values('time')
if len(rows) >= 2:
    prev = rows.iloc[-2]
    curr = rows.iloc[-1]
    
    # 前一期選定的中價
    p_bid = prev['c.last_bid'] if prev['c.source'] == 'Q_last' else prev['c.min_bid']
    p_ask = prev['c.last_ask'] if prev['c.source'] == 'Q_last' else prev['c.min_ask']
    p_mid = (p_bid + p_ask) / 2
    
    # 當前 Q_Min 的中價
    c_mid = (curr['c.min_bid'] + curr['c.min_ask']) / 2
    
    print(f"Prev Mid: {p_mid} (repr: {repr(p_mid)})")
    print(f"Curr Mid: {c_mid} (repr: {repr(c_mid)})")
    
    print(f"\n比較結果:")
    print(f"  curr <= prev: {c_mid <= p_mid}")
    print(f"  curr > prev:  {c_mid > p_mid}")
    print(f"  差值: {c_mid - p_mid}")
    
    if c_mid > p_mid and abs(c_mid - p_mid) < 1e-9:
        print("\n>>> 發現問題：兩者幾乎相等，但因為浮點數誤差判定為『上漲』(Gamma=2.0)")
