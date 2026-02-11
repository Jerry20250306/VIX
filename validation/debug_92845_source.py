"""
找出 92845, 31800 (Call) 的 c.source 和各項屬性
"""
import pandas as pd

df = pd.read_csv('output/驗證20251231_NearPROD.csv')
row = df[(df['time'] == 92845) & (df['strike'] == 31800)]

if len(row) > 0:
    r = row.iloc[0]
    print(f"time=92845, strike=31800:")
    print(f"  c.source: {r['c.source']}")
    print(f"  c.gamma:  {r['c.gamma']}")
    print(f"  c.last_bid/ask: {r['c.last_bid']} / {r['c.last_ask']}")
    print(f"  c.min_bid/ask:  {r['c.min_bid']} / {r['c.min_ask']}")
    
    # 讀取 step1 看看這時點的 Q_hat_Mid_prev
    step1 = pd.read_csv('output/驗證20251231_Near_step1.csv')
    s1_row = step1[(step1['Time'] == 92845) & (step1['Strike'] == 31800) & (step1['CP'] == 'Call')]
    if len(s1_row) > 0:
        s1 = s1_row.iloc[0]
        # 注意: step1 可能沒有 Q_hat_Mid_prev，但我可以看前一個 time 的 Q_hat_Mid
        prev_s1 = step1[(step1['Time'] < 92845) & (step1['Strike'] == 31800) & (step1['CP'] == 'Call')].sort_values('Time').iloc[-1:]
        if len(prev_s1) > 0:
            ps1 = prev_s1.iloc[0]
            print(f"\nPrevious time ({ps1['Time']}):")
            print(f"  Q_hat_Mid: {ps1.get('Q_hat_Mid', 'NOT FOUND')}")
            # 如果 step1 沒有 Q_hat_Mid，我們從 NearPROD 找
            prev_near = df[(df['time'] == ps1['Time']) & (df['strike'] == 31800)]
            if len(prev_near) > 0:
                pn = prev_near.iloc[0]
                p_bid = pn['c.last_bid'] if pn['c.source'] == 'Q_last' else pn['c.min_bid']
                p_ask = pn['c.last_ask'] if pn['c.source'] == 'Q_last' else pn['c.min_ask']
                print(f"  Q_hat_Mid (from NearPROD): {(p_bid+p_ask)/2}")
else:
    print("找不到筆數")
